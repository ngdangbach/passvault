"""
core/crypto.py — Crypto layer.

Master password → Argon2id KDF → AES-256-GCM.
Mọi sensitive field lưu trong DB đều được encrypt bằng derived key.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from argon2 import low_level
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32
NONCE_LEN = 12


class CryptoError(Exception):
    """Sai password hoặc data bị tamper."""


@dataclass
class VaultCrypto:
    """Crypto context cho 1 unlocked session."""
    master_key: bytes  # 32 bytes — wrap bằng derived key từ master password

    def encrypt(self, plaintext: bytes, aad: bytes = b"") -> bytes:
        aesgcm = AESGCM(self.master_key)
        nonce = secrets.token_bytes(NONCE_LEN)
        return nonce + aesgcm.encrypt(nonce, plaintext, aad)

    def decrypt(self, blob: bytes, aad: bytes = b"") -> bytes:
        if len(blob) < NONCE_LEN + 16:
            raise CryptoError("Ciphertext too short")
        aesgcm = AESGCM(self.master_key)
        try:
            return aesgcm.decrypt(blob[:NONCE_LEN], blob[NONCE_LEN:], aad)
        except Exception as e:
            raise CryptoError(f"Decryption failed: {e}") from e

    def encrypt_str(self, text: str) -> bytes:
        return self.encrypt(text.encode("utf-8"))

    def decrypt_str(self, blob: bytes) -> str:
        return self.decrypt(blob).decode("utf-8")


def derive_key(master_password: str, salt: bytes) -> bytes:
    """Argon2id KDF. Tốn ~200ms."""
    return low_level.hash_secret_raw(
        secret=master_password.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=ARGON2_HASH_LEN,
        type=low_level.Type.ID,
    )


def generate_salt() -> bytes:
    return secrets.token_bytes(16)


def generate_master_key() -> bytes:
    return secrets.token_bytes(32)
