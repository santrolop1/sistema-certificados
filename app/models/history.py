from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import BigInteger, DateTime, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AccionHistorial(str, Enum):
    CREAR = "crear"
    ACTUALIZAR = "actualizar"
    ELIMINAR = "eliminar"
    RESTAURAR = "restaurar"


class HistorialCambio(Base):
    """
    Registro inmutable de todos los cambios a cualquier entidad.
    Nunca se actualiza ni elimina — es solo append.
    """

    __tablename__ = "historial_cambios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Qué entidad cambió y cuál instancia
    entidad: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entidad_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Qué pasó
    accion: Mapped[str] = mapped_column(String(20), nullable=False)

    # Quién lo hizo (Telegram user_id)
    usuario_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Estado completo antes y después del cambio
    snapshot_antes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    snapshot_despues: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    cambiado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<HistorialCambio {self.accion} {self.entidad}#{self.entidad_id}"
            f" by={self.usuario_id}>"
        )
