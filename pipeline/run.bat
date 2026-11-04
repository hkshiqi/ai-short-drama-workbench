@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0.."
echo === RUN ALL ===
python pipeline\run_all.py %*
echo === DONE, exit=%ERRORLEVEL% ===
