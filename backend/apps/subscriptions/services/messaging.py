from __future__ import annotations

from urllib.parse import quote

from django.conf import settings

from apps.subscriptions.models import OutboundMessage


def _digits_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if digits.startswith("0") and len(digits) == 11:
        return f"964{digits[1:]}"
    if digits.startswith("964"):
        return digits
    return digits


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
