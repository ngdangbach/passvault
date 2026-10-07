"""
core/vault.py — Vault session manager.

Khi unlock thành công → tạo Vault object chứa master_key trong memory.
Mọi encrypt/decrypt đi qua VaultCrypto với master_key này.
Lock → xóa master_key khỏi memory (best-effort).
"""

from __future__ import annotations

import secrets
import time
import uuid
from pathlib import Path
from typing import List, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .crypto import (
    CryptoError, VaultCrypto, derive_key, generate_salt, generate_master_key
)
from .database import Database, VaultItem


class Vault:
    """Một unlocked session. master_key chỉ tồn tại trong memory."""

    def __init__(self, db: Database, crypto: VaultCrypto) -> None:
        self.db = db
        self.crypto = crypto
        self._unlocked_at = time.time()

    # ---------- CRUD ----------

    def list_items(self) -> List[dict]:
        """Trả về metadata cho UI (không decrypt sensitive fields)."""
        return [
            {
                "id": row[0], "name": row[1], "url": row[2], "username": row[3],
                "has_totp": bool(row[4]), "updated_at": row[5],
            }
            for row in self.db.list_item_metadata()
        ]

    def get_item(self, item_id: str) -> Optional[VaultItem]:
        return self.db.decrypt_item(item_id, self.crypto)

    def add_item(self, name: str, url: str, username: str,
                 password: str, totp_secret: str = "", notes: str = "") -> str:
        item = VaultItem(
            id=uuid.uuid4().hex,
            name=name, url=url, username=username,
            password=password, totp_secret=totp_secret, notes=notes,
            created_at=time.time(), updated_at=time.time(),
        )
        self.db.insert_item(item, self.crypto)
        return item.id

    def update_item(self, item_id: str, name: str, url: str, username: str,
                    password: str, totp_secret: str = "", notes: str = "") -> None:
        existing = self.db.get_item_encrypted(item_id)
        if not existing:
            return
        item = VaultItem(
            id=item_id, name=name, url=url, username=username,
            password=password, totp_secret=totp_secret, notes=notes,
            created_at=existing["created_at"], updated_at=time.time(),
        )
        self.db.update_item(item, self.crypto)

    def delete_item(self, item_id: str) -> None:
        self.db.delete_item(item_id)

    def lock(self) -> None:
        """Xóa crypto context khỏi memory."""
        if self.crypto and self.crypto.master_key:
            self.crypto.master_key = b"\x00" * len(self.crypto.master_key)
        self.crypto = None  # type: ignore


# ---------- Crypto helpers ----------

def _wrap_master_key(master_key: bytes, derived_key: bytes) -> bytes:
    """Wrap master_key bằng derived_key từ master password."""
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(derived_key).encrypt(nonce, master_key, None)


def _make_check_blob(derived_key: bytes) -> bytes:
    """Check blob dùng để verify password nhanh trước khi unwrap master key."""
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(derived_key).encrypt(
        nonce, b"PassVault::CHECK::v1", None
    )


def _verify_check_blob(derived_key: bytes, check_blob: bytes) -> bool:
    """Return True nếu derived_key verify được check_blob."""
    try:
        nonce = check_blob[:12]
        ct = check_blob[12:]
        plaintext = AESGCM(derived_key).decrypt(nonce, ct, None)
        return plaintext == b"PassVault::CHECK::v1"
    except Exception:
        return False


# ---------- Lifecycle helpers ----------

def create_new_vault(db: Database, master_password: str) -> Vault:
    """Tạo vault mới — generate salt + master key + KDF check blob."""
    salt = generate_salt()
    db.set_meta("salt", salt)

    derived_key = derive_key(master_password, salt)
    master_key = generate_master_key()

    db.set_meta("wrapped_key", _wrap_master_key(master_key, derived_key))
    db.set_meta("check_blob", _make_check_blob(derived_key))

    return Vault(db, VaultCrypto(master_key=master_key))


def unlock_existing_vault(db: Database, master_password: str) -> Optional[Vault]:
    """Verify password + unwrap master key. Return None nếu sai."""
    salt = db.get_salt()
    wrapped = db.get_meta("wrapped_key")
    check_blob = db.get_meta("check_blob")
    if not (salt and wrapped and check_blob):
        return None

    derived_key = derive_key(master_password, salt)

    if not _verify_check_blob(derived_key, check_blob):
        return None

    try:
        nonce = wrapped[:12]
        ct = wrapped[12:]
        master_key = AESGCM(derived_key).decrypt(nonce, ct, None)
    except Exception:
        return None

    return Vault(db, VaultCrypto(master_key=master_key))


def change_master_password(
    db: Database,
    old_password: str,
    new_password: str,
) -> Optional[Vault]:
    """Change master password. Re-wraps master_key với new derived_key.

    Returns new Vault session if successful, None nếu old_password sai.
    Vault items KHÔNG cần re-encrypt vì chúng được encrypt với master_key
    (không đổi) — chỉ wrap key đổi.

    Salt được GIỮ NGUYÊN (không generate mới) để tránh phải update mọi
    derived references.

    Thứ tự:
      1. Unlock với old_password (verify + unwrap master_key)
      2. Derive new key từ new_password + salt
      3. Re-wrap master_key với new derived_key
      4. Tạo check_blob mới
      5. Update DB
      6. Clear old vault, return new vault session
    """
    # Step 1: Verify old password
    old_vault = unlock_existing_vault(db, old_password)
    if old_vault is None:
        return None

    master_key = old_vault.crypto.master_key
    salt = db.get_salt()

    # Step 2: Derive new key
    new_derived_key = derive_key(new_password, salt)

    # Step 3-4: Re-wrap + new check blob
    db.set_meta("wrapped_key", _wrap_master_key(master_key, new_derived_key))
    db.set_meta("check_blob", _make_check_blob(new_derived_key))

    # Step 5: Clear old vault session
    old_vault.lock()

    # Step 6: Return new session (master_key unchanged - chỉ re-wrapped)
    return Vault(db, VaultCrypto(master_key=master_key))
