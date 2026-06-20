from pathlib import Path

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.bot.handlers.admin import es_admin
from app.bot.keyboards.buttons import confirmar_accion_backup, lista_backups, menu_principal
from app.services.backup_service import (
    crear_backup,
    eliminar_backup,
    listar_backups,
    restaurar_backup,
    verificar_backup,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _resolver_ruta(nombre: str) -> Path | None:
    """Busca el archivo de backup por nombre en el directorio de backups."""
    from app.config import settings
    coincidencias = list(settings.backups_dir.rglob(nombre))
    return coincidencias[0] if coincidencias else None


# ── /backup ───────────────────────────────────────────────────────────────────

async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not es_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Solo el administrador puede crear backups.")
        return

    msg = await update.message.reply_text("⏳ Creando backup, espera...")

    try:
        ruta = crear_backup()
        tamanio = ruta.stat().st_size / (1024 * 1024)

        await msg.edit_text(f"✅ Backup creado ({tamanio:.2f} MB). Enviando...")

        with open(ruta, "rb") as f:
            await update.effective_chat.send_document(
                document=f,
                filename=ruta.name,
                caption=f"📦 {ruta.name}\n💾 {tamanio:.2f} MB",
            )
        await msg.delete()

    except OSError as e:
        logger.error("Error de disco al crear backup: %s", e)
        await msg.edit_text(f"❌ Error de almacenamiento: {e}")
    except Exception as e:
        logger.error("Error inesperado en backup: %s", e, exc_info=True)
        await msg.edit_text("❌ Error al crear el backup. Revisa los logs.")


# ── /backups ──────────────────────────────────────────────────────────────────

async def cmd_backups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    backups = listar_backups(limite=10)

    if not backups:
        await update.message.reply_text(
            "📭 No hay backups disponibles. Usa /backup para crear uno.",
            reply_markup=menu_principal(),
        )
        return

    texto = f"📦 *{len(backups)} backup(s) disponibles*\n_(mostrando los últimos 10)_"
    await update.message.reply_text(
        texto,
        parse_mode="Markdown",
        reply_markup=lista_backups(backups),
    )


# ── callbacks de la lista ─────────────────────────────────────────────────────

async def cb_backup_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra información detallada de un backup al pulsar su nombre."""
    query = update.callback_query
    await query.answer()
    nombre = query.data.split(":", 1)[1]
    ruta = _resolver_ruta(nombre)

    if not ruta:
        await query.answer("Backup no encontrado.", show_alert=True)
        return

    stat = ruta.stat()
    from datetime import datetime
    creado = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S")

    await query.answer(
        f"📦 {nombre}\n💾 {stat.st_size / (1024*1024):.2f} MB\n📅 {creado}",
        show_alert=True,
    )


async def cb_backup_descargar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Preparando descarga...")
    nombre = query.data.split(":", 1)[1]
    ruta = _resolver_ruta(nombre)

    if not ruta or not ruta.exists():
        await query.answer("❌ Backup no encontrado.", show_alert=True)
        return

    try:
        verificar_backup(ruta)
    except ValueError as e:
        await update.effective_chat.send_message(f"❌ ZIP corrupto: {e}")
        return

    with open(ruta, "rb") as f:
        await update.effective_chat.send_document(
            document=f,
            filename=ruta.name,
            caption=f"📦 {ruta.name}",
        )


async def cb_backup_restaurar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not es_admin(update.effective_user.id):
        await query.answer("⛔ Solo el administrador puede restaurar.", show_alert=True)
        return

    nombre = query.data.split(":", 1)[1]
    ruta = _resolver_ruta(nombre)
    if not ruta:
        await query.answer("❌ Backup no encontrado.", show_alert=True)
        return

    await query.edit_message_text(
        f"⚠️ *¿Restaurar este backup?*\n\n`{nombre}`\n\n"
        "Esto sobreescribirá la BD y los documentos actuales.",
        parse_mode="Markdown",
        reply_markup=confirmar_accion_backup("rest", nombre),
    )


async def cb_backup_eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not es_admin(update.effective_user.id):
        await query.answer("⛔ Solo el administrador puede eliminar backups.", show_alert=True)
        return

    nombre = query.data.split(":", 1)[1]
    await query.edit_message_text(
        f"🗑 *¿Eliminar este backup?*\n\n`{nombre}`",
        parse_mode="Markdown",
        reply_markup=confirmar_accion_backup("del", nombre),
    )


async def cb_confirmar_restaurar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not es_admin(update.effective_user.id):
        await query.answer("⛔ No autorizado.", show_alert=True)
        return

    nombre = query.data.split(":", 1)[1]
    ruta = _resolver_ruta(nombre)

    if not ruta:
        await query.edit_message_text("❌ Backup no encontrado.")
        return

    await query.edit_message_text(f"⏳ Restaurando `{nombre}`...", parse_mode="Markdown")

    try:
        restaurar_backup(ruta)
        await query.edit_message_text(
            f"✅ *Backup restaurado correctamente*\n`{nombre}`",
            parse_mode="Markdown",
        )
        logger.info("Backup restaurado: %s por usuario %s", nombre, update.effective_user.id)
    except (FileNotFoundError, ValueError) as e:
        await query.edit_message_text(f"❌ Error: {e}")
    except Exception as e:
        logger.error("Error restaurando backup %s: %s", nombre, e, exc_info=True)
        await query.edit_message_text("❌ Error inesperado durante la restauración. Revisa los logs.")


async def cb_confirmar_eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not es_admin(update.effective_user.id):
        await query.answer("⛔ No autorizado.", show_alert=True)
        return

    nombre = query.data.split(":", 1)[1]
    ruta = _resolver_ruta(nombre)

    try:
        eliminar_backup(ruta)
        await query.edit_message_text(f"🗑 Backup `{nombre}` eliminado.", parse_mode="Markdown")
        logger.info("Backup eliminado: %s por usuario %s", nombre, update.effective_user.id)
    except FileNotFoundError as e:
        await query.edit_message_text(f"❌ {e}")
    except Exception as e:
        logger.error("Error eliminando backup: %s", e, exc_info=True)
        await query.edit_message_text("❌ Error al eliminar el backup.")


async def cb_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Operación cancelada.")


# ── builder ───────────────────────────────────────────────────────────────────

def build_backup_handlers() -> list:
    """Devuelve CommandHandlers y CallbackQueryHandlers de backup."""
    return [
        # Comandos
        CommandHandler("backup",           cmd_backup),
        CommandHandler("backups",          cmd_backups),
        # Callbacks
        CallbackQueryHandler(cb_backup_info,         pattern="^bk_info:"),
        CallbackQueryHandler(cb_backup_descargar,    pattern="^bk_dl:"),
        CallbackQueryHandler(cb_backup_restaurar,    pattern="^bk_rest:"),
        CallbackQueryHandler(cb_backup_eliminar,     pattern="^bk_del:"),
        CallbackQueryHandler(cb_confirmar_restaurar, pattern="^bk_conf_rest:"),
        CallbackQueryHandler(cb_confirmar_eliminar,  pattern="^bk_conf_del:"),
        CallbackQueryHandler(cb_cancelar,            pattern="^bk_cancel$"),
    ]
