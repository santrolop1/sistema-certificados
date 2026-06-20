@echo off
title Sistema de Certificados - Bot Telegram
echo Iniciando bot...
call .venv\Scripts\activate
python main.py
echo.
echo El bot se detuvo. Presiona cualquier tecla para cerrar.
pause
