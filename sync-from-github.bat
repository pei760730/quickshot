@echo off
:: Red Tea Bus - 從 GitHub 同步到本機
:: 雙擊執行，自動拉取最新內容
:: 路徑：C:\KaiOS-ContentSystem\KaiOS-ContentSystem\

cd /d "C:\KaiOS-ContentSystem\KaiOS-ContentSystem"

echo.
echo ==============================
echo  Red Tea Bus 同步中...
echo ==============================
echo.

git pull origin main

echo.
echo ==============================
echo  同步完成！
echo ==============================
echo.
pause
