from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import Date, DateTime, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class TipoCertificado(str, Enum):
    PIMPINA = "pimpina"
    KG = "kg"


class Certificate(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "certificados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identificador único legible: CERT-YYYYMMDD-XXXXXXXX
    codigo_certificado: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Datos del restaurante
    restaurante: Mapped[str] = mapped_column(String(200), nullable=False)
    nit: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    direccion: Mapped[str] = mapped_column(String(300), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Datos de recolección
    fecha_recoleccion: Mapped[date] = mapped_column(Date, nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # Guardado como string para no depender de migraciones al añadir tipos nuevos
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    plantilla: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata del certificado
    fecha_generacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False
    )
    usuario_creador: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    archivo_generado: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Columna de extensibilidad: campos futuros sin romper esquema
    campos_extra: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Certificate {self.codigo_certificado} | {self.restaurante}>"
