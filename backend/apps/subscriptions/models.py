from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class PaymentSettings(models.Model):
    """
    Singleton admin-editable SuperQI wallet details shown on the subscriptions panel.
    """

    merchant_phone = models.CharField(
        max_length=32,
        help_text="رقم سوبر كي للتحويل المباشر (يظهر للمستخدم).",
    )
    title_ar = models.CharField(
        max_length=120,
        default="رقم سوبر كي للتحويل المباشر",
    )
    title_en = models.CharField(
        max_length=120,
        default="SuperQI number for direct transfer",
    )
    hint_ar = models.CharField(
        max_length=255,
        default="حوّل المبلغ مباشرة على هذا الرقم ثم أكّد التحويل أدناه.",
    )
    hint_en = models.CharField(
        max_length=255,
        default="Transfer the amount directly to this number, then confirm below.",
    )
    merchant_label_ar = models.CharField(
        max_length=120,
        default="سوبر كي — محفظة البرنامج",
        blank=True,
    )
    merchant_label_en = models.CharField(
        max_length=120,
        default="SuperQI — program wallet",
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SuperQI payment settings"
        verbose_name_plural = "SuperQI payment settings"

    def __str__(self) -> str:
        return f"SuperQI · {self.merchant_phone}"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls) -> "PaymentSettings":
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "merchant_phone": getattr(settings, "SUPERQI_MERCHANT_PHONE", "07801234567"),
                "merchant_label_ar": getattr(
                    settings,
                    "SUPERQI_MERCHANT_LABEL",
                    "سوبر كي — محفظة البرنامج",
                ),
            },
        )
        return obj


class SubscriptionPlan(models.Model):
    """Paid plan that unlocks the weekly meal program."""

    code = models.SlugField(unique=True)
    name_ar = models.CharField(max_length=120)
    name_en = models.CharField(max_length=120)
    price_iqd = models.PositiveIntegerField(help_text="Price in Iraqi dinars.")
    duration_days = models.PositiveIntegerField(default=30)
    meal_variety_level = models.PositiveSmallIntegerField(
        default=1,
        help_text="Higher = more dish variety in weekly menus.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price_iqd"]

    def __str__(self) -> str:
        return f"{self.name_en} ({self.price_iqd} IQD)"


class Subscription(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending SuperQI payment"
        PAID_PENDING_ACTIVATION = "paid_pending_activation", "Paid — awaiting admin"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
    )
    payment_reference = models.CharField(
        max_length=32,
        unique=True,
        help_text="Reference the user must include in the SuperQI transfer.",
    )
    amount_iqd = models.PositiveIntegerField()
    superqi_transaction_id = models.CharField(max_length=128, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activated_subscriptions",
    )
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    expiry_warning_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the pre-expiry WhatsApp / system alert was sent.",
    )
    admin_note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} · {self.plan.code} · {self.status}"

    @staticmethod
    def generate_reference() -> str:
        return f"NT-{secrets.token_hex(4).upper()}"

    @property
    def is_access_granted(self) -> bool:
        if self.status != self.Status.ACTIVE:
            return False
        if self.ends_at and timezone.now() > self.ends_at:
            return False
        return True

    def mark_paid(self, *, transaction_id: str = "", note: str = "") -> None:
        self.status = self.Status.PAID_PENDING_ACTIVATION
        self.paid_at = timezone.now()
        if transaction_id:
            self.superqi_transaction_id = transaction_id
        if note:
            self.admin_note = note
        self.save(
            update_fields=[
                "status",
                "paid_at",
                "superqi_transaction_id",
                "admin_note",
                "updated_at",
            ]
        )

    def apply_plan_window(self, *, admin_user=None, prefer_existing_start: bool = True) -> None:
        """
        Set ACTIVE and fill starts_at / ends_at from the selected plan duration.
        ends_at = starts_at + plan.duration_days (automatic).
        """
        now = timezone.now()
        if not prefer_existing_start or not self.starts_at:
            self.starts_at = now
        if not self.activated_at:
            self.activated_at = now
        if admin_user is not None:
            self.activated_by = admin_user
        duration = int(self.plan.duration_days or 30)
        self.ends_at = self.starts_at + timedelta(days=duration)
        self.status = self.Status.ACTIVE

    def activate(self, *, admin_user=None) -> None:
        self.apply_plan_window(admin_user=admin_user, prefer_existing_start=False)
        self.save(
            update_fields=[
                "status",
                "activated_at",
                "starts_at",
                "ends_at",
                "activated_by",
                "updated_at",
            ]
        )


