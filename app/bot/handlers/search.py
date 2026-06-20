from datetime import datetime

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.bot.keyboards.buttons import (
    confirmar_restaurar,
    criterios_busqueda,
    detalle_certificado,
    menu_principal,
    resultados_paginados,
)
from app.bot.pagination import (
    Pagina,
    guardar_pagina,
    limpiar_pagina,
    obtener_pagina,
)
from app.bot.states import (
    BUSCAR_FECHA_DESDE,
    BUSCAR_FECHA_HASTA,
    BUSCAR_TERMINO,
    HISTORIAL_CODIGO,
    RESTAURAR_CODIGO,
)
from app.database.base import AsyncSessionLocal
from app.models.certificate import Certificate
from app.schemas.certificate import CertificateSearch
from app.services.certificate_service import (
    buscar_certificados,
    historial_certificado,
    obtener_por_codigo,
    obtener_por_id,
    restaurar_certificado,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ── helpers de formato ────────────────────────────────────────────────────────

def _estado_cert(cert: Certificate) -> str:
    return "🗑 Eliminado" if cert.is_deleted else "✅ Activo"


def _formato_resumen(cert: Certificate) -> str:
    return (
        f"📄 *{cert.codigo_certificado}*\n"
        f"🏪 {cert.restaurante} | NIT: `{cert.nit}`\n"
        f"🌆 {cert.ciudad} | 📅 {cert.fecha_recoleccion.strftime('%d/%m/%Y')}\n"
        f"⚖️ {cert.cantidad} {cert.tipo} | {_estado_cert(cert)}\n"
    )


def _formato_detalle(cert: Certificate) -> str:
    return (
        f"📋 *Detalle del certificado*\n\n"
        f"🔑 Código: `{cert.codigo_certificado}`\n"
        f"🏪 Restaurante: {cert.restaurante}\n"
        f"🔢 NIT: `{cert.nit}`\n"
        f"📍 Dirección: {cert.direccion}\n"
        f"🌆 Ciudad: {cert.ciudad}\n"
        f"📅 Fecha recolección: {cert.fecha_recoleccion.strftime('%d/%m/%Y')}\n"
        f"⚖️ Cantidad: {cert.cantidad} {cert.tipo}\n"
        f"📁 Archivo: `{cert.archivo_generado or 'no generado'}`\n"
        f"📊 Estado: {_estado_cert(cert)}\n"
        f"🕐 Creado: {cert.creado_en.strftime('%d/%m/%Y %H:%M')}\n"
    )


def _diff_snapshot(antes: dict | None, despues: dict | None) -> str:
    if not antes or not despues:
        return ""
    cambios = []
    for k, v_despues in despues.items():
        v_antes = antes.get(k)
        if str(v_antes) != str(v_despues):
            cambios.append(f"  • {k}: `{v_antes}` → `{v_despues}`")
    return "\n".join(cambios) if cambios else "  (sin cambios en datos)"


# ── mostrar página de resultados ──────────────────────────────────────────────

async def _mostrar_pagina(update: Update, context: ContextTypes.DEFAULT_TYPE, pagina: Pagina, editar: bool = False) -> None:
    if not pagina.ids:
        texto = "🔍 No se encontraron certificados."
        if editar and update.callback_query:
            await update.callback_query.edit_message_text(texto)
        else:
            await update.effective_message.reply_text(texto, reply_markup=menu_principal())
        return

    async with AsyncSessionLocal() as session:
        certs = []
        for cert_id in pagina.ids_actuales:
            cert = await obtener_por_id(session, cert_id, incluir_eliminados=True)
            if cert:
                certs.append(cert)

    ids_con_codigo = [(c.id, c.codigo_certificado) for c in certs]
    texto = f"🔍 *{pagina.total} resultado(s)* — página {pagina.pagina + 1}/{pagina.total_paginas}\n\n"
    texto += "\n".join(_formato_resumen(c) for c in certs)

    teclado = resultados_paginados(pagina, ids_con_codigo)

    if editar and update.callback_query:
        await update.callback_query.edit_message_text(texto, parse_mode="Markdown", reply_markup=teclado)
    else:
        await update.effective_message.reply_text(texto, parse_mode="Markdown", reply_markup=teclado)


# ── /buscar ───────────────────────────────────────────────────────────────────

async def buscar_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["buscar_campo"] = None
    await update.message.reply_text(
        "🔍 *¿Cómo deseas buscar?*\nO escribe directamente un término para búsqueda general:",
        parse_mode="Markdown",
        reply_markup=criterios_busqueda(),
    )
    return BUSCAR_TERMINO


async def cb_seleccionar_campo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    campo = query.data.split(":")[1]
    context.user_data["buscar_campo"] = campo

    if campo == "fechas":
        await query.edit_message_text(
            "📅 Ingresa la *fecha de inicio* (DD/MM/AAAA):", parse_mode="Markdown"
        )
        return BUSCAR_FECHA_DESDE

    preguntas = {
        "texto":  "🔍 Ingresa el nombre del restaurante, NIT o código:",
        "ciudad": "🌆 Ingresa la ciudad:",
        "tipo":   "🪣 Ingresa el tipo (`pimpina` o `kg`):",
    }
    await query.edit_message_text(preguntas.get(campo, "Ingresa el término:"), parse_mode="Markdown")
    return BUSCAR_TERMINO


async def buscar_por_texto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    termino = update.message.text.strip()
    campo = context.user_data.get("buscar_campo", "texto")

    filtros: dict = {"incluir_eliminados": False}

    if campo == "ciudad":
        filtros["ciudad"] = termino
    elif campo == "tipo":
        filtros["tipo"] = termino.lower()
    else:
        # búsqueda general: restaurante + NIT + código
        filtros["restaurante"] = termino

    async with AsyncSessionLocal() as session:
        resultados = await buscar_certificados(session, CertificateSearch(**filtros), limite=200)

        # Si no encontró por restaurante, intenta por NIT o código
        if not resultados and campo == "texto":
            resultados = await buscar_certificados(
                session, CertificateSearch(nit=termino), limite=200
            )
        if not resultados and campo == "texto":
            resultados = await buscar_certificados(
                session, CertificateSearch(restaurante=termino, incluir_eliminados=True), limite=200
            )

    if not resultados:
        await update.message.reply_text(
            "🔍 No se encontraron certificados con ese criterio.",
            reply_markup=menu_principal(),
        )
        return ConversationHandler.END

    pagina = Pagina(ids=[c.id for c in resultados])
    guardar_pagina(context, pagina)
    await _mostrar_pagina(update, context, pagina)
    return ConversationHandler.END


async def buscar_fecha_desde(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        fecha = datetime.strptime(update.message.text.strip(), "%d/%m/%Y").date()
    except ValueError:
        await update.message.reply_text("Formato inválido. Usa DD/MM/AAAA:")
        return BUSCAR_FECHA_DESDE
    context.user_data["fecha_desde"] = fecha
    await update.message.reply_text("📅 Ingresa la *fecha de fin* (DD/MM/AAAA):", parse_mode="Markdown")
    return BUSCAR_FECHA_HASTA


async def buscar_fecha_hasta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        fecha = datetime.strptime(update.message.text.strip(), "%d/%m/%Y").date()
    except ValueError:
        await update.message.reply_text("Formato inválido. Usa DD/MM/AAAA:")
        return BUSCAR_FECHA_HASTA

    fecha_desde = context.user_data.get("fecha_desde")
    if fecha < fecha_desde:
        await update.message.reply_text("La fecha de fin no puede ser anterior a la de inicio:")
        return BUSCAR_FECHA_HASTA

    async with AsyncSessionLocal() as session:
        resultados = await buscar_certificados(
            session,
            CertificateSearch(fecha_desde=fecha_desde, fecha_hasta=fecha),
            limite=200,
        )

    if not resultados:
        await update.message.reply_text(
            "🔍 No se encontraron certificados en ese rango.", reply_markup=menu_principal()
        )
        return ConversationHandler.END

    pagina = Pagina(ids=[c.id for c in resultados])
    guardar_pagina(context, pagina)
    await _mostrar_pagina(update, context, pagina)
    return ConversationHandler.END


# ── callbacks de paginación e interacción ────────────────────────────────────

async def cb_pag_prev(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    pagina = obtener_pagina(context)
    if not pagina:
        return
    pagina.retroceder()
    await _mostrar_pagina(update, context, pagina, editar=True)


async def cb_pag_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    pagina = obtener_pagina(context)
    if not pagina:
        return
    pagina.avanzar()
    await _mostrar_pagina(update, context, pagina, editar=True)


async def cb_noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()


async def cb_ver_detalle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    cert_id = int(query.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        cert = await obtener_por_id(session, cert_id, incluir_eliminados=True)

    if not cert:
        await query.edit_message_text("❌ Certificado no encontrado.")
        return

    await query.edit_message_text(
        _formato_detalle(cert),
        parse_mode="Markdown",
        reply_markup=detalle_certificado(cert.id, cert.is_deleted),
    )


async def cb_volver_resultados(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    pagina = obtener_pagina(context)
    if not pagina:
        await update.callback_query.edit_message_text("La búsqueda ya expiró. Usa /buscar de nuevo.")
        return
    await _mostrar_pagina(update, context, pagina, editar=True)


# ── historial ─────────────────────────────────────────────────────────────────

async def cb_historial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    cert_id = int(query.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        cert = await obtener_por_id(session, cert_id, incluir_eliminados=True)
        if not cert:
            await query.edit_message_text("❌ Certificado no encontrado.")
            return
        cambios = await historial_certificado(session, cert_id)

    if not cambios:
        await query.edit_message_text(f"📜 Sin historial para `{cert.codigo_certificado}`.", parse_mode="Markdown")
        return

    texto = f"📜 *Historial de {cert.codigo_certificado}*\n_{len(cambios)} cambio(s)_\n\n"
    for c in cambios[:10]:
        fecha_str = c.cambiado_en.strftime("%d/%m/%Y %H:%M")
        texto += f"*{fecha_str}* — `{c.accion.upper()}`\nUsuario: `{c.usuario_id}`\n"
        diff = _diff_snapshot(c.snapshot_antes, c.snapshot_despues)
        if diff:
            texto += f"{diff}\n"
        texto += "\n"

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    volver = InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅ Volver al detalle", callback_data=f"b_det:{cert_id}")
    ]])
    await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=volver)


# ── restaurar ─────────────────────────────────────────────────────────────────

async def cb_restaurar_iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    cert_id = int(query.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        cert = await obtener_por_id(session, cert_id, incluir_eliminados=True)

    if not cert:
        await query.edit_message_text("❌ Certificado no encontrado.")
        return
    if not cert.is_deleted:
        await query.edit_message_text("ℹ️ Este certificado no está eliminado.")
        return

    await query.edit_message_text(
        f"♻ *¿Restaurar este certificado?*\n\n`{cert.codigo_certificado}`\n{cert.restaurante}",
        parse_mode="Markdown",
        reply_markup=confirmar_restaurar(cert_id),
    )


async def cb_restaurar_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    cert_id = int(query.data.split(":")[1])
    usuario_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        cert = await obtener_por_id(session, cert_id, incluir_eliminados=True)
        if not cert:
            await query.edit_message_text("❌ Certificado no encontrado.")
            return
        if not cert.is_deleted:
            await query.edit_message_text("ℹ️ Ya estaba activo.")
            return
        await restaurar_certificado(session, cert, usuario_id)
        await session.commit()
        codigo = cert.codigo_certificado

    logger.info("Certificado %s restaurado por usuario %s", codigo, usuario_id)
    await query.edit_message_text(
        f"♻ *Certificado restaurado*\nCódigo: `{codigo}`",
        parse_mode="Markdown",
    )


async def cb_restaurar_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Operación cancelada.")


# ── /historial por comando ────────────────────────────────────────────────────

async def historial_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📜 Ingresa el *código del certificado* (ej: CERT-20260410-ABCD1234):",
        parse_mode="Markdown",
    )
    return HISTORIAL_CODIGO


async def historial_por_codigo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    codigo = update.message.text.strip().upper()
    async with AsyncSessionLocal() as session:
        cert = await obtener_por_codigo(session, codigo, incluir_eliminados=True)
        if not cert:
            await update.message.reply_text(
                f"❌ No existe el certificado `{codigo}`.", parse_mode="Markdown",
                reply_markup=menu_principal()
            )
            return ConversationHandler.END
        cambios = await historial_certificado(session, cert.id)

    if not cambios:
        await update.message.reply_text(
            f"📜 Sin historial para `{codigo}`.", parse_mode="Markdown",
            reply_markup=menu_principal()
        )
        return ConversationHandler.END

    texto = f"📜 *Historial de {codigo}*\n_{len(cambios)} cambio(s)_\n\n"
    for c in cambios[:10]:
        fecha_str = c.cambiado_en.strftime("%d/%m/%Y %H:%M")
        texto += f"*{fecha_str}* — `{c.accion.upper()}`\nUsuario: `{c.usuario_id}`\n"
        diff = _diff_snapshot(c.snapshot_antes, c.snapshot_despues)
        if diff:
            texto += f"{diff}\n"
        texto += "\n"

    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=menu_principal())
    return ConversationHandler.END


# ── /restaurar por comando ────────────────────────────────────────────────────

async def restaurar_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "♻ Ingresa el *código del certificado* a restaurar:", parse_mode="Markdown"
    )
    return RESTAURAR_CODIGO


