@echo off
title Sistema de Certificados - Bot Telegram
echo ================================
echo  Sistema de Certificados
echo ================================
echo.

:: Crear entorno virtual si no existe
if not exist ".venv" (
    echo Creando entorno virtual por primera vez...
    python -m venv .venv
)

:: Activar entorno virtual
call .venv\Scripts\activate

:: Instalar dependencias si falta alguna
echo Verificando dependencias...
pip install -r requirements.txt --quiet

:: Verificar que existe el .env
if not exist ".env" (
    echo.
    echo ERROR: No encontre el archivo .env
    echo Copia .env.example a .env y rellena tu token de Telegram.
    echo.
    pause
    exit /b 1
)

echo.
echo Iniciando bot...
echo Para detenerlo presiona Ctrl+C
echo.
python main.py

echo.
echo El bot se detuvo.
pause
