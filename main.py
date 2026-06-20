"""
Punto de entrada del Sistema de Certificados.
"""
import asyncio
import os
import sys
from pathlib import Path

from app.bot.bot import build_app
from app.utils.logger import get_logger

logger = get_logger(__name__)

_PID_FILE = Path("bot.pid")


def _verificar_instancia_unica() -> None:
    """Evita arrancar si ya hay una instancia corriendo."""
    if _PID_FILE.exists():
        pid_anterior = _PID_FILE.read_text().strip()
        try:
            # Comprueba si el proceso sigue vivo
            os.kill(int(pid_anterior), 0)
            logger.error(
                "Ya hay una instancia del bot corriendo (PID %s). "
                "Detén esa instancia antes de iniciar otra.",
                pid_anterior,
            )
            sys.exit(1)
        except (OSError, ValueError):
            # El proceso ya no existe — el archivo es obsoleto
            _PID_FILE.unlink(missing_ok=True)

    _PID_FILE.write_text(str(os.getpid()))


def _limpiar_pid() -> None:
    _PID_FILE.unlink(missing_ok=True)


def main() -> None:
    _verificar_instancia_unica()

    try:
        # Python 3.12+ no crea event loop implícito; PTB lo necesita
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        app = build_app()
        logger.info("Bot iniciado (PID %s). Esperando mensajes...", os.getpid())
        app.run_polling(drop_pending_updates=True)
    finally:
        _limpiar_pid()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Sistema detenido por el usuario.")
        sys.exit(0)
