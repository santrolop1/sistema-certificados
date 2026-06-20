from enum import Enum

from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class RolUsuario(str, Enum):
    ADMIN = "admin"
    OPERADOR = "operador"


class TelegramUser(Base, TimestampMixin, SoftDeleteMixin):
    """
    Usuarios autorizados del bot.
    El `id` es el Telegram user_id (BigInteger para cubrir todos los IDs de Telegram).
    """

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user_id
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rol: Mapped[str] = mapped_column(String(20), nullable=False, default=RolUsuario.OPERADOR)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<TelegramUser id={self.id} username={self.username} rol={self.rol}>"
