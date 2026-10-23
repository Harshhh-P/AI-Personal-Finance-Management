@echo off
cd /d "%~dp0"
echo Starting FinanceFlow backend at http://127.0.0.1:5000
python backend\app.py
pause
