from __future__ import annotations

from django.conf import settings

from apps.subscriptions.models import PaymentSettings


def superqi_public_info() -> dict:
    cfg = PaymentSettings.load()
    phone = (cfg.merchant_phone or getattr(settings, "SUPERQI_MERCHANT_PHONE", "")).strip()
    return {
        "method": "superqi",
        "merchant_label": cfg.merchant_label_ar or cfg.merchant_label_en or "SuperQI",
        "merchant_label_ar": cfg.merchant_label_ar,
        "merchant_label_en": cfg.merchant_label_en,
        "merchant_phone": phone,
        "merchant_phone_clean": "".join(ch for ch in phone if ch.isdigit() or ch == "+"),
        "title_ar": cfg.title_ar,
        "title_en": cfg.title_en,
        "hint_ar": cfg.hint_ar,
        "hint_en": cfg.hint_en,
    }


def payment_instructions(*, amount_iqd: int, reference: str) -> dict[str, str]:
    info = superqi_public_info()
    phone = info["merchant_phone_clean"] or info["merchant_phone"]
    return {
        "instructions_ar": (
            f"حوّل {amount_iqd:,} دينار مباشرة إلى رقم سوبر كي {phone} "
            f"واكتب المرجع {reference} في ملاحظة التحويل، ثم اضغط «أكدّت التحويل»."
        ),
        "instructions_en": (
            f"Transfer {amount_iqd:,} IQD directly to SuperQI number {phone}, "
            f"include reference {reference} in the note, then tap “I transferred”."
        ),
    }
