@echo off
cd /d "%~dp0frontend"
echo Open http://127.0.0.1:8000 in your browser
python -m http.server 8000 --bind 127.0.0.1
pause
