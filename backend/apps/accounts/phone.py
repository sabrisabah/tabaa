from __future__ import annotations

import re

# Iraqi mobile local form: 07 + 9 digits (11 total), e.g. 07901234567
IRAQ_PHONE_RE = re.compile(r"^07\d{9}$")


def normalize_iraq_phone(value: str) -> str:
    """
    Normalize common Iraq mobile inputs to local 11-digit form (07XXXXXXXXX).

    Accepts: 07XXXXXXXXX, 7XXXXXXXXX, 9647XXXXXXXXX, +9647XXXXXXXXX,
    and formats with spaces or dashes.
    """
    raw = (value or "").strip()
    digits = re.sub(r"\D", "", raw)

    if digits.startswith("00"):
        digits = digits[2:]

    if digits.startswith("964"):
        digits = digits[3:]

    if digits.startswith("7") and len(digits) == 10:
        digits = f"0{digits}"

    return digits


def is_valid_iraq_phone(value: str) -> bool:
    return bool(IRAQ_PHONE_RE.fullmatch(value or ""))


def validate_iraq_phone(value: str) -> str:
    normalized = normalize_iraq_phone(value)
    if not is_valid_iraq_phone(normalized):
        raise ValueError(
            "Enter a valid Iraqi mobile number (07XXXXXXXXX).",
        )
    return normalized
