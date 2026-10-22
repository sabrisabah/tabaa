from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import UserProfile
from apps.accounts.permissions import get_clinic_role
from apps.billing.models import (
    AuditAction,
    ClinicService,
    DiscountReason,
    Invoice,
    InvoiceAuditLog,
    InvoiceLine,
    PaymentMethod,
    PaymentStatus,
    ServicePriceVariant,
)

User = get_user_model()


def patient_has_paid_doctor_visit(patient) -> bool:
    return InvoiceLine.objects.filter(
        invoice__patient=patient,
        invoice__payment_status=PaymentStatus.PAID,
        service__is_doctor_visit=True,
    ).exists()


def resolve_unit_price(*, service: ClinicService, variant: ServicePriceVariant | None) -> int:
    if variant:
        if variant.service_id != service.id:
            raise ValidationError({"variant": "Variant does not belong to this service."})
        if not variant.is_active:
            raise ValidationError({"variant": "Variant is inactive."})
        return int(variant.price_iqd)
    return int(service.base_price_iqd)


@transaction.atomic
def create_invoice(
    *,
    patient,
    created_by,
    items: list[dict],
    notes: str = "",
    discount_percent: float | None = None,
    discount_reason: str = "",
    discount_reason_custom: str = "",
    discount_approved_by=None,
    show_discount_reason_on_receipt: bool = False,
) -> Invoice:
    if not items:
        raise ValidationError({"items": "At least one service line is required."})

    profile = getattr(patient, "profile", None)
    patient_name = ""
    patient_file = ""
    if profile:
        patient_name = profile.full_name or patient.username
        patient_file = profile.patient_file_number

    invoice = Invoice(
        invoice_number=Invoice.next_invoice_number(),
        patient=patient,
        patient_name_snapshot=patient_name,
        patient_file_snapshot=patient_file,
        created_by=created_by,
        notes=notes or "",
        show_discount_reason_on_receipt=show_discount_reason_on_receipt,
    )
    invoice.save()

    has_paid_visit = patient_has_paid_doctor_visit(patient)

    for index, raw in enumerate(items):
        service_id = raw.get("service_id")
        variant_id = raw.get("variant_id")
        quantity = int(raw.get("quantity") or 1)
        if quantity < 1:
            raise ValidationError({"items": "Quantity must be at least 1."})

        try:
            service = ClinicService.objects.get(pk=service_id, is_active=True)
        except ClinicService.DoesNotExist as exc:
            raise ValidationError({"items": f"Unknown service id {service_id}."}) from exc

        variant = None
        if variant_id:
            try:
                variant = ServicePriceVariant.objects.get(pk=variant_id, is_active=True)
            except ServicePriceVariant.DoesNotExist as exc:
                raise ValidationError({"items": f"Unknown variant id {variant_id}."}) from exc

        # Free follow-up rule: if doctor visit requested and patient already paid once → free follow-up
        if service.is_doctor_visit and has_paid_visit:
            follow_up = ClinicService.objects.filter(is_free_follow_up=True, is_active=True).first()
            if follow_up:
                service = follow_up
                variant = None
                quantity = 1

        if service.is_free_follow_up and not has_paid_visit and not service.is_doctor_visit:
            # Allow explicit free follow-up only after a paid visit exists
            if not patient_has_paid_doctor_visit(patient):
                raise ValidationError(
                    {
                        "items": "لا يمكن تسجيل متابعة مجانية قبل وجود كشفية مدفوعة للمريض.",
                    },
                )

        if service.has_price_variants and variant is None:
            raise ValidationError(
                {"items": f"الخدمة «{service.name_ar}» تتطلب اختيار جرعة/متغير سعر."},
            )

        if not service.allow_quantity:
            quantity = 1

        unit_price = 0 if service.is_free_follow_up else resolve_unit_price(service=service, variant=variant)
        InvoiceLine.objects.create(
            invoice=invoice,
            service=service,
            variant=variant,
            service_name_snapshot=service.name_ar,
            variant_label_snapshot=variant.label_ar if variant else "",
            unit_price_iqd=unit_price,
            quantity=quantity,
            sort_order=index,
        )

    invoice.recalculate(save=True)

    if discount_percent is not None and float(discount_percent) > 0:
        approved = discount_approved_by
        if approved is None and get_clinic_role(created_by) == UserProfile.ClinicRole.DOCTOR:
            approved = created_by
        apply_discount(
            invoice=invoice,
            percent=float(discount_percent),
            reason=discount_reason or DiscountReason.CUSTOM,
            reason_custom=discount_reason_custom,
            entered_by=created_by,
            approved_by=approved,
        )

    InvoiceAuditLog.objects.create(
        invoice=invoice,
        action=AuditAction.CREATE,
        actor=created_by,
        detail=f"Created invoice {invoice} with {invoice.items.count()} lines.",
    )
    return invoice


