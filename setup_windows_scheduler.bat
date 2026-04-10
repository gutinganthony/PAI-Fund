@echo off
REM ============================================================
REM  Setup Windows Task Scheduler as BACKUP for daily scan
REM  This ensures scan runs even if LobsterAI is down
REM ============================================================

REM Create task that runs daily at 9:05 AM (5 min after cron, as fallback)
REM The standalone_scan.py is idempotent — if cron already ran, it skips

schtasks /create ^
  /tn "AI Trading System - Daily Scan (Backup)" ^
  /tr "python \"C:\Users\Jake Chien\lobsterai\project\trading-system\standalone_scan.py\"" ^
  /sc daily ^
  /st 09:05 ^
  /f

REM Also add a noon check in case morning scan failed
schtasks /create ^
  /tn "AI Trading System - Noon Recovery Scan" ^
  /tr "python \"C:\Users\Jake Chien\lobsterai\project\trading-system\standalone_scan.py\"" ^
  /sc daily ^
  /st 12:00 ^
  /f

echo.
echo Done! Two backup tasks created:
echo   1. Daily 09:05 - Primary backup (5 min after cron)
echo   2. Daily 12:00 - Recovery check (in case morning failed)
echo.
echo Both are idempotent: if scan already ran today, they skip.
echo.
pause
