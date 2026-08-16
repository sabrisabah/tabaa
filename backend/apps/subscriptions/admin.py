from django.contrib import admin, messages
from django.utils import timezone

from apps.subscriptions.models import (
    AdminAlert,
    CardPayment,
    OutboundMessage,
    PaymentNotification,
    PaymentSettings,
    SavedPaymentMethod,
    Subscription,
    SubscriptionPlan,
)


@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ("merchant_phone", "title_ar", "is_active", "updated_at")
    fields = (
        "merchant_phone",
        "title_ar",
        "title_en",
        "hint_ar",
        "hint_en",
        "merchant_label_ar",
        "merchant_label_en",
        "is_active",
        "updated_at",
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return not PaymentSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name_ar",
        "price_iqd",
        "duration_days",
        "meal_variety_level",
        "is_active",
    )
    list_filter = ("is_active",)
    prepopulated_fields = {"code": ("name_en",)}


@admin.action(description="Activate selected subscriptions (grant meal access)")
def activate_subscriptions(modeladmin, request, queryset):
    activated = 0
    for sub in queryset.select_related("plan"):
        if sub.status in {
            Subscription.Status.PAID_PENDING_ACTIVATION,
            Subscription.Status.PENDING_PAYMENT,
            Subscription.Status.EXPIRED,
            Subscription.Status.ACTIVE,
        }:
            if sub.status == Subscription.Status.PENDING_PAYMENT and not sub.paid_at:
                sub.paid_at = timezone.now()
                sub.save(update_fields=["paid_at", "updated_at"])
            # Recalculate window from plan duration (fills Ends at automatically).
            if sub.status == Subscription.Status.ACTIVE and sub.starts_at:
                sub.apply_plan_window(admin_user=request.user, prefer_existing_start=True)
                sub.save(
                    update_fields=[
                        "status",
                        "activated_at",
                        "starts_at",
                        "ends_at",
                        "activated_by",
                        "updated_at",
                    ]
                )
            else:
                sub.activate(admin_user=request.user)
            activated += 1
    messages.success(
        request,
        f"Activated {activated} subscription(s). Ends at = Starts at + plan days.",
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "plan",
        "status",
        "payment_reference",
        "amount_iqd",
        "starts_at",
        "ends_at",
        "duration_label",
        "created_at",
    )
    list_filter = ("status", "plan")
    search_fields = ("user__username", "payment_reference", "superqi_transaction_id")
    readonly_fields = ("created_at", "updated_at", "payment_reference", "plan_duration_hint")
    actions = [activate_subscriptions]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "plan",
                    "plan_duration_hint",
                    "status",
                    "payment_reference",
                    "amount_iqd",
                    "superqi_transaction_id",
                )
            },
        ),
        (
            "Activation window (auto from plan)",
            {
                "description": (
                    "عند اختيار Status = Active والحفظ: "
                    "يُحسب Ends at تلقائياً = Starts at + مدة الباقة (مثلاً 30 أو 90 يوم). "
                    "يظهر التقويم في الواجهة الرئيسية للمستخدم بعد التفعيل."
                ),
                "fields": (
                    "paid_at",
                    "activated_at",
                    "activated_by",
                    "starts_at",
                    "ends_at",
                    "admin_note",
                ),
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Plan days")
    def duration_label(self, obj):
        return f"{obj.plan.duration_days}d"

    @admin.display(description="Plan duration")
    def plan_duration_hint(self, obj):
        if not obj or not obj.plan_id:
            return "—"
        return (
            f"{obj.plan.name_ar} · {obj.plan.duration_days} يوم "
            f"({obj.plan.price_iqd:,} د.ع) — Ends at يُملأ تلقائياً عند التفعيل"
        )

    def save_model(self, request, obj, form, change):
        becoming_active = obj.status == Subscription.Status.ACTIVE
        if becoming_active:
            # Keep admin-entered Starts at if present; always derive Ends at from plan.
            obj.apply_plan_window(
                admin_user=request.user,
                prefer_existing_start=True,
            )
            if not obj.paid_at:
                obj.paid_at = timezone.now()
        super().save_model(request, obj, form, change)
        if becoming_active:
            self.message_user(
                request,
                (
                    f"تم التفعيل: من {obj.starts_at:%Y-%m-%d %H:%M} "
                    f"إلى {obj.ends_at:%Y-%m-%d %H:%M} "
                    f"({obj.plan.duration_days} يوم حسب الباقة)."
                ),
                level=messages.SUCCESS,
            )


@admin.register(PaymentNotification)
class PaymentNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment_reference",
        "payer_name",
        "amount_iqd",
        "transaction_id",
        "subscription",
        "processed",
        "created_at",
    )
    list_filter = ("processed",)
    search_fields = ("payment_reference", "transaction_id", "payer_name", "payer_address")
    readonly_fields = ("created_at", "raw_payload")


@admin.register(AdminAlert)
class AdminAlertAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "title", "user", "is_read", "created_at")
    list_filter = ("kind", "is_read")
    search_fields = ("title", "body", "user__username")
    readonly_fields = ("created_at",)
    actions = ["mark_read"]

    @admin.action(description="Mark selected alerts as read")
    def mark_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"Marked {updated} alert(s) as read.")


@admin.register(OutboundMessage)
class OutboundMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "channel", "phone", "status", "user", "created_at")
    list_filter = ("channel", "status")
    search_fields = ("phone", "body", "user__username")
    readonly_fields = ("created_at", "deep_link")


@admin.register(SavedPaymentMethod)
class SavedPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("user", "brand", "last4", "exp_month", "exp_year", "is_default", "created_at")
    search_fields = ("user__username", "last4", "gateway_token")
    readonly_fields = ("gateway_token", "created_at")


@admin.register(CardPayment)
class CardPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "gateway_order_id",
        "user",
        "amount_iqd",
        "status",
        "gateway_transaction_id",
        "card_brand",
        "card_last4",
        "paid_at",
    )
    list_filter = ("status", "gateway")
    search_fields = ("gateway_order_id", "gateway_transaction_id", "user__username", "card_last4")
    readonly_fields = ("created_at", "updated_at", "raw_gateway_status", "redirect_url")