@transaction.atomic
def apply_discount(
    *,
    invoice: Invoice,
    percent: float,
    reason: str,
    reason_custom: str,
    entered_by,
    approved_by=None,
) -> Invoice:
    if invoice.is_locked:
        raise ValidationError("الفاتورة مقفلة ولا يمكن تعديل الخصم.")
    if invoice.subtotal_iqd == 0:
        raise ValidationError("لا يُطبَّق خصم على فاتورة مجموعها صفر.")
    if invoice.discount_percent and float(invoice.discount_percent) > 0:
        raise ValidationError("لا يمكن جمع أكثر من خصم على نفس الفاتورة.")
    if percent <= 0 or percent > 100:
        raise ValidationError({"discount_percent": "نسبة الخصم يجب أن تكون بين 0 و 100."})

    role = get_clinic_role(entered_by)
    if role == UserProfile.ClinicRole.SECRETARY and approved_by is None:
        raise ValidationError("خصم السكرتيرة يتطلب موافقة الطبيبة.")

    if approved_by is not None and get_clinic_role(approved_by) != UserProfile.ClinicRole.DOCTOR:
        if not getattr(approved_by, "is_superuser", False):
            raise ValidationError("الموافقة على الخصم متاحة للطبيبة/المدير فقط.")

    invoice.discount_percent = percent
    invoice.discount_reason = reason or DiscountReason.CUSTOM
    invoice.discount_reason_custom = reason_custom or ""
    invoice.discount_entered_by = entered_by
    invoice.discount_approved_by = approved_by
    invoice.discount_approved_at = timezone.now() if approved_by else None
    invoice.recalculate(save=True)

    InvoiceAuditLog.objects.create(
        invoice=invoice,
        action=AuditAction.DISCOUNT,
        actor=entered_by,
        detail=(
            f"Discount {percent}% reason={invoice.discount_reason} "
            f"amount={invoice.discount_amount_iqd} approved_by={approved_by}"
        ),
    )
    return invoice


@transaction.atomic
def record_payment(
    *,
    invoice: Invoice,
    amount_paid_iqd: int,
    payment_method: str,
    actor,
) -> Invoice:
    if invoice.payment_status in {PaymentStatus.CANCELLED, PaymentStatus.REFUNDED}:
        raise ValidationError("لا يمكن الدفع على فاتورة ملغاة أو مستردة.")
    if invoice.is_locked and invoice.payment_status == PaymentStatus.PAID:
        raise ValidationError("الفاتورة مدفوعة ومقفلة.")
    if payment_method not in PaymentMethod.values:
        raise ValidationError({"payment_method": "طريقة الدفع غير صالحة."})
    if amount_paid_iqd < 0:
        raise ValidationError({"amount_paid_iqd": "المبلغ المدفوع غير صالح."})

    invoice.payment_method = payment_method
    invoice.amount_paid_iqd = int(amount_paid_iqd)

    if invoice.amount_paid_iqd <= 0:
        invoice.payment_status = PaymentStatus.UNPAID
        invoice.paid_at = None
        invoice.is_locked = False
    elif invoice.amount_paid_iqd < invoice.total_due_iqd:
        invoice.payment_status = PaymentStatus.PARTIAL
        invoice.paid_at = None
        invoice.is_locked = False
    else:
        invoice.payment_status = PaymentStatus.PAID
        invoice.paid_at = timezone.now()
        invoice.is_locked = True

    invoice.save(
        update_fields=[
            "payment_method",
            "amount_paid_iqd",
            "payment_status",
            "paid_at",
            "is_locked",
            "updated_at",
        ],
    )
    InvoiceAuditLog.objects.create(
        invoice=invoice,
        action=AuditAction.PAY,
        actor=actor,
        detail=f"Paid {amount_paid_iqd} via {payment_method}; status={invoice.payment_status}",
    )
    return invoice


@transaction.atomic
def cancel_or_refund_invoice(
    *,
    invoice: Invoice,
    actor,
    action: str,
    reason: str,
) -> Invoice:
    if get_clinic_role(actor) != UserProfile.ClinicRole.DOCTOR and not actor.is_superuser:
        raise ValidationError("إلغاء/استرداد الفواتير متاح للطبيبة فقط.")
    if action == "cancel":
        invoice.payment_status = PaymentStatus.CANCELLED
        audit = AuditAction.CANCEL
    elif action == "refund":
        invoice.payment_status = PaymentStatus.REFUNDED
        audit = AuditAction.REFUND
    else:
        raise ValidationError("الإجراء غير معروف.")
    invoice.is_locked = True
    invoice.save(update_fields=["payment_status", "is_locked", "updated_at"])
    InvoiceAuditLog.objects.create(
        invoice=invoice,
        action=audit,
        actor=actor,
        detail=reason or "",
    )
    return invoice
