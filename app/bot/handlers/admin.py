from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings
from app.database.base import AsyncSessionLocal
from app.schemas.certificate import CertificateSearch
from app.services.certificate_service import buscar_certificados
from app.utils.logger import get_logger

logger = get_logger(__name__)


def es_admin(user_id: int) -> bool:
    ids = settings.get_authorized_user_ids()
    # Si no hay lista configurada, nadie es admin
    return bool(ids) and user_id == ids[0]


async def estadisticas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not es_admin(update.effective_user.id):
        await update.message.reply_text("⛔ No tienes permisos para este comando.")
        return

    async with AsyncSessionLocal() as session:
        todos = await buscar_certificados(session, CertificateSearch(), limite=1000)
        eliminados = await buscar_certificados(
            session, CertificateSearch(incluir_eliminados=True), limite=1000
        )

    activos = len(todos)
    total = len(eliminados)

    await update.message.reply_text(
        f"📊 *Estadísticas*\n\n"
        f"✅ Certificados activos: {activos}\n"
        f"🗑 Eliminados: {total - activos}\n"
        f"📁 Total: {total}",
        parse_mode="Markdown",
    )
