#!/bin/bash
cd "$(dirname "$0")"
echo "Iniciando bot..."
source .venv/bin/activate
python main.py
echo ""
echo "El bot se detuvo."
read -p "Presiona Enter para cerrar..."