class PaymentNotification(models.Model):
    """Inbound SuperQI (or manual) payment signal for admin review."""

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="payment_notifications",
        null=True,
        blank=True,
    )
    payment_reference = models.CharField(max_length=32, db_index=True)
    amount_iqd = models.PositiveIntegerField(null=True, blank=True)
    transaction_id = models.CharField(max_length=128, blank=True, default="")
    payer_name = models.CharField(max_length=120, blank=True, default="")
    payer_address = models.CharField(max_length=255, blank=True, default="")
    gps_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Payment {self.payment_reference} ({self.transaction_id or 'no-tx'})"


class AdminAlert(models.Model):
    """Internal inbox message for supervisors (renewals, payment confirmations)."""

    class Kind(models.TextChoices):
        PAYMENT_CONFIRMED = "payment_confirmed", "Payment confirmed by user"
        RENEWAL_REQUEST = "renewal_request", "Renewal payment — activate again"
        SUBSCRIPTION_EXPIRED = "subscription_expired", "Subscription expired"
        EXPIRY_WARNING = "expiry_warning", "Expiry warning sent"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="admin_alerts",
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_alerts",
    )
    kind = models.CharField(max_length=40, choices=Kind.choices)
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.kind}] {self.title}"


class OutboundMessage(models.Model):
    """WhatsApp (or SMS) messages queued/sent to subscribers."""

    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="outbound_messages",
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outbound_messages",
    )
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.WHATSAPP)
    phone = models.CharField(max_length=32)
    body = models.TextField()
    deep_link = models.URLField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.channel} → {self.phone} ({self.status})"


class SavedPaymentMethod(models.Model):
    """
    Tokenized card on file — PCI-safe.

    NEVER store full PAN or CVV. Only gateway token + display metadata.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_payment_methods",
    )
    gateway = models.CharField(max_length=32, default="qicard")
    gateway_token = models.CharField(max_length=255)
    brand = models.CharField(max_length=32, blank=True, default="")
    last4 = models.CharField(max_length=4)
    exp_month = models.PositiveSmallIntegerField(null=True, blank=True)
    exp_year = models.PositiveSmallIntegerField(null=True, blank=True)
    cardholder_name = models.CharField(max_length=120, blank=True, default="")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self) -> str:
        return f"{self.brand} •••• {self.last4}"


class CardPayment(models.Model):
    """Card charge attempt via payment gateway (3-D Secure / OTP)."""

    class Status(models.TextChoices):
        CREATED = "created", "Created"
        AWAITING_3DS = "awaiting_3ds", "Awaiting 3-D Secure / OTP"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="card_payments",
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="card_payments",
    )
    saved_method = models.ForeignKey(
        SavedPaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    amount_iqd = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="IQD")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
    )
    gateway = models.CharField(max_length=32, default="sandbox")
    gateway_transaction_id = models.CharField(max_length=128, blank=True, default="", db_index=True)
    gateway_order_id = models.CharField(max_length=64, unique=True)
    redirect_url = models.URLField(blank=True, default="", max_length=500)
    # Display-only card meta returned by gateway after auth (never PAN/CVV)
    card_brand = models.CharField(max_length=32, blank=True, default="")
    card_last4 = models.CharField(max_length=4, blank=True, default="")
    failure_reason = models.CharField(max_length=255, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    raw_gateway_status = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.gateway_order_id} · {self.amount_iqd} · {self.status}"
