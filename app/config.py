from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Telegram
    telegram_bot_token: str
    authorized_users: str = ""

    # Base de datos
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR}/app/database/certificados.db"

    # Rutas
    documents_dir: Path = BASE_DIR / "documentos"
    generated_dir: Path = BASE_DIR / "generated"
    backups_dir: Path = BASE_DIR / "backups"
    templates_dir: Path = BASE_DIR / "app" / "templates"
    logs_dir: Path = BASE_DIR / "logs"

    # Aplicación
    app_env: str = "development"
    log_level: str = "INFO"

    # API
    api_secret_key: str = "change_this_secret"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @field_validator("documents_dir", "backups_dir", "templates_dir", mode="before")
    @classmethod
    def resolve_path(cls, v: str | Path) -> Path:
        p = Path(v)
        return p if p.is_absolute() else BASE_DIR / p

    def get_authorized_user_ids(self) -> list[int]:
        if not self.authorized_users.strip():
            return []
        return [int(uid.strip()) for uid in self.authorized_users.split(",") if uid.strip()]

    def ensure_dirs(self) -> None:
        """Crea los directorios necesarios si no existen."""
        for directory in (
            self.documents_dir,
            self.generated_dir,
            self.backups_dir,
            self.templates_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


# Instancia única compartida por toda la aplicación
settings = Settings()  # type: ignore[call-arg]
settings.ensure_dirs()
