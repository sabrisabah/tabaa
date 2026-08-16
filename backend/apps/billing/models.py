from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Max
from django.utils import timezone


class ServiceCategory(models.TextChoices):
    CONSULTATION = "consultation", "Consultation"
    LAB = "lab", "Lab / Device"
    NUTRITION = "nutrition", "Nutrition plan"
    INJECTION = "injection", "Injection / session"
    MEDICATION = "medication", "Medication dose"
    FOLLOW_UP = "follow_up", "Follow-up"
    OTHER = "other", "Other"


class ClinicService(models.Model):
    """
    Manageable service catalog for د. طيبة clinic revenue.
    Soft-disable instead of delete to preserve historical invoices.
    """

    code = models.SlugField(max_length=64, unique=True)
    name_ar = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200, blank=True, default="")
    category = models.CharField(
        max_length=32,
        choices=ServiceCategory.choices,
        default=ServiceCategory.OTHER,
    )
    unit_label_ar = models.CharField(max_length=80, blank=True, default="لكل خدمة")
    base_price_iqd = models.PositiveIntegerField(
        help_text="Default IQD price (no decimals).",
    )
    allow_quantity = models.BooleanField(default=False)
    is_doctor_visit = models.BooleanField(
        default=False,
        help_text="One paid doctor visit per patient; later visits become free follow-up.",
    )
    is_free_follow_up = models.BooleanField(
        default=False,
        help_text="Zero-price follow-up line used for documentation only.",
    )
    has_price_variants = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name_ar"]

    def __str__(self) -> str:
        return f"{self.name_ar} ({self.base_price_iqd:,} IQD)"


class ServicePriceVariant(models.Model):
    """Independent price option (e.g. Mounjaro dose strengths)."""

    service = models.ForeignKey(
        ClinicService,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    code = models.SlugField(max_length=64)
    label_ar = models.CharField(max_length=120)
    label_en = models.CharField(max_length=120, blank=True, default="")
    price_iqd = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    effective_from = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "label_ar"]
        unique_together = [("service", "code")]

    def __str__(self) -> str:
        return f"{self.service.code}:{self.label_ar} = {self.price_iqd:,}"


class DiscountReason(models.TextChoices):
    FRIENDS = "friends", "الأصدقاء"
    RELATIVES = "relatives", "الأقارب"
    STUDENTS = "students", "الطلبة"
    DISABILITY = "disability", "ذوو الإعاقة"
    CUSTOM = "custom", "سبب مخصص"


class PaymentMethod(models.TextChoices):
    CASH = "cash", "نقداً"
    MASTER_QI_CARD = "master_qi_card", "Master Qi Card"


class PaymentStatus(models.TextChoices):
    UNPAID = "unpaid", "غير مدفوعة"
    PARTIAL = "partial", "مدفوعة جزئياً"
    PAID = "paid", "مدفوعة"
    CANCELLED = "cancelled", "ملغاة"
    REFUNDED = "refunded", "مستردة"


class Invoice(models.Model):
    """Clinic invoice for د. طيبة — sequential IQD billing."""

    invoice_number = models.PositiveIntegerField(unique=True, editable=False)
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clinic_invoices",
    )
    patient_name_snapshot = models.CharField(max_length=160, blank=True, default="")
    patient_file_snapshot = models.CharField(max_length=32, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_invoices",
    )
    subtotal_iqd = models.PositiveIntegerField(default=0)
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    discount_amount_iqd = models.PositiveIntegerField(default=0)
    discount_reason = models.CharField(
        max_length=32,
        choices=DiscountReason.choices,
        blank=True,
        default="",
    )
    discount_reason_custom = models.CharField(max_length=255, blank=True, default="")
    discount_entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entered_discounts",
    )
    discount_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_discounts",
    )
    discount_approved_at = models.DateTimeField(null=True, blank=True)
    total_due_iqd = models.PositiveIntegerField(default=0)
    amount_paid_iqd = models.PositiveIntegerField(default=0)
    payment_method = models.CharField(
        max_length=32,
        choices=PaymentMethod.choices,
        blank=True,
        default="",
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )
    show_discount_reason_on_receipt = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"INV-{self.invoice_number:06d}"

    @staticmethod
    def next_invoice_number() -> int:
        current = Invoice.objects.aggregate(m=Max("invoice_number"))["m"] or 0
        return current + 1

    def recalculate(self, *, save: bool = True) -> None:
        subtotal = sum(item.line_total_iqd for item in self.items.all())
        self.subtotal_iqd = int(subtotal)
        if self.subtotal_iqd == 0 or not self.discount_percent:
            self.discount_amount_iqd = 0
        else:
            # Final = subtotal - (subtotal × discount% / 100), integer IQD
            raw = (self.subtotal_iqd * float(self.discount_percent)) / 100.0
            self.discount_amount_iqd = int(round(raw))
        self.total_due_iqd = max(0, self.subtotal_iqd - self.discount_amount_iqd)
        if save:
            self.save(
                update_fields=[
                    "subtotal_iqd",
                    "discount_amount_iqd",
                    "total_due_iqd",
                    "updated_at",
                ],
            )


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(
        ClinicService,
        on_delete=models.PROTECT,
        related_name="invoice_lines",
        null=True,
        blank=True,
    )
    variant = models.ForeignKey(
        ServicePriceVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_lines",
    )
    service_name_snapshot = models.CharField(max_length=200)
    variant_label_snapshot = models.CharField(max_length=120, blank=True, default="")
    unit_price_iqd = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    line_total_iqd = models.PositiveIntegerField()
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        self.line_total_iqd = int(self.unit_price_iqd) * int(self.quantity)
        super().save(*args, **kwargs)


class AuditAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    PAY = "pay", "Pay"
    CANCEL = "cancel", "Cancel"
    REFUND = "refund", "Refund"
    DISCOUNT = "discount", "Discount"
    UNLOCK = "unlock", "Unlock"


class InvoiceAuditLog(models.Model):
    """Immutable audit trail for financial records."""

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=20, choices=AuditAction.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    detail = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Audit log entries are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit log entries cannot be deleted.")


class ClinicSettings(models.Model):
    """Singleton clinic branding / payment settings for د. طيبة."""

    clinic_name_ar = models.CharField(max_length=120, default="د. طيبة")
    clinic_name_en = models.CharField(max_length=120, default="Dr. Taybah")
    currency_code = models.CharField(max_length=8, default="IQD")
    default_discount_percent = models.PositiveSmallIntegerField(default=20)
    master_qi_card_number = models.CharField(max_length=32, default="7113596071")
    calorie_target_reason_threshold_pct = models.PositiveSmallIntegerField(
        default=15,
        help_text="Require clinical reason when prescribed calories differ from TDEE by this %.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Clinic Settings"
        verbose_name_plural = "Clinic Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> ClinicSettings:
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self) -> str:
        return self.clinic_name_ar
