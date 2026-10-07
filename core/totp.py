"""
core/totp.py — TOTP generator cho 2FA codes.

Dùng pyotp (RFC 6238 compliant). User nhập secret (dạng base32) khi add item.
"""

from __future__ import annotations

import pyotp
from typing import Tuple


def generate_code(secret: str) -> Tuple[str, int]:
    """
    Tạo TOTP code hiện tại.

    Returns:
        (code, seconds_remaining) — code là string 6 số,
        seconds_remaining là số giây trước khi code hết hạn.
    """
    totp = pyotp.TOTP(secret)
    code = totp.now()
    remaining = 30 - (int(pyotp.TOTP(secret).timecode(pyotp.TOTP(secret).time.time())) % 30) \
               if False else _seconds_remaining(totp)
    return code, remaining


def _seconds_remaining(totp: pyotp.TOTP) -> int:
    import time
    counter = int(time.time())
    seconds = counter % totp.interval
    return totp.interval - seconds


def verify_code(secret: str, code: str) -> bool:
    """Verify a 2FA code (cho testing)."""
    return pyotp.TOTP(secret).verify(code)


def normalize_secret(secret: str) -> str:
    """User thường paste secret có spaces/dashes — strip cho an toàn."""
    return secret.replace(" ", "").replace("-", "").upper().strip()
