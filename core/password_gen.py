"""
core/password_gen.py — Cryptographically secure password generator.

Dùng `secrets` module (CSPRNG), không phải `random`.
"""

from __future__ import annotations

import math
import secrets
import string
from dataclasses import dataclass


@dataclass
class PasswordConfig:
    length: int = 20
    use_upper: bool = True
    use_lower: bool = True
    use_digits: bool = True
    use_symbols: bool = True

    def charset(self) -> str:
        chars = ""
        if self.use_upper:
            chars += string.ascii_uppercase
        if self.use_lower:
            chars += string.ascii_lowercase
        if self.use_digits:
            chars += string.digits
        if self.use_symbols:
            chars += "!@#$%^&*()-_=+[]{};:,.<>?/"
        return chars


def generate(config: PasswordConfig) -> str:
    """Generate password theo config. Đảm bảo mỗi loại ký tự enabled đều có ít nhất 1."""
    if config.length < 4:
        raise ValueError("Length phải >= 4")
    charset = config.charset()
    if not charset:
        raise ValueError("Phải enable ít nhất 1 loại ký tự")

    # Ensure at least 1 of each enabled type
    required = []
    if config.use_upper:
        required.append(secrets.choice(string.ascii_uppercase))
    if config.use_lower:
        required.append(secrets.choice(string.ascii_lowercase))
    if config.use_digits:
        required.append(secrets.choice(string.digits))
    if config.use_symbols:
        required.append(secrets.choice("!@#$%^&*()-_=+[]{};:,.<>?/"))

    remaining = config.length - len(required)
    password_chars = required + [secrets.choice(charset) for _ in range(remaining)]

    # Shuffle (Fisher-Yates với secrets)
    for i in range(len(password_chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        password_chars[i], password_chars[j] = password_chars[j], password_chars[i]

    return "".join(password_chars)


def entropy_bits(password: str, charset_size: int) -> float:
    """Tính entropy = log2(charset^length)."""
    if charset_size <= 1 or not password:
        return 0.0
    return len(password) * math.log2(charset_size)


def strength_label(bits: float) -> str:
    """Phân loại độ mạnh."""
    if bits < 28:
        return "Rất yếu"
    if bits < 36:
        return "Yếu"
    if bits < 60:
        return "Trung bình"
    if bits < 80:
        return "Mạnh"
    return "Rất mạnh"
