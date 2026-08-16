from __future__ import annotations

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserProfile
from apps.subscriptions.models import PaymentNotification, Subscription, SubscriptionPlan
from apps.subscriptions.serializers import (
    ConfirmTransferSerializer,
    SubscribeSerializer,
    SubscriptionPlanSerializer,
    SubscriptionSerializer,
)
from apps.subscriptions.services.lifecycle import grant_paid_meal_access, process_subscription_lifecycle
from apps.subscriptions.services.messaging import notify_payment_received
from apps.subscriptions.services.superqi import payment_instructions, superqi_public_info


def _active_subscription(user) -> Subscription | None:
    now = timezone.now()
    return (
        Subscription.objects.filter(
            user=user,
            status=Subscription.Status.ACTIVE,
            ends_at__gt=now,
        )
        .select_related("plan")
        .order_by("-ends_at")
        .first()
    )


def _subscriber_display_name(user) -> str:
    profile = getattr(user, "profile", None)
    if profile and profile.full_name:
        return profile.full_name
    return user.get_username()


def _weight_progress(user) -> dict | None:
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        return None

    start = profile.starting_weight_kg or profile.weight_kg
    current = profile.weight_kg
    lost = float(start) - float(current) if start is not None else 0.0
    return {
        "full_name": profile.full_name or user.get_username(),
        "starting_weight_kg": float(start) if start is not None else None,
        "current_weight_kg": float(current),
        "lost_kg": round(lost, 1),
        "gift_eligible": lost >= 3,
    }


class PlanListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        plans = SubscriptionPlan.objects.filter(is_active=True)
        return Response(SubscriptionPlanSerializer(plans, many=True).data)


class MySubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        # Auto warn / expire for this user so access locks without waiting for cron.
        process_subscription_lifecycle(user=request.user)

        active = _active_subscription(request.user)
        latest = (
            Subscription.objects.filter(user=request.user)
            .select_related("plan")
            .order_by("-created_at")
            .first()
        )
        expired_latest = (
            Subscription.objects.filter(
                user=request.user,
                status=Subscription.Status.EXPIRED,
            )
            .select_related("plan")
            .order_by("-ends_at")
            .first()
        )
        info = superqi_public_info()
        instructions = payment_instructions(
            amount_iqd=(latest.amount_iqd if latest else 25000),
            reference=(latest.payment_reference if latest else "NT-XXXX"),
        )
        needs_renewal = bool(
            not active
            and (
                (latest and latest.status == Subscription.Status.EXPIRED)
                or expired_latest
            )
        )
        calendar_source = active or expired_latest
        return Response(
            {
                "has_meal_access": bool(active and active.is_access_granted),
                "needs_renewal": needs_renewal,
                "subscriber_name": _subscriber_display_name(request.user),
                "promo_banner": {
                    "name": _subscriber_display_name(request.user),
                    "text_ar": "إذا نزلت وزنك راح تربح هدية · وينا اشترك واربح صحتك",
                    "text_en": "Lose weight and win a gift · Subscribe and win your health",
                },
                "weight_progress": _weight_progress(request.user),
                "active": SubscriptionSerializer(active).data if active else None,
                "latest": SubscriptionSerializer(latest).data if latest else None,
                "calendar": (
                    {
                        "starts_at": calendar_source.starts_at,
                        "ends_at": calendar_source.ends_at,
                        "plan_name_ar": calendar_source.plan.name_ar,
                        "plan_name_en": calendar_source.plan.name_en,
                        "access_active": bool(active and active.is_access_granted),
                    }
                    if calendar_source and calendar_source.starts_at and calendar_source.ends_at
                    else None
                ),
                "superqi": {
                    **info,
                    **instructions,
                },
            }
        )


