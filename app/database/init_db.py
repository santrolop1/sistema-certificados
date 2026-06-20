from sqlalchemy import inspect, text

from app.database.base import Base, engine
from app.models import certificate, history, user  # noqa: F401 — registrar modelos en Base
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def _ensure_schema(conn) -> None:
    def _sync_inspect(sync_conn):
        inspector = inspect(sync_conn)
        tables = inspector.get_table_names()
        if "certificados" not in tables:
            return set(), set()
        columns = {column["name"] for column in inspector.get_columns("certificados")}
        indexes = {index["name"] for index in inspector.get_indexes("certificados")}
        return columns, indexes

    existing_columns, existing_indexes = await conn.run_sync(_sync_inspect)

    if "plantilla" not in existing_columns:
        await conn.execute(text("ALTER TABLE certificados ADD COLUMN plantilla INTEGER DEFAULT 1"))
        logger.info("Columna 'plantilla' agregada a certificados.")

    if "ix_certificados_nit" not in existing_indexes:
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_certificados_nit ON certificados(nit)"))
        logger.info("Índice ix_certificados_nit creado.")

    if "ix_certificados_ciudad" not in existing_indexes:
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_certificados_ciudad ON certificados(ciudad)"))
        logger.info("Índice ix_certificados_ciudad creado.")


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_schema(conn)
    logger.info("Base de datos inicializada correctamente.")


async def drop_db() -> None:
    """Solo para desarrollo/tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("Todas las tablas eliminadas.")
