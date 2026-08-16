from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.billing.models import (
    ClinicService,
    ClinicSettings,
    DiscountReason,
    Invoice,
    InvoiceAuditLog,
    InvoiceLine,
    PaymentMethod,
    ServicePriceVariant,
)

User = get_user_model()


class ServicePriceVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePriceVariant
        fields = [
            "id",
            "code",
            "label_ar",
            "label_en",
            "price_iqd",
            "is_active",
            "sort_order",
            "effective_from",
        ]


class ClinicServiceSerializer(serializers.ModelSerializer):
    variants = ServicePriceVariantSerializer(many=True, read_only=True)

    class Meta:
        model = ClinicService
        fields = [
            "id",
            "code",
            "name_ar",
            "name_en",
            "category",
            "unit_label_ar",
            "base_price_iqd",
            "allow_quantity",
            "is_doctor_visit",
            "is_free_follow_up",
            "has_price_variants",
            "is_active",
            "sort_order",
            "notes",
            "variants",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "service",
            "variant",
            "service_name_snapshot",
            "variant_label_snapshot",
            "unit_price_iqd",
            "quantity",
            "line_total_iqd",
            "sort_order",
        ]
        read_only_fields = fields


class InvoiceAuditLogSerializer(serializers.ModelSerializer):
    actor_phone = serializers.CharField(source="actor.username", read_only=True, default="")

    class Meta:
        model = InvoiceAuditLog
        fields = ["id", "action", "actor", "actor_phone", "detail", "created_at"]
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceLineSerializer(many=True, read_only=True)
    audit_logs = InvoiceAuditLogSerializer(many=True, read_only=True)
    patient_phone = serializers.CharField(source="patient.username", read_only=True)
    created_by_phone = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "patient",
            "patient_phone",
            "patient_name_snapshot",
            "patient_file_snapshot",
            "created_by",
            "created_by_phone",
            "subtotal_iqd",
            "discount_percent",
            "discount_amount_iqd",
            "discount_reason",
            "discount_reason_custom",
            "discount_entered_by",
            "discount_approved_by",
            "discount_approved_at",
            "total_due_iqd",
            "amount_paid_iqd",
            "payment_method",
            "payment_status",
            "show_discount_reason_on_receipt",
            "notes",
            "is_locked",
            "created_at",
            "updated_at",
            "paid_at",
            "items",
            "audit_logs",
        ]
        read_only_fields = [
            "id",
            "invoice_number",
            "subtotal_iqd",
            "discount_amount_iqd",
            "total_due_iqd",
            "is_locked",
            "created_at",
            "updated_at",
            "paid_at",
            "items",
            "audit_logs",
        ]


class InvoiceCreateSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    discount_percent = serializers.FloatField(required=False, min_value=0, max_value=100)
    discount_reason = serializers.ChoiceField(
        choices=DiscountReason.choices,
        required=False,
        allow_blank=True,
        default="",
    )
    discount_reason_custom = serializers.CharField(required=False, allow_blank=True, default="")
    discount_approved_by_id = serializers.IntegerField(required=False, allow_null=True)
    show_discount_reason_on_receipt = serializers.BooleanField(required=False, default=False)
    items = serializers.ListField(child=serializers.DictField(), min_length=1)

    def validate_patient_id(self, value):
        if not User.objects.filter(pk=value).exists():
            raise serializers.ValidationError("المريض غير موجود.")
        return value


class PaymentSerializer(serializers.Serializer):
    amount_paid_iqd = serializers.IntegerField(min_value=0)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices)


class DiscountSerializer(serializers.Serializer):
    discount_percent = serializers.FloatField(min_value=0.01, max_value=100)
    discount_reason = serializers.ChoiceField(choices=DiscountReason.choices)
    discount_reason_custom = serializers.CharField(required=False, allow_blank=True, default="")
    discount_approved_by_id = serializers.IntegerField(required=False, allow_null=True)


class ClinicSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicSettings
        fields = [
            "clinic_name_ar",
            "clinic_name_en",
            "currency_code",
            "default_discount_percent",
            "master_qi_card_number",
            "calorie_target_reason_threshold_pct",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]
