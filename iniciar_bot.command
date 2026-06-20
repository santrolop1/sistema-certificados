#!/bin/bash
cd "$(dirname "$0")"
echo "================================"
echo " Sistema de Certificados"
echo "================================"
echo ""

# Crear entorno virtual si no existe
if [ ! -d ".venv" ]; then
    echo "Creando entorno virtual por primera vez..."
    python3 -m venv .venv
fi

# Activar entorno virtual
source .venv/bin/activate

# Instalar dependencias
echo "Verificando dependencias..."
pip install -r requirements.txt --quiet

# Verificar que existe el .env
if [ ! -f ".env" ]; then
    echo ""
    echo "ERROR: No encontré el archivo .env"
    echo "Copia .env.example a .env y rellena tu token de Telegram."
    echo ""
    read -p "Presiona Enter para cerrar..."
    exit 1
fi

echo ""
echo "Iniciando bot..."
echo "Para detenerlo presiona Ctrl+C"
echo ""
python main.py

echo ""
echo "El bot se detuvo."
read -p "Presiona Enter para cerrar..."
