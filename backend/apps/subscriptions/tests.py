from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import UserProfile
from apps.subscriptions.card_views import _apply_successful_payment
from apps.subscriptions.models import (
    AdminAlert,
    CardPayment,
    OutboundMessage,
    PaymentNotification,
    Subscription,
    SubscriptionPlan,
)
from apps.subscriptions.services.messaging import notify_payment_received


def _make_profile(user, *, full_name="", clinic_role=UserProfile.ClinicRole.PATIENT):
    return UserProfile.objects.create(
        user=user,
        clinic_role=clinic_role,
        full_name=full_name,
        gender=UserProfile.Gender.FEMALE,
        age=30,
        height_cm=Decimal("160"),
        weight_kg=Decimal("70"),
        activity_level=UserProfile.ActivityLevel.MODERATELY_ACTIVE,
    )


class PaymentNotificationSignalTests(TestCase):
    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            code="monthly",
            name_ar="اشتراك شهري",
            name_en="Monthly subscription",
            price_iqd=25000,
            duration_days=30,
        )
        self.patient = User.objects.create_user(username="07801112233", password="pass1234")
        _make_profile(self.patient, full_name="سارة علي")
        self.doctor = User.objects.create_user(username="07809998877", password="pass1234")
        _make_profile(
            self.doctor,
            full_name="د. طيبة",
            clinic_role=UserProfile.ClinicRole.DOCTOR,
        )
        self.subscription = Subscription.objects.create(
            user=self.patient,
            plan=self.plan,
            amount_iqd=25000,
            payment_reference="NT-MONTH01",
            status=Subscription.Status.PENDING_PAYMENT,
        )

    def test_notify_includes_name_and_monthly_subscription_number(self):
        alert = notify_payment_received(
            user=self.patient,
            subscription=self.subscription,
            source="إرسال / دفع بالبطاقة",
        )
        self.assertEqual(alert.kind, AdminAlert.Kind.PAYMENT_CONFIRMED)
        self.assertIn("سارة علي", alert.title)
        self.assertIn("NT-MONTH01", alert.title)
        self.assertIn("الاسم: سارة علي", alert.body)
        self.assertIn("رقم الاشتراك الشهري: NT-MONTH01", alert.body)
        self.assertIn("تم فتح برنامج الوجبات تلقائياً حسب الهدف اليومي وخطة نزول الوزن", alert.body)

        patient_msgs = OutboundMessage.objects.filter(user=self.patient)
        self.assertEqual(patient_msgs.count(), 1)
        self.assertIn("سارة علي", patient_msgs.first().body)
        self.assertIn("NT-MONTH01", patient_msgs.first().body)
        self.assertIn("تم فتح برنامج الوجبات تلقائياً", patient_msgs.first().body)

        doctor_msgs = OutboundMessage.objects.filter(user=self.doctor)
        self.assertEqual(doctor_msgs.count(), 1)
        self.assertIn("سارة علي قام بالدفع", doctor_msgs.first().body)
        self.assertIn("NT-MONTH01", doctor_msgs.first().body)

    def test_card_send_pay_creates_django_payment_signal(self):
        payment = CardPayment.objects.create(
            user=self.patient,
            subscription=self.subscription,
            amount_iqd=25000,
            status=CardPayment.Status.AWAITING_3DS,
            gateway="sandbox",
            gateway_transaction_id="SANDBOX-TX-1",
            gateway_order_id="NTC-TEST01",
            card_brand="visa",
            card_last4="4242",
        )
        _apply_successful_payment(payment, brand="visa", last4="4242")
        payment.refresh_from_db()
        self.subscription.refresh_from_db()

        self.assertEqual(payment.status, CardPayment.Status.SUCCEEDED)
        self.assertEqual(self.subscription.status, Subscription.Status.ACTIVE)
        self.assertTrue(self.subscription.is_access_granted)
        self.patient.profile.refresh_from_db()
        self.assertGreaterEqual(self.patient.profile.target_calories, 1200)
        self.assertEqual(self.patient.profile.clinical_goal, "نزول الوزن")
        self.assertTrue(
            PaymentNotification.objects.filter(
                payment_reference="NT-MONTH01",
                payer_name="سارة علي",
                processed=True,
            ).exists()
        )
        alert = AdminAlert.objects.get(user=self.patient)
        self.assertIn("سارة علي", alert.title)
        self.assertIn("NT-MONTH01", alert.body)
        self.assertIn("إرسال / دفع بالبطاقة", alert.body)

        # Idempotent: second success must not duplicate alerts / WhatsApp.
        _apply_successful_payment(payment, brand="visa", last4="4242")
        self.assertEqual(AdminAlert.objects.filter(user=self.patient).count(), 1)
        self.assertEqual(OutboundMessage.objects.filter(user=self.patient).count(), 1)

    def test_confirm_transfer_sends_named_alert(self):
        client = APIClient()
        client.force_authenticate(user=self.patient)
        response = client.post(
            "/api/subscriptions/confirm-transfer/",
            {
                "full_name": "سارة علي",
                "address": "بغداد",
                "subscription_id": self.subscription.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, Subscription.Status.ACTIVE)
        self.assertTrue(self.subscription.is_access_granted)
        alert = AdminAlert.objects.get(user=self.patient)
        self.assertIn("سارة علي", alert.title)
        self.assertIn("رقم الاشتراك الشهري: NT-MONTH01", alert.body)
        self.assertIn("تم فتح برنامج الوجبات تلقائياً حسب الهدف اليومي وخطة نزول الوزن", alert.body)
        self.assertTrue(OutboundMessage.objects.filter(user=self.doctor).exists())

    def test_paid_user_can_open_weekly_meals_at_fat_loss_goal(self):
        from apps.accounts.services.tdee import calculate_daily_targets

        client = APIClient()
        client.force_authenticate(user=self.patient)
        blocked = client.get("/api/meal-plans/weekly/")
        self.assertEqual(blocked.status_code, 403)

        client.post(
            "/api/subscriptions/confirm-transfer/",
            {
                "full_name": "سارة علي",
                "address": "بغداد",
                "subscription_id": self.subscription.id,
            },
            format="json",
        )
        opened = client.get("/api/meal-plans/weekly/")
        self.assertEqual(opened.status_code, 200)
        energy = calculate_daily_targets(
            weight_kg=Decimal("70"),
            height_cm=Decimal("160"),
            age=30,
            gender=UserProfile.Gender.FEMALE,
            activity_level=UserProfile.ActivityLevel.MODERATELY_ACTIVE,
            deficit=500,
        )
        self.assertEqual(opened.data["target_calories"], energy["goal_calories"])
        self.assertEqual(opened.data["goal_source"], "weight_loss")
        self.assertEqual(opened.data["deficit"], 500)
