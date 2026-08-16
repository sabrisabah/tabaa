from django.contrib import admin

from apps.billing.models import (
    ClinicService,
    ClinicSettings,
    Invoice,
    InvoiceAuditLog,
    InvoiceLine,
    ServicePriceVariant,
)


class ServicePriceVariantInline(admin.TabularInline):
    model = ServicePriceVariant
    extra = 0


@admin.register(ClinicService)
class ClinicServiceAdmin(admin.ModelAdmin):
    list_display = ("code", "name_ar", "base_price_iqd", "category", "is_active", "sort_order")
    list_filter = ("category", "is_active", "has_price_variants")
    search_fields = ("code", "name_ar", "name_en")
    inlines = [ServicePriceVariantInline]


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = ("line_total_iqd",)


class InvoiceAuditInline(admin.TabularInline):
    model = InvoiceAuditLog
    extra = 0
    readonly_fields = ("action", "actor", "detail", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "patient",
        "total_due_iqd",
        "payment_status",
        "payment_method",
        "created_at",
    )
    list_filter = ("payment_status", "payment_method")
    search_fields = ("invoice_number", "patient_name_snapshot", "patient__username")
    inlines = [InvoiceLineInline, InvoiceAuditInline]
    readonly_fields = ("invoice_number", "subtotal_iqd", "discount_amount_iqd", "total_due_iqd")


@admin.register(ClinicSettings)
class ClinicSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not ClinicSettings.objects.exists()
