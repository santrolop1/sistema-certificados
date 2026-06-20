import re
from datetime import date
from pathlib import Path

from app.config import settings


_CHARS_NO_VALIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_ESPACIOS_MULTIPLES = re.compile(r'\s+')


def sanitizar_nombre(nombre: str, max_len: int = 50) -> str:
    """Elimina caracteres no válidos en nombres de carpeta/archivo en Windows y Linux."""
    limpio = _CHARS_NO_VALIDOS.sub("", nombre)
    limpio = _ESPACIOS_MULTIPLES.sub("_", limpio.strip())
    limpio = limpio.strip("._")
    return limpio[:max_len] or "sin_nombre"


def ruta_documento(restaurante: str, fecha: date, codigo: str) -> Path:
    """
    Construye y crea la ruta:
    generated/AAAA/MM/restaurante/CERT-XXXX.docx
    """
    carpeta = (
        settings.generated_dir
        / str(fecha.year)
        / f"{fecha.month:02d}"
        / sanitizar_nombre(restaurante)
    )
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta / f"{codigo}.docx"
