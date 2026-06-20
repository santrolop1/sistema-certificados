from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.bot.handlers.admin import estadisticas
from app.bot.handlers.backup import build_backup_handlers
from app.bot.handlers.certificate import build_nuevo_handler, verificar
from app.bot.handlers.search import (
    build_buscar_handler,
    build_historial_handler,
    build_restaurar_handler,
    build_search_callbacks,
)
from app.bot.handlers.start import ayuda, start
from app.bot.keyboards.buttons import menu_principal
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

AUTHORIZED = set(settings.get_authorized_user_ids())


async def _no_autorizado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning("Acceso denegado a usuario %s", update.effective_user.id)
    await update.message.reply_text("⛔ No tienes acceso a este bot.")


async def _handle_global_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Error no controlado en el bot: %s", context.error)
    try:
        if hasattr(update, "message") and update.message:
            await update.message.reply_text(
                "❌ Ocurrió un error inesperado. Intenta de nuevo más tarde."
            )
    except Exception:
        logger.exception("No se pudo notificar al usuario del error")


def _auth_filter() -> filters.BaseFilter:
    """Filtra mensajes de usuarios no autorizados."""
    if not AUTHORIZED:
        # Sin lista configurada: acepta a todos (útil en desarrollo)
        logger.warning("AUTHORIZED_USERS vacío — el bot acepta a cualquier usuario")
        return filters.ALL
    return filters.User(user_id=list(AUTHORIZED))


async def _post_init(application: Application) -> None:
    from app.database.init_db import init_db
    await init_db()

    comandos = [
        BotCommand("start",     "Inicio y menú principal"),
        BotCommand("nuevo",     "Crear un certificado"),
        BotCommand("buscar",    "Buscar certificados"),
        BotCommand("historial", "Ver historial de un certificado"),
        BotCommand("restaurar", "Restaurar certificado eliminado"),
        BotCommand("verificar", "Verificar certificado por código"),
        BotCommand("backup",    "Crear backup ahora (solo admin)"),
        BotCommand("backups",   "Ver backups disponibles"),
        BotCommand("stats",     "Estadísticas (solo admin)"),
        BotCommand("ayuda",     "Mostrar ayuda"),
        BotCommand("cancelar",  "Cancelar operación actual"),
    ]
    await application.bot.set_my_commands(comandos)
    logger.info("Comandos del bot registrados en Telegram.")


def build_app() -> Application:
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(_post_init)
        .build()
    )

    auth = _auth_filter()

    # Handlers globales (sin ConversationHandler)
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("ayuda",  ayuda))
    app.add_handler(CommandHandler("stats",  estadisticas))
    app.add_handler(CommandHandler("verificar", verificar))

    # ConversationHandlers — orden importa: más específicos primero
    app.add_handler(build_nuevo_handler())
    app.add_handler(build_buscar_handler())
    app.add_handler(build_historial_handler())
    app.add_handler(build_restaurar_handler())

    # Callbacks globales de búsqueda/paginación
    for cb in build_search_callbacks():
        app.add_handler(cb)

    # Handlers de backup (comandos + callbacks)
    for h in build_backup_handlers():
        app.add_handler(h)

    # Bloquear usuarios no autorizados (cae al final si no matcheó nada)
    if AUTHORIZED:
        app.add_handler(
            MessageHandler(~auth, _no_autorizado)
        )

    app.add_error_handler(_handle_global_error)

    logger.info("Bot configurado con %d usuario(s) autorizado(s).", len(AUTHORIZED))
    return app
