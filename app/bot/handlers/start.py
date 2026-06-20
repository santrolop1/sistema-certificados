from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards.buttons import menu_principal
from app.utils.logger import get_logger

logger = get_logger(__name__)

AYUDA_TEXTO = """
*Sistema de Certificados* 🗂

*Comandos disponibles:*
/nuevo — Crear un certificado
/buscar — Buscar certificados
/historial — Ver historial
/ayuda — Mostrar esta ayuda
/cancelar — Cancelar operación actual

*Botones del menú:*
➕ Nuevo certificado
🔍 Buscar
📜 Historial
♻ Restaurar
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("Usuario %s inició el bot", user.id)
    await update.message.reply_text(
        f"Hola, *{user.first_name}*\\. Bienvenido al sistema de certificados\\.",
        parse_mode="MarkdownV2",
        reply_markup=menu_principal(),
    )


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(AYUDA_TEXTO, parse_mode="Markdown")
