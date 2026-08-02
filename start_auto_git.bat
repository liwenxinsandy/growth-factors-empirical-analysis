@echo off
:: 在后台启动 auto_git watcher（无窗口）
start /min powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\Users\Lenovo\Documents\经济增长因素\auto_git.ps1"
echo Auto-git watcher started in background.
echo Check auto_git.log for status.
pause
