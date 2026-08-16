from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.subscriptions.models import AdminAlert, Subscription
from apps.subscriptions.services.messaging import (
    expiry_warning_whatsapp_body,
    expiry_whatsapp_body,
    queue_whatsapp,
)
from apps.mealplans.services.weekly import apply_weight_loss_daily_targets

# Warn this many days before ends_at (inclusive of that calendar day).
WARNING_DAYS_BEFORE = 3


def _display_name(user) -> str:
    profile = getattr(user, "profile", None)
    if profile and profile.full_name:
        return profile.full_name
    return user.get_username()


def grant_paid_meal_access(
    *,
    subscription: Subscription,
    transaction_id: str = "",
    note: str = "",
) -> Subscription:
    """
    Confirm payment and immediately open the weekly meal program.

    Meals scale to the subscriber's daily fat-loss goal (or the physician plan).
    """
    already_open = (
        subscription.status == Subscription.Status.ACTIVE and subscription.is_access_granted
    )
    if not already_open:
        if not subscription.paid_at or subscription.status != Subscription.Status.ACTIVE:
            subscription.mark_paid(transaction_id=transaction_id, note=note)
        subscription.activate()
    apply_weight_loss_daily_targets(subscription.user)
    subscription.refresh_from_db()
    return subscription


def send_expiry_warning(sub: Subscription) -> None:
    """Notify user (WhatsApp) + system (AdminAlert) that access ends on a specific day."""
    if sub.expiry_warning_sent_at:
        return
    name = _display_name(sub.user)
    end_date = timezone.localtime(sub.ends_at).strftime("%Y/%m/%d") if sub.ends_at else "—"
    plan_name = sub.plan.name_ar
    body = expiry_warning_whatsapp_body(
        name=name,
        plan_name=plan_name,
        end_date=end_date,
    )
    msg = queue_whatsapp(
        user=sub.user,
        phone=sub.user.username,
        body=body,
        subscription=sub,
    )
    AdminAlert.objects.create(
        user=sub.user,
        subscription=sub,
        kind=AdminAlert.Kind.EXPIRY_WARNING,
        title=f"تنبيه نفاد اشتراك: {name}",
        body=(
            f"الهاتف: {sub.user.username}\n"
            f"الباقة: {plan_name}\n"
            f"تاريخ النفاد: {end_date}\n"
            f"تم إرسال واتساب للمشترك.\n"
            f"رابط: {msg.deep_link}"
        ),
    )
    sub.expiry_warning_sent_at = timezone.now()
    sub.save(update_fields=["expiry_warning_sent_at", "updated_at"])


def expire_subscription(sub: Subscription) -> None:
    """Mark expired, revoke meal access, WhatsApp + system alert. Renew payment reopens meals."""
    if sub.status == Subscription.Status.EXPIRED:
        return
    sub.status = Subscription.Status.EXPIRED
    sub.save(update_fields=["status", "updated_at"])

    name = _display_name(sub.user)
    end_date = timezone.localtime(sub.ends_at).strftime("%Y/%m/%d") if sub.ends_at else "—"
    plan_name = sub.plan.name_ar
    body = expiry_whatsapp_body(name=name, plan_name=plan_name, end_date=end_date)
    msg = queue_whatsapp(
        user=sub.user,
        phone=sub.user.username,
        body=body,
        subscription=sub,
    )
    AdminAlert.objects.create(
        user=sub.user,
        subscription=sub,
        kind=AdminAlert.Kind.SUBSCRIPTION_EXPIRED,
        title=f"انتهى اشتراك {name}",
        body=(
            f"الهاتف: {sub.user.username}\n"
            f"الباقة: {plan_name}\n"
            f"تاريخ النفاد: {end_date}\n"
            f"تم إيقاف الوجبات. يلزم اشتراك جديد ثم يُفتح البرنامج تلقائياً بعد تأكيد الدفع.\n"
            f"واتساب: {msg.deep_link}"
        ),
    )


def process_subscription_lifecycle(*, user=None) -> dict:
    """
    Run warnings + expirations.

    If user is set, only that user's active subscriptions (for on-request sync).
    Otherwise process all (management command / cron).
    """
    now = timezone.now()
    warn_before = now + timedelta(days=WARNING_DAYS_BEFORE)
    qs = Subscription.objects.filter(status=Subscription.Status.ACTIVE).select_related(
        "user", "plan"
    )
    if user is not None:
        qs = qs.filter(user=user)

    warned = 0
    expired = 0
    for sub in qs:
        if not sub.ends_at:
            continue
        if sub.ends_at <= now:
            expire_subscription(sub)
            expired += 1
            continue
        if sub.ends_at <= warn_before and not sub.expiry_warning_sent_at:
            send_expiry_warning(sub)
            warned += 1
    return {"warned": warned, "expired": expired}
