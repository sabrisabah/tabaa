from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model

from apps.subscriptions.models import AdminAlert, OutboundMessage


def _digits_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if digits.startswith("0") and len(digits) == 11:
        return f"964{digits[1:]}"
    if digits.startswith("964"):
        return digits
    return digits


def subscriber_display_name(user, fallback: str = "") -> str:
    from django.core.exceptions import ObjectDoesNotExist

    try:
        profile = user.profile
    except ObjectDoesNotExist:
        profile = None
    if profile and getattr(profile, "full_name", None):
        return profile.full_name
    if fallback:
        return fallback
    return user.get_username()


def monthly_subscription_number(subscription) -> str:
    """Human-facing monthly subscription number shown to staff and the payer."""
    if subscription is None:
        return "—"
    return (subscription.payment_reference or "").strip() or str(subscription.id)


def queue_whatsapp(*, user, phone: str, body: str, subscription=None) -> OutboundMessage:
    intl = _digits_phone(phone or user.username)
    deep_link = f"https://wa.me/{intl}?text={quote(body)}"
    status = (
        OutboundMessage.Status.SENT
        if getattr(settings, "WHATSAPP_ENABLED", True)
        else OutboundMessage.Status.QUEUED
    )
    return OutboundMessage.objects.create(
        user=user,
        subscription=subscription,
        channel=OutboundMessage.Channel.WHATSAPP,
        phone=intl,
        body=body,
        deep_link=deep_link,
        status=status,
    )


def expiry_whatsapp_body(*, name: str, plan_name: str, end_date: str = "") -> str:
    greeting = name or "مشتركنا"
    when = f" بتاريخ {end_date}" if end_date else ""
    return (
        f"مرحباً {greeting}، انتهى اشتراكك في باقة «{plan_name}»{when}. "
        "تم إيقاف برنامج الوجبات. للاشتراك مرة ثانية ادفع من التطبيق، "
        "ثم ينتظر موافقة مشرف النظام لإعادة فتح الدخول."
    )


def expiry_warning_whatsapp_body(*, name: str, plan_name: str, end_date: str) -> str:
    greeting = name or "مشتركنا"
    return (
        f"مرحباً {greeting}، تنبيه: اشتراكك في باقة «{plan_name}» "
        f"سينتهي في يوم {end_date} حسب جدول الباقة. "
        "جدّد الاشتراك قبل النفاد لتستمر الوجبات بدون انقطاع، "
        "وبعد الدفع يلزم موافقة المشرف للتفعيل."
    )


def payment_received_patient_body(*, name: str, subscription_number: str) -> str:
    greeting = name or "مشتركنا"
    return (
        f"مرحباً {greeting}، تم استلام الدفع بنجاح. "
        f"رقم الاشتراك الشهري: {subscription_number}. "
        "تم الدفع وبانتظار موافقة الطبيب لفتح برنامج الوجبات."
    )


def payment_received_doctor_body(*, name: str, subscription_number: str, phone: str, amount_iqd=None) -> str:
    amount_line = f"المبلغ: {amount_iqd} د.ع. " if amount_iqd not in (None, "") else ""
    return (
        f"إشعار دفع: {name} قام بالدفع. "
        f"رقم الاشتراك الشهري: {subscription_number}. "
        f"الهاتف: {phone}. {amount_line}"
        "تم الدفع وبانتظار موافقة الطبيب لفتح برنامج الوجبات."
    )


def _doctor_users():
    from apps.accounts.models import UserProfile

    User = get_user_model()
    return list(User.objects.filter(profile__clinic_role=UserProfile.ClinicRole.DOCTOR))


def notify_payment_received(
    *,
    user,
    subscription=None,
    source: str = "",
    extra_lines: list[str] | None = None,
    is_renewal: bool = False,
    payer_name: str = "",
) -> AdminAlert:
    """
    Django + WhatsApp signals after a successful pay (card send / SuperQI).

    1. AdminAlert: this person paid (name + monthly subscription number).
    2. Messages: payment received, waiting for doctor approval to open meals.
    """
    name = payer_name or subscriber_display_name(user)
    sub_no = monthly_subscription_number(subscription)
    phone = user.get_username()
    amount = getattr(subscription, "amount_iqd", None)
    plan_name = ""
    if subscription is not None and getattr(subscription, "plan_id", None):
        plan_name = subscription.plan.name_ar

    kind = (
        AdminAlert.Kind.RENEWAL_REQUEST
        if is_renewal
        else AdminAlert.Kind.PAYMENT_CONFIRMED
    )
    title = f"{'تجديد' if is_renewal else 'قام بالدفع'}: {name} — {sub_no}"
    lines = [
        f"قام المشترك بالدفع ({source or 'التطبيق'}).",
        f"الاسم: {name}",
        f"رقم الاشتراك الشهري: {sub_no}",
        f"الهاتف: {phone}",
    ]
    if plan_name:
        lines.append(f"الباقة: {plan_name}")
    if amount is not None:
        lines.append(f"المبلغ: {amount} د.ع")
    if subscription is not None:
        lines.append(f"رقم السجل: {subscription.id}")
    if extra_lines:
        lines.extend(extra_lines)
    lines.append("تم الدفع وبانتظار موافقة الطبيب على فتح برنامج الوجبات.")
    body = "\n".join(lines)

    alert = AdminAlert.objects.create(
        user=user,
        subscription=subscription,
        kind=kind,
        title=title,
        body=body,
    )

    queue_whatsapp(
        user=user,
        phone=phone,
        body=payment_received_patient_body(name=name, subscription_number=sub_no),
        subscription=subscription,
    )

    doctor_body = payment_received_doctor_body(
        name=name,
        subscription_number=sub_no,
        phone=phone,
        amount_iqd=amount,
    )
    for doctor in _doctor_users():
        queue_whatsapp(
            user=doctor,
            phone=doctor.get_username(),
            body=doctor_body,
            subscription=subscription,
        )

    return alert