class SubscribeView(APIView):
    """Create a pending subscription and return SuperQI payment details."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan_code = serializer.validated_data["plan_code"]

        try:
            plan = SubscriptionPlan.objects.get(code=plan_code, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"detail": "Subscription plan not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        open_statuses = {
            Subscription.Status.PENDING_PAYMENT,
            Subscription.Status.PAID_PENDING_ACTIVATION,
            Subscription.Status.ACTIVE,
        }
        existing = (
            Subscription.objects.filter(user=request.user, status__in=open_statuses)
            .select_related("plan")
            .order_by("-created_at")
            .first()
        )
        if existing:
            if existing.status == Subscription.Status.ACTIVE and existing.is_access_granted:
                return Response(
                    {
                        "detail": "You already have an active subscription.",
                        "subscription": SubscriptionSerializer(existing).data,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Stale ACTIVE past ends_at — expire then allow renew flow.
            if existing.status == Subscription.Status.ACTIVE and not existing.is_access_granted:
                from apps.subscriptions.services.lifecycle import expire_subscription

                expire_subscription(existing)
                existing = None
            elif existing.status == Subscription.Status.PENDING_PAYMENT:
                if existing.plan_id != plan.id:
                    existing.plan = plan
                    existing.amount_iqd = plan.price_iqd
                    existing.payment_reference = Subscription.generate_reference()
                    existing.save(
                        update_fields=[
                            "plan",
                            "amount_iqd",
                            "payment_reference",
                            "updated_at",
                        ]
                    )
                info = superqi_public_info()
                instructions = payment_instructions(
                    amount_iqd=existing.amount_iqd,
                    reference=existing.payment_reference,
                )
                return Response(
                    {
                        "subscription": SubscriptionSerializer(existing).data,
                        "superqi": {
                            **info,
                            "amount_iqd": existing.amount_iqd,
                            "payment_reference": existing.payment_reference,
                            **instructions,
                        },
                    }
                )
            elif existing.status == Subscription.Status.PAID_PENDING_ACTIVATION:
                info = superqi_public_info()
                instructions = payment_instructions(
                    amount_iqd=existing.amount_iqd,
                    reference=existing.payment_reference,
                )
                return Response(
                    {
                        "detail": "Complete or wait on your existing subscription request.",
                        "subscription": SubscriptionSerializer(existing).data,
                        "superqi": {
                            **info,
                            "amount_iqd": existing.amount_iqd,
                            "payment_reference": existing.payment_reference,
                            **instructions,
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Allow renewing from EXPIRED by creating a fresh pending subscription.
        subscription = Subscription.objects.create(
            user=request.user,
            plan=plan,
            amount_iqd=plan.price_iqd,
            payment_reference=Subscription.generate_reference(),
            status=Subscription.Status.PENDING_PAYMENT,
        )
        info = superqi_public_info()
        instructions = payment_instructions(
            amount_iqd=subscription.amount_iqd,
            reference=subscription.payment_reference,
        )
        return Response(
            {
                "subscription": SubscriptionSerializer(subscription).data,
                "superqi": {
                    **info,
                    "amount_iqd": subscription.amount_iqd,
                    "payment_reference": subscription.payment_reference,
                    **instructions,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class ConfirmTransferView(APIView):
    """
    User confirms they transferred via SuperQI.
    Saves name/address/GPS and creates an admin alert for activation.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = ConfirmTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        subscription_id = data.get("subscription_id")
        qs = Subscription.objects.filter(user=request.user).select_related("plan")
        if subscription_id:
            subscription = qs.filter(id=subscription_id).first()
        else:
            subscription = (
                qs.filter(
                    status__in={
                        Subscription.Status.PENDING_PAYMENT,
                        Subscription.Status.PAID_PENDING_ACTIVATION,
                        Subscription.Status.EXPIRED,
                    }
                )
                .order_by("-created_at")
                .first()
            )

        if not subscription:
            return Response(
                {"detail": "No pending subscription to confirm."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Persist contact + GPS on profile for future months.
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "Complete your profile first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        profile.full_name = data["full_name"]
        profile.address = data["address"]
        if data.get("gps_latitude") is not None:
            profile.gps_latitude = data["gps_latitude"]
        if data.get("gps_longitude") is not None:
            profile.gps_longitude = data["gps_longitude"]
        if profile.starting_weight_kg is None:
            profile.starting_weight_kg = profile.weight_kg
        profile.save()

        had_prior_active = Subscription.objects.filter(
            user=request.user,
            status=Subscription.Status.EXPIRED,
        ).exists() or bool(subscription.activated_at)

        if subscription.status == Subscription.Status.ACTIVE and subscription.is_access_granted:
            return Response(
                {
                    "ok": True,
                    "subscription": SubscriptionSerializer(subscription).data,
                    "detail": "الاشتراك مفعّل وبرنامج الوجبات مفتوح حسب هدفك اليومي.",
                }
            )

        grant_paid_meal_access(
            subscription=subscription,
            note=f"User confirmed SuperQI transfer. Name={data['full_name']}",
        )

        PaymentNotification.objects.create(
            subscription=subscription,
            payment_reference=subscription.payment_reference,
            amount_iqd=subscription.amount_iqd,
            payer_name=data["full_name"],
            payer_address=data["address"],
            gps_latitude=data.get("gps_latitude"),
            gps_longitude=data.get("gps_longitude"),
            raw_payload={
                "source": "user_confirm_transfer",
                **{k: str(v) for k, v in data.items() if v is not None},
            },
            processed=True,
        )

        extra_lines = [f"العنوان: {data['address']}"]
        if data.get("gps_latitude") is not None and data.get("gps_longitude") is not None:
            extra_lines.append(f"GPS: {data['gps_latitude']}, {data['gps_longitude']}")

        notify_payment_received(
            user=request.user,
            subscription=subscription,
            source="سوبر كي",
            extra_lines=extra_lines,
            is_renewal=had_prior_active,
            payer_name=data["full_name"],
        )

        return Response(
            {
                "ok": True,
                "subscription": SubscriptionSerializer(subscription).data,
                "detail": "تم تأكيد الدفع. برنامج الوجبات مفتوح حسب هدفك اليومي وخطة نزول الوزن.",
            }
        )


class SuperQiWebhookView(APIView):
    """Receive SuperQI payment notifications (optional automated path)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        data = request.data if isinstance(request.data, dict) else {}
        reference = (
            data.get("payment_reference")
            or data.get("reference")
            or data.get("orderId")
            or data.get("order_id")
            or ""
        )
        reference = str(reference).strip().upper()
        transaction_id = str(
            data.get("transaction_id")
            or data.get("transactionId")
            or data.get("id")
            or ""
        ).strip()
        amount = data.get("amount_iqd") or data.get("amount")

        notification = PaymentNotification.objects.create(
            payment_reference=reference or "UNKNOWN",
            amount_iqd=int(amount) if amount not in (None, "") else None,
            transaction_id=transaction_id,
            payer_name=str(data.get("payer_name") or data.get("name") or ""),
            payer_address=str(data.get("address") or ""),
            raw_payload=data,
        )

        if not reference:
            return Response(
                {"detail": "Missing payment reference.", "notification_id": notification.id},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription = (
            Subscription.objects.filter(payment_reference__iexact=reference)
            .exclude(status=Subscription.Status.CANCELLED)
            .select_related("user", "user__profile", "plan")
            .order_by("-created_at")
            .first()
        )
        if not subscription:
            return Response(
                {
                    "detail": "No subscription matched this reference.",
                    "notification_id": notification.id,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        notification.subscription = subscription
        notification.processed = True
        notification.save(update_fields=["subscription", "processed"])

        if subscription.status in {
            Subscription.Status.PENDING_PAYMENT,
            Subscription.Status.PAID_PENDING_ACTIVATION,
            Subscription.Status.EXPIRED,
        }:
            is_renewal = Subscription.objects.filter(
                user=subscription.user,
                status=Subscription.Status.EXPIRED,
            ).exists() or bool(subscription.activated_at)
            grant_paid_meal_access(
                subscription=subscription,
                transaction_id=transaction_id,
                note="Auto-marked paid from SuperQI webhook.",
            )
            notify_payment_received(
                user=subscription.user,
                subscription=subscription,
                source="إشعار سوبر كي",
                extra_lines=[f"TX: {transaction_id or '—'}"],
                is_renewal=is_renewal,
                payer_name=notification.payer_name,
            )

        return Response(
            {
                "ok": True,
                "subscription_id": subscription.id,
                "status": subscription.status,
                "notification_id": notification.id,
            }
        )
