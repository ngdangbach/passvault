"""
build.py — Đóng gói PassVault thành file .exe.

Chạy:
    python build.py

Output:
    dist/PassVault.exe — standalone executable
    dist/PassVault/    — thư mục (nếu dùng --onedir)

Lưu ý:
  - PyInstaller không bundle Qt6 DLLs của OS; nó bundle Qt6 từ PyQt6 wheel.
  - Argon2 dùng native lib (argon2-cffi bundles .pyd → OK).
  - cryptography dùng OpenSSL bundled → OK.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "PassVault"
MAIN_SCRIPT = "main.py"


def build():
    # Clean previous build artifacts
    for d in ["build", "dist"]:
        if Path(d).exists():
            shutil.rmtree(d)
    for f in Path(".").glob(f"{APP_NAME}.spec"):
        f.unlink()

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",                 # Single .exe
        "--windowed",                # No console window (GUI app)
        "--clean",
        "--noconfirm",
        # Add data files nếu có (icon, README)
        # "--add-data", "assets;assets",
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "argon2",
        "--hidden-import", "argon2.low_level",
        "--hidden-import", "cryptography",
        "--hidden-import", "pyotp",
        "--hidden-import", "cv2",
        "--hidden-import", "mss",
        "--hidden-import", "PIL",
        "--hidden-import", "numpy",
        MAIN_SCRIPT,
    ]

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print("\n[FAIL] Build failed. Check output above.")
        return False

    exe_path = Path("dist") / f"{APP_NAME}.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n[OK] Build successful!")
        print(f"  Output: {exe_path}")
        print(f"  Size: {size_mb:.1f} MB")
        print(f"\nTo run: double-click {exe_path}")
        return True

    print("\n[FAIL] Build succeeded but exe not found.")
    return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
