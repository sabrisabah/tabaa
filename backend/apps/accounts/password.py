from __future__ import annotations

import re

# 4-character clinic PIN: digits and/or English letters.
AUTH_PASSWORD_RE = re.compile(r"^[A-Za-z0-9]{4}$")


def is_valid_auth_password(value: str) -> bool:
    return bool(AUTH_PASSWORD_RE.fullmatch(value or ""))
