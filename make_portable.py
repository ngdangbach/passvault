"""
make_portable.py — Tạo folder portable trên USB.

Chạy script này để:
  1. Copy PassVault.exe vào thư mục portable/
  2. Tạo marker file portable.flag
  3. Tạo Run_PassVault.bat (chạy nhanh)
  4. Tạo README hướng dẫn
"""

from __future__ import annotations

import shutil
from pathlib import Path


HERE = Path(__file__).parent
EXE = HERE / "dist" / "PassVault.exe"
OUTPUT_DIR = HERE / "portable"


def main() -> int:
    if not EXE.exists():
        print(f"[FAIL] Not found: {EXE}")
        print("       Run 'python build.py' first.")
        return 1

    OUTPUT_DIR.mkdir(exist_ok=True)

    # 1. Copy exe
    dest_exe = OUTPUT_DIR / "PassVault.exe"
    shutil.copy(EXE, dest_exe)
    print(f"[OK] Copied: {dest_exe}")

    # 2. Marker file (auto-detect portable mode)
    (OUTPUT_DIR / "portable.flag").write_text("PassVault portable mode\n")
    print(f"[OK] Created: {OUTPUT_DIR / 'portable.flag'}")

    # 3. data/ folder (will hold vault.db)
    (OUTPUT_DIR / "data").mkdir(exist_ok=True)
    print(f"[OK] Created: {OUTPUT_DIR / 'data'}")

    # 4. Run script - double-click to launch
    run_bat = OUTPUT_DIR / "Run_PassVault.bat"
    run_bat.write_text(
        '@echo off\r\n'
        'cd /d "%~dp0"\r\n'
        'start "" PassVault.exe --portable\r\n'
    )
    print(f"[OK] Created: {run_bat}")

    # 5. install.bat - fix Smart App Control blocking
    install_src = HERE / "install.bat"
    if install_src.exists():
        shutil.copy(install_src, OUTPUT_DIR / "install.bat")
        print(f"[OK] Copied: install.bat (Smart App Control fix)")

    # 6. README
    readme = OUTPUT_DIR / "README.txt"
    readme.write_text("""PassVault - Portable Edition
============================

HOW TO USE:
  1. Copy this entire folder to a USB drive
  2. If Windows shows "Windows protected your PC" warning:
     - Click "More info"
     - Click "Run anyway"
     - OR double-click install.bat (as Administrator)
  3. Double-click Run_PassVault.bat (or PassVault.exe)
  4. Create a vault on first run, or unlock if one exists

DATA LOCATION:
  vault.db is stored in the data/ folder next to the .exe

SMART APP CONTROL (Windows 11):
  If you see a blue warning screen when running, Windows Smart App
  Control is blocking the .exe because it is unsigned.

  Three ways to fix:
    A. Click "More info" then "Run anyway" (quick, every time)
    B. Right-click PassVault.exe - Properties - check "Unblock"
    C. Run install.bat as Administrator (one-time fix)
    D. Disable Smart App Control:
       Settings - Privacy - Windows Security - App & browser control
       - Smart App Control - Turn OFF

SECURITY NOTES:
  - DO NOT sync this folder to cloud storage (OneDrive, Dropbox, ...)
  - Lost USB = lost vault (backup to another USB if needed)
  - Master password CANNOT be recovered if forgotten
  - Use a 16+ character random password
""")
    print(f"[OK] Created: {readme}")

    print()
    print("=" * 50)
    print(f"Portable folder: {OUTPUT_DIR}")
    print(f"Size:")
    total = sum(f.stat().st_size for f in OUTPUT_DIR.rglob("*") if f.is_file())
    print(f"  {total / 1024 / 1024:.1f} MB")
    print()
    print("Copy the portable/ folder to a USB drive and try it out.")
    print("If blocked by Smart App Control, run install.bat as Admin.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
