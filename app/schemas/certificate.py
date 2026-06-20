from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.certificate import TipoCertificado


class CertificateCreate(BaseModel):
    restaurante: str = Field(..., min_length=2, max_length=200)
    nit: str = Field(..., min_length=5, max_length=30)
    direccion: str = Field(..., min_length=5, max_length=300)
    ciudad: str = Field(..., min_length=2, max_length=100)
    fecha_recoleccion: date
    cantidad: Decimal = Field(..., gt=0, decimal_places=3)
    tipo: TipoCertificado
    plantilla: int = Field(default=1, ge=1)
    observaciones: str | None = Field(default=None, max_length=1000)
    campos_extra: dict[str, Any] | None = None

    @field_validator("nit")
    @classmethod
    def nit_formato(cls, v: str) -> str:
        v = v.strip().replace(" ", "")
        if not v.replace("-", "").replace(".", "").isdigit():
            raise ValueError("El NIT solo puede contener dígitos, guiones y puntos")
        return v

    @field_validator("fecha_recoleccion")
    @classmethod
    def fecha_no_futura(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("La fecha de recolección no puede ser futura")
        return v


class CertificateUpdate(BaseModel):
    restaurante: str | None = Field(default=None, min_length=2, max_length=200)
    nit: str | None = Field(default=None, min_length=5, max_length=30)
    direccion: str | None = Field(default=None, min_length=5, max_length=300)
    ciudad: str | None = Field(default=None, min_length=2, max_length=100)
    fecha_recoleccion: date | None = None
    cantidad: Decimal | None = Field(default=None, gt=0, decimal_places=3)
    tipo: TipoCertificado | None = None
    plantilla: int | None = Field(default=None, ge=1)
    observaciones: str | None = Field(default=None, max_length=1000)
    campos_extra: dict[str, Any] | None = None


class CertificateOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    codigo_certificado: str
    restaurante: str
    nit: str
    direccion: str
    ciudad: str
    fecha_recoleccion: date
    cantidad: Decimal
    tipo: str
    observaciones: str | None
    fecha_generacion: datetime
    usuario_creador: int
    archivo_generado: str | None
    plantilla: int
    campos_extra: dict[str, Any] | None
    creado_en: datetime
    actualizado_en: datetime
    deleted_at: datetime | None


class CertificateSearch(BaseModel):
    restaurante: str | None = None
    nit: str | None = None
    ciudad: str | None = None
    tipo: TipoCertificado | None = None
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    incluir_eliminados: bool = False
