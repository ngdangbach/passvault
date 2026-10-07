@echo off
:: ============================================================
:: install.bat - Fix Smart App Control blocking for PassVault
:: ============================================================
:: Run this ONCE to whitelist PassVault in Windows Security.
:: Need Administrator rights to add Defender exclusion.
:: ============================================================

setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo  PassVault - Smart App Control Fix
echo ============================================================
echo.
echo  This script will:
echo    1. Unblock PassVault.exe (file properties)
echo    2. Add folder to Windows Defender exclusions
echo    3. Try to disable Smart App Control (if possible)
echo    4. Launch PassVault
echo.
echo  If any step fails, run as Administrator (right-click
echo  install.bat -^> Run as administrator).
echo.
pause

echo.
echo [1/4] Unblocking PassVault.exe...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Unblock-File -Path '%CD%\PassVault.exe' -ErrorAction Stop; Write-Host '    OK - file unblocked' -ForegroundColor Green } catch { Write-Host '    WARN - could not unblock' -ForegroundColor Yellow }"

echo.
echo [2/4] Adding folder to Windows Defender exclusions...
net session >nul 2>&1
if %errorlevel% == 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Add-MpPreference -ExclusionPath '%CD%' -ErrorAction Stop; Write-Host '    OK - folder excluded from real-time scanning' -ForegroundColor Green } catch { Write-Host '    WARN - could not add exclusion' -ForegroundColor Yellow }"
) else (
    echo    SKIP - not running as Administrator.
    echo    To enable: right-click install.bat - Run as administrator
)

echo.
echo [3/4] Disabling Smart App Control...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$path = 'HKLM:\SOFTWARE\Microsoft\Windows Security\Windows Defender\SmartScreen'; if (Test-Path $path) { try { Set-ItemProperty -Path $path -Name 'SmartAppControlEnabled' -Value 'Off' -ErrorAction Stop; Write-Host '    OK - Smart App Control disabled' -ForegroundColor Green } catch { Write-Host '    SKIP - need Administrator to change registry' -ForegroundColor Yellow } } else { Write-Host '    SKIP - Smart App Control not configured (likely Off already)' -ForegroundColor Yellow }"

echo.
echo [4/4] Launching PassVault...
if exist "%CD%\PassVault.exe" (
    start "" "%CD%\PassVault.exe"
    echo    OK - launched
) else (
    echo    FAIL - PassVault.exe not found in this folder
)

echo.
echo ============================================================
echo  If PassVault still gets blocked:
echo.
echo    Option A: Right-click PassVault.exe - Properties
echo              - Check "Unblock" - Apply - OK
echo.
echo    Option B: Settings - Privacy - Windows Security
echo              - App ^& browser control - Smart App Control
echo              - Turn OFF (recommended for personal use)
echo.
echo    Option C: Run install.bat as Administrator
echo ============================================================
echo.
pause
endlocal
