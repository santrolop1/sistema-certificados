import shutil
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Carpetas y extensiones que nunca entran al ZIP
_EXCLUIR_DIRS  = {"__pycache__", ".git", "venv", ".venv", "env", "backups"}
_EXCLUIR_EXTS  = {".pyc", ".pyo", ".log"}
_MB = 1024 * 1024
_ESPACIO_MIN_MB = 50


# ── modelo de metadatos ───────────────────────────────────────────────────────

@dataclass
class InfoBackup:
    nombre: str
    ruta: Path
    tamanio_bytes: int
    creado_en: datetime

    @property
    def tamanio_mb(self) -> str:
        return f"{self.tamanio_bytes / _MB:.2f} MB"

    @property
    def nombre_corto(self) -> str:
        return self.ruta.name


# ── helpers internos ──────────────────────────────────────────────────────────

def _ruta_backup() -> Path:
    ahora = datetime.now()
    carpeta = settings.backups_dir / str(ahora.year) / f"{ahora.month:02d}"
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = f"backup_{ahora.strftime('%Y%m%d_%H%M%S')}.zip"
    return carpeta / nombre


def _verificar_espacio(ruta: Path) -> None:
    libre = shutil.disk_usage(ruta).free
    if libre < _ESPACIO_MIN_MB * _MB:
        raise OSError(
            f"Espacio insuficiente: {libre // _MB} MB libres (mínimo {_ESPACIO_MIN_MB} MB requeridos)"
        )


def _db_path() -> Path:
    """Resuelve la ruta absoluta de la BD desde la URL de SQLAlchemy."""
    url = settings.database_url
    # sqlite+aiosqlite:///./ruta  →  ruta
    rel = url.split("///")[-1].lstrip("./")
    return (settings.documents_dir.parent / rel).resolve()


def _agregar_directorio(zf: zipfile.ZipFile, directorio: Path, base: Path) -> int:
    """Agrega un directorio al ZIP respetando las exclusiones. Devuelve archivos agregados."""
    agregados = 0
    for ruta in directorio.rglob("*"):
        if ruta.is_dir():
            continue
        if any(excluido in ruta.parts for excluido in _EXCLUIR_DIRS):
            continue
        if ruta.suffix in _EXCLUIR_EXTS:
            continue
        arcname = ruta.relative_to(base)
        zf.write(ruta, arcname)
        agregados += 1
    return agregados


def _backup_db(zf: zipfile.ZipFile, base: Path) -> None:
    """
    Usa la API de backup de SQLite para obtener una copia consistente
    incluso con la BD abierta por SQLAlchemy.
    """
    db_origen = _db_path()
    if not db_origen.exists():
        logger.warning("BD no encontrada en %s, se omite del backup", db_origen)
        return

    temporal = db_origen.with_suffix(".bak")
    try:
        src = sqlite3.connect(str(db_origen))
        dst = sqlite3.connect(str(temporal))
        src.backup(dst)
        dst.close()
        src.close()
        zf.write(temporal, db_origen.relative_to(base))
    finally:
        if temporal.exists():
            temporal.unlink()


# ── funciones públicas ────────────────────────────────────────────────────────

def crear_backup() -> Path:
    """
    Crea un ZIP con: BD, documentos y templates.
    Devuelve la ruta del archivo generado.
    """
    base = settings.documents_dir.parent  # raíz del proyecto
    destino = _ruta_backup()

    _verificar_espacio(settings.backups_dir)

    logger.info("Iniciando backup: %s", destino)

    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # 1. Base de datos
        _backup_db(zf, base)

        # 2. Documentos generados
        if settings.documents_dir.exists():
            n = _agregar_directorio(zf, settings.documents_dir, base)
            logger.info("Documentos agregados al backup: %d archivos", n)

        # 3. Plantillas
        if settings.templates_dir.exists():
            n = _agregar_directorio(zf, settings.templates_dir, base)
            logger.info("Templates agregados al backup: %d archivos", n)

    tamanio = destino.stat().st_size
    logger.info("Backup creado: %s (%.2f MB)", destino.name, tamanio / _MB)
    return destino


def listar_backups(limite: int = 20) -> list[InfoBackup]:
    """Lista los backups disponibles ordenados del más reciente al más antiguo."""
    zips = sorted(
        settings.backups_dir.rglob("backup_*.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    resultado = []
    for ruta in zips[:limite]:
        stat = ruta.stat()
        resultado.append(InfoBackup(
            nombre=ruta.name,
            ruta=ruta,
            tamanio_bytes=stat.st_size,
            creado_en=datetime.fromtimestamp(stat.st_mtime),
        ))
    return resultado


def verificar_backup(ruta: Path) -> None:
    """Lanza ValueError si el ZIP está corrupto o no existe."""
    if not ruta.exists():
        raise FileNotFoundError(f"Backup no encontrado: {ruta.name}")
    try:
        with zipfile.ZipFile(ruta, "r") as zf:
            resultado = zf.testzip()
            if resultado is not None:
                raise ValueError(f"Archivo corrupto en el ZIP: {resultado}")
    except zipfile.BadZipFile as e:
        raise ValueError(f"ZIP inválido: {e}") from e


def restaurar_backup(ruta: Path) -> None:
    """
    Extrae el backup sobre la raíz del proyecto.
    Solo restaura BD, documentos y templates — nunca sobreescribe código.
    """
    verificar_backup(ruta)
    base = settings.documents_dir.parent

    logger.info("Iniciando restauración desde: %s", ruta.name)

    with zipfile.ZipFile(ruta, "r") as zf:
        miembros = zf.namelist()
        # Filtro de seguridad: solo rutas relativas, sin "../"
        seguros = [m for m in miembros if not Path(m).is_absolute() and ".." not in m]
        zf.extractall(base, members=seguros)

    logger.info("Restauración completada: %d archivos", len(seguros))


def eliminar_backup(ruta: Path) -> None:
    """Elimina un archivo de backup."""
    if not ruta.exists():
        raise FileNotFoundError(f"Backup no encontrado: {ruta.name}")
    ruta.unlink()
    logger.info("Backup eliminado: %s", ruta.name)