async def restaurar_por_codigo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    codigo = update.message.text.strip().upper()
    async with AsyncSessionLocal() as session:
        cert = await obtener_por_codigo(session, codigo, incluir_eliminados=True)

    if not cert:
        await update.message.reply_text(f"❌ No existe `{codigo}`.", parse_mode="Markdown", reply_markup=menu_principal())
        return ConversationHandler.END
    if not cert.is_deleted:
        await update.message.reply_text("ℹ️ Ese certificado no está eliminado.", reply_markup=menu_principal())
        return ConversationHandler.END

    context.user_data["restaurar_cert_id"] = cert.id
    await update.message.reply_text(
        f"♻ *¿Restaurar este certificado?*\n\n`{cert.codigo_certificado}`\n{cert.restaurante}",
        parse_mode="Markdown",
        reply_markup=confirmar_restaurar(cert.id),
    )
    return ConversationHandler.END


# ── cancelar ──────────────────────────────────────────────────────────────────

async def _cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    limpiar_pagina(context)
    await update.message.reply_text("Operación cancelada.", reply_markup=menu_principal())
    return ConversationHandler.END


# ── builders ──────────────────────────────────────────────────────────────────

def build_buscar_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("buscar", buscar_start),
            MessageHandler(filters.Regex("^🔍 Buscar$"), buscar_start),
        ],
        states={
            BUSCAR_TERMINO: [
                CallbackQueryHandler(cb_seleccionar_campo, pattern="^buscar_campo:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, buscar_por_texto),
            ],
            BUSCAR_FECHA_DESDE: [MessageHandler(filters.TEXT & ~filters.COMMAND, buscar_fecha_desde)],
            BUSCAR_FECHA_HASTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, buscar_fecha_hasta)],
        },
        fallbacks=[CommandHandler("cancelar", _cancelar)],
        allow_reentry=True,
    )


