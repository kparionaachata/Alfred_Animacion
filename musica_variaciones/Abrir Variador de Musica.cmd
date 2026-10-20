@echo off
cd /d "%~dp0"
"ACE-Step-1.5\.venv\Scripts\python.exe" "abrir_estudio_musical.py"
if errorlevel 1 pause
