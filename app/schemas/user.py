from datetime import datetime

from pydantic import BaseModel, Field

from app.models.user import RolUsuario


class UserCreate(BaseModel):
    id: int = Field(..., description="Telegram user_id")
    username: str | None = None
    full_name: str | None = None
    rol: RolUsuario = RolUsuario.OPERADOR


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    username: str | None
    full_name: str | None
    rol: str
    is_active: bool
    creado_en: datetime
