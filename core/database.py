"""
core/database.py — SQLite wrapper cho PassVault.

Schema:
  vault_meta (key, value)  — salt, kdf_params, kdf_check_blob
  items       (id, name, url, username, password_enc, totp_secret_enc,
               notes_enc, created_at, updated_at)

Sensitive fields (password, totp_secret, notes) lưu dưới dạng
encrypted blob. Metadata (name, url, username) lưu plaintext để search.
"""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .crypto import VaultCrypto


@dataclass
class VaultItem:
    id: str
    name: str
    url: str
    username: str
    password: str  # Decrypted in memory
    totp_secret: str  # Decrypted in memory, "" nếu không có
    notes: str
    created_at: float
    updated_at: float


SCHEMA = """
CREATE TABLE IF NOT EXISTS vault_meta (
    key   TEXT PRIMARY KEY,
    value BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    url           TEXT DEFAULT '',
    username      TEXT DEFAULT '',
    password_enc  BLOB NOT NULL,
    totp_secret_enc BLOB,
    notes_enc     BLOB,
    created_at    REAL NOT NULL,
    updated_at    REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_name ON items(name);
CREATE INDEX IF NOT EXISTS idx_items_updated ON items(updated_at DESC);
"""


class Database:
    def __init__(self, db_path: Path) -> None:
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(db_path), check_same_thread=False, isolation_level=None
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---------- Metadata ----------

    def get_meta(self, key: str) -> Optional[bytes]:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM vault_meta WHERE key=?", (key,)
            ).fetchone()
        return row[0] if row else None

    def set_meta(self, key: str, value: bytes) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO vault_meta (key, value) VALUES (?,?)",
                (key, value),
            )

    def has_vault(self) -> bool:
        return self.get_meta("salt") is not None

    def init_vault(self, salt: bytes, check_blob: bytes) -> None:
        self.set_meta("salt", salt)
        self.set_meta("check_blob", check_blob)

    def get_salt(self) -> Optional[bytes]:
        return self.get_meta("salt")

    def get_check_blob(self) -> Optional[bytes]:
        return self.get_meta("check_blob")

    # ---------- Items ----------

    def insert_item(self, item: VaultItem, crypto: VaultCrypto) -> None:
        now = time.time()
        with self._lock:
            self._conn.execute(
                """INSERT INTO items (id, name, url, username, password_enc,
                   totp_secret_enc, notes_enc, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    item.id, item.name, item.url, item.username,
                    crypto.encrypt_str(item.password),
                    crypto.encrypt_str(item.totp_secret) if item.totp_secret else None,
                    crypto.encrypt_str(item.notes) if item.notes else None,
                    now, now,
                ),
            )

    def update_item(self, item: VaultItem, crypto: VaultCrypto) -> None:
        now = time.time()
        with self._lock:
            self._conn.execute(
                """UPDATE items SET name=?, url=?, username=?, password_enc=?,
                   totp_secret_enc=?, notes_enc=?, updated_at=?
                   WHERE id=?""",
                (
                    item.name, item.url, item.username,
                    crypto.encrypt_str(item.password),
                    crypto.encrypt_str(item.totp_secret) if item.totp_secret else None,
                    crypto.encrypt_str(item.notes) if item.notes else None,
                    now, item.id,
                ),
            )

    def delete_item(self, item_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM items WHERE id=?", (item_id,))

    def list_item_metadata(self) -> List[tuple]:
        """List items without decrypting — cho UI list/search."""
        with self._lock:
            return self._conn.execute(
                """SELECT id, name, url, username,
                          totp_secret_enc IS NOT NULL AS has_totp,
                          updated_at
                   FROM items ORDER BY updated_at DESC"""
            ).fetchall()

    def get_item_encrypted(self, item_id: str) -> Optional[dict]:
        """Fetch 1 item với fields chưa decrypt."""
        with self._lock:
            row = self._conn.execute(
                """SELECT id, name, url, username, password_enc,
                          totp_secret_enc, notes_enc, created_at, updated_at
                   FROM items WHERE id=?""",
                (item_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row[0], "name": row[1], "url": row[2], "username": row[3],
            "password_enc": row[4], "totp_secret_enc": row[5], "notes_enc": row[6],
            "created_at": row[7], "updated_at": row[8],
        }

    def decrypt_item(self, item_id: str, crypto: VaultCrypto) -> Optional[VaultItem]:
        enc = self.get_item_encrypted(item_id)
        if not enc:
            return None
        return VaultItem(
            id=enc["id"],
            name=enc["name"],
            url=enc["url"],
            username=enc["username"],
            password=crypto.decrypt_str(enc["password_enc"]),
            totp_secret=crypto.decrypt_str(enc["totp_secret_enc"]) if enc["totp_secret_enc"] else "",
            notes=crypto.decrypt_str(enc["notes_enc"]) if enc["notes_enc"] else "",
            created_at=enc["created_at"],
            updated_at=enc["updated_at"],
        )

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