def build_historial_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("historial", historial_start),
            MessageHandler(filters.Regex("^📜 Historial$"), historial_start),
        ],
        states={
            HISTORIAL_CODIGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, historial_por_codigo)],
        },
        fallbacks=[CommandHandler("cancelar", _cancelar)],
        allow_reentry=True,
    )


def build_restaurar_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("restaurar", restaurar_start),
            MessageHandler(filters.Regex("^♻ Restaurar$"), restaurar_start),
        ],
        states={
            RESTAURAR_CODIGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, restaurar_por_codigo)],
        },
        fallbacks=[CommandHandler("cancelar", _cancelar)],
        allow_reentry=True,
    )


def build_search_callbacks() -> list[CallbackQueryHandler]:
    """Callbacks globales para paginación, detalle, historial y restaurar."""
    return [
        CallbackQueryHandler(cb_pag_prev,           pattern="^b_prev$"),
        CallbackQueryHandler(cb_pag_next,           pattern="^b_next$"),
        CallbackQueryHandler(cb_noop,               pattern="^b_noop$"),
        CallbackQueryHandler(cb_ver_detalle,        pattern="^b_det:"),
        CallbackQueryHandler(cb_volver_resultados,  pattern="^b_volver$"),
        CallbackQueryHandler(cb_historial,          pattern="^b_hist:"),
        CallbackQueryHandler(cb_restaurar_iniciar,  pattern="^b_rest:"),
        CallbackQueryHandler(cb_restaurar_confirmar,pattern="^b_conf:"),
        CallbackQueryHandler(cb_restaurar_cancelar, pattern="^b_cancel_rest$"),
    ]
