"""
main.py — Entry point cho PassVault.

Modes:
  - Default: data ở %USERPROFILE%\\.passvault\\vault.db
  - Portable: data ở cùng folder với .exe (dùng cho USB)

Cách dùng portable:
  - Command line: PassVault.exe --portable
  - Hoặc đặt file "portable.flag" cạnh PassVault.exe
  - Hoặc set env var PASSVAULT_PORTABLE=1

Flow:
  1. Mở SQLite database
  2. Nếu vault chưa có: show UnlockDialog (mode = new) → create_new_vault
  3. Nếu vault đã có: show UnlockDialog (mode = unlock) → unlock_existing_vault
  4. Mở MainWindow với Vault session
  5. Khi lock/close → vault.lock() → clear master_key khỏi memory
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QApplication, QMessageBox

from core.database import Database
from core.vault import create_new_vault, unlock_existing_vault
from ui.main_window import MainWindow
from ui.theme import apply_theme_to_app
from ui.unlock_dialog import UnlockDialog


APP_NAME = "PassVault"


def is_portable_mode() -> bool:
    """Detect nếu user muốn chạy portable (vault.db cạnh .exe)."""
    # Method 1: command line flag
    if "--portable" in sys.argv or "-p" in sys.argv:
        return True
    # Method 2: env var
    if os.environ.get("PASSVAULT_PORTABLE") == "1":
        return True
    # Method 3: marker file next to .exe
    try:
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "portable.flag").exists():
            return True
    except Exception:
        pass
    return False


def get_data_dir() -> Path:
    """Trả về thư mục chứa vault.db.

    Portable mode: cạnh file .exe
    Normal mode:   %USERPROFILE%\\.passvault\\
    """
    if is_portable_mode():
        exe_dir = Path(sys.executable).resolve().parent
        data_dir = exe_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    return Path.home() / ".passvault"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    apply_theme_to_app(app)

    data_dir = get_data_dir()
    db = Database(data_dir / "vault.db")

    # Status bar message for portable mode
    if is_portable_mode():
        print(f"[PassVault] Portable mode - vault.db at {data_dir}")
    else:
        print(f"[PassVault] Normal mode - vault.db at {data_dir}")

    try:
        # Bước 1: Hỏi master password
        is_new = not db.has_vault()
        dlg = UnlockDialog(parent=None, is_new_vault=is_new)
        if dlg.exec() != UnlockDialog.DialogCode.Accepted:
            db.close()
            return 0
        password = dlg.get_password()
        if not password:
            db.close()
            return 0

        # Bước 2: Tạo vault hoặc unlock
        if is_new:
            vault = create_new_vault(db, password)
        else:
            vault = unlock_existing_vault(db, password)
            if not vault:
                QMessageBox.critical(
                    None, "Sai password",
                    "Master password không đúng."
                )
                db.close()
                return 1

        # Bước 3: Mở main window
        window = MainWindow(vault, on_lock=lambda: lock_and_quit(app, window))
        window.setWindowTitle(
            f"PassVault - {'Portable' if is_portable_mode() else 'Local'}"
        )
        window.show()

        return app.exec()
    finally:
        try:
            db.close()
        except Exception:
            pass


def lock_and_quit(app: QApplication, window: MainWindow) -> None:
    """Lock vault → clear master_key → quit app."""
    try:
        if hasattr(window, "tray_icon") and window.tray_icon:
            window.tray_icon.hide()
    except Exception:
        pass
    try:
        if hasattr(window, "vault") and window.vault:
            window.vault.lock()
    except Exception:
        pass
    app.quit()


if __name__ == "__main__":
    sys.exit(main())
