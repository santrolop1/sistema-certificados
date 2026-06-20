import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.bot.keyboards.buttons import confirmar_certificado, menu_principal, seleccionar_plantilla, tipo_certificado
from app.bot.states import (
    CANTIDAD,
    CIUDAD,
    CONFIRMAR,
    DIRECCION,
    FECHA,
    NIT,
    PLANTILLA,
    RESTAURANTE,
    TIPO,
)
from app.database.base import AsyncSessionLocal
from app.models.certificate import Certificate, TipoCertificado
from app.schemas.certificate import CertificateCreate, CertificateUpdate
from app.services.certificate_service import actualizar_certificado, crear_certificado, obtener_por_codigo
from app.services.document_service import generar_certificado_docx, get_available_templates
from app.utils.logger import get_logger

logger = get_logger(__name__)

_KEY = "nuevo_cert"
_TOTAL_PASOS = 8

# Aliases aceptados para el tipo de recolección
_ALIAS_TIPO = {
    "kg": TipoCertificado.KG,
    "k": TipoCertificado.KG,
    "kilo": TipoCertificado.KG,
    "kilos": TipoCertificado.KG,
    "kilogramo": TipoCertificado.KG,
    "kilogramos": TipoCertificado.KG,
    "pimpina": TipoCertificado.PIMPINA,
    "pimpinas": TipoCertificado.PIMPINA,
    "pimp": TipoCertificado.PIMPINA,
    "pmp": TipoCertificado.PIMPINA,
    "p": TipoCertificado.PIMPINA,
}

# Formatos de fecha aceptados
_FORMATOS_FECHA = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"]


# ── helpers ───────────────────────────────────────────────────────────────────

def _datos(context: ContextTypes.DEFAULT_TYPE) -> dict:
    if _KEY not in context.user_data:
        context.user_data[_KEY] = {}
    return context.user_data[_KEY]


def _paso(numero: int, titulo: str) -> str:
    barra = "🟢" * numero + "⚪" * (_TOTAL_PASOS - numero)
    return f"{barra}\n*Paso {numero} de {_TOTAL_PASOS} — {titulo}*\n\n"


def _parsear_fecha(texto: str) -> date | None:
    texto = texto.strip()
    for fmt in _FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def _parsear_tipo(texto: str) -> TipoCertificado | None:
    return _ALIAS_TIPO.get(texto.strip().lower())


def _sanitizar_texto(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.strip())


def _resumen(d: dict) -> str:
    tipo = d.get("tipo", "")
    tipo_label = "Pimpina" if tipo == TipoCertificado.PIMPINA.value else "Kg"
    fecha = d.get("fecha_recoleccion")
    fecha_str = fecha.strftime("%d/%m/%Y") if fecha else "-"
    plantilla = d.get("plantilla", 1)
    return (
        f"📋 *Resumen del certificado*\n\n"
        f"🏪 Restaurante: {d.get('restaurante', '-')}\n"
        f"🔢 NIT: {d.get('nit', '-')}\n"
        f"📍 Dirección: {d.get('direccion', '-')}\n"
        f"🌆 Ciudad: {d.get('ciudad', '-')}\n"
        f"📅 Fecha recolección: {fecha_str}\n"
        f"⚖️ Cantidad: {d.get('cantidad', '-')}\n"
        f"🪣 Tipo: {tipo_label}\n"
        f"📄 Plantilla: {plantilla}\n"
    )


async def _cancelar_operacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(_KEY, None)
    await update.message.reply_text("Operación cancelada.", reply_markup=menu_principal())
    return ConversationHandler.END


# ── pasos ─────────────────────────────────────────────────────────────────────

async def nuevo_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[_KEY] = {}
    await update.message.reply_text(
        "Vamos a crear un nuevo certificado.\n"
        "Te voy a pedir los datos *uno por uno*.\n"
        "En cualquier momento escribe /cancelar para salir.\n\n"
        + _paso(1, "Nombre del restaurante")
        + "Escribe el nombre completo del restaurante o establecimiento:\n"
        "_Ejemplo: Restaurante El Buen Sabor_",
        parse_mode="Markdown",
    )
    return RESTAURANTE


async def recibir_restaurante(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = _sanitizar_texto(update.message.text)
    if len(texto) < 2:
        await update.message.reply_text(
            "❌ El nombre que pusiste es muy corto.\n\n"
            "✏️ Escribe el nombre completo del restaurante:\n"
            "_Ejemplo: Restaurante El Buen Sabor_",
            parse_mode="Markdown",
        )
        return RESTAURANTE
    if len(texto) > 200:
        await update.message.reply_text(
            f"❌ El nombre es muy largo ({len(texto)} caracteres, máximo 200).\n\n"
            "✏️ Escribe un nombre más corto:",
        )
        return RESTAURANTE
    _datos(context)["restaurante"] = texto
    await update.message.reply_text(
        _paso(2, "NIT")
        + "Escribe el NIT del restaurante:\n"
        "_Ejemplo: 901234567-1_",
        parse_mode="Markdown",
    )
    return NIT


async def recibir_nit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = _sanitizar_texto(update.message.text).replace(" ", "")
    limpio = texto.replace("-", "").replace(".", "")
    if not limpio.isdigit() or len(limpio) < 5:
        await update.message.reply_text(
            f"❌ *'{update.message.text.strip()}'* no es un NIT válido.\n\n"
            "El NIT solo puede tener números, guiones o puntos.\n\n"
            "✏️ Escríbelo de nuevo:\n"
            "_Ejemplo: 901234567-1_",
            parse_mode="Markdown",
        )
        return NIT
    _datos(context)["nit"] = texto
    await update.message.reply_text(
        _paso(3, "Dirección")
        + "Escribe la dirección del restaurante:\n"
        "_Ejemplo: Calle 45 # 12-30_",
        parse_mode="Markdown",
    )
    return DIRECCION


async def recibir_direccion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = _sanitizar_texto(update.message.text)
    if len(texto) < 5:
        await update.message.reply_text(
            f"❌ La dirección *'{texto}'* es muy corta.\n\n"
            "✏️ Escribe la dirección completa:\n"
            "_Ejemplo: Calle 45 # 12-30_",
            parse_mode="Markdown",
        )
        return DIRECCION
    _datos(context)["direccion"] = texto
    await update.message.reply_text(
        _paso(4, "Ciudad")
        + "Escribe el nombre de la ciudad:\n"
        "_Ejemplo: Bucaramanga_",
        parse_mode="Markdown",
    )
    return CIUDAD


async def recibir_ciudad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = _sanitizar_texto(update.message.text)
    if len(texto) < 2:
        await update.message.reply_text(
            "❌ Eso no parece una ciudad.\n\n"
            "✏️ Escribe el nombre de la ciudad:\n"
            "_Ejemplo: Bucaramanga_",
            parse_mode="Markdown",
        )
        return CIUDAD
    _datos(context)["ciudad"] = texto
    await update.message.reply_text(
        _paso(5, "Fecha de recolección")
        + "Escribe la fecha en que se recolectó el aceite:\n"
        "_Formato: DD/MM/AAAA — Ejemplo: 25/05/2026_",
        parse_mode="Markdown",
    )
    return FECHA


async def recibir_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto_original = update.message.text.strip()
    fecha = _parsear_fecha(texto_original)
    if not fecha:
        await update.message.reply_text(
            f"❌ *'{texto_original}'* no es una fecha válida.\n\n"
            "✏️ Escríbela así: DD/MM/AAAA\n"
            "_Ejemplo: 25/05/2026_",
            parse_mode="Markdown",
        )
        return FECHA
    if fecha > date.today():
        await update.message.reply_text(
            f"❌ La fecha *{fecha.strftime('%d/%m/%Y')}* es futura y no es válida.\n\n"
            "✏️ Escribe la fecha real en que se recogió el aceite:",
            parse_mode="Markdown",
        )
        return FECHA
    _datos(context)["fecha_recoleccion"] = fecha
    await update.message.reply_text(
        _paso(6, "Cantidad")
        + "Escribe la cantidad de aceite recolectado (solo el número):\n"
        "_Ejemplo: 2.932 o 15 o 8,5_",
        parse_mode="Markdown",
    )
    return CANTIDAD


async def recibir_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto_original = update.message.text.strip()
    texto = texto_original.replace(",", ".")
    try:
        cantidad = Decimal(texto)
        if cantidad <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await update.message.reply_text(
            f"❌ *'{texto_original}'* no es una cantidad válida.\n\n"
            "✏️ Escribe solo el número (usa punto o coma para decimales):\n"
            "_Ejemplo: 2.932 o 15 o 8,5_",
            parse_mode="Markdown",
        )
        return CANTIDAD
    _datos(context)["cantidad"] = cantidad
    await update.message.reply_text(
        _paso(7, "Tipo de recolección")
        + "¿Cómo se entregó el aceite?\n"
        "👇 *Toca uno de los botones:*",
        parse_mode="Markdown",
        reply_markup=tipo_certificado(),
    )
    return TIPO


async def recibir_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tipo = _parsear_tipo(update.message.text)
    if not tipo:
        await update.message.reply_text(
            f"❌ *'{update.message.text.strip()}'* no es válido.\n\n"
            "👇 Toca uno de los dos botones:",
            parse_mode="Markdown",
            reply_markup=tipo_certificado(),
        )
        return TIPO
    _datos(context)["tipo"] = tipo.value
    await update.message.reply_text(
        _paso(8, "Tipo de plantilla")
        + "¿Qué plantilla quieres usar?\n"
        "👇 *Toca uno de los botones:*",
        parse_mode="Markdown",
        reply_markup=seleccionar_plantilla(),
    )
    return PLANTILLA


async def recibir_plantilla(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = _sanitizar_texto(update.message.text)
    match = re.search(r"(\d+)", texto)
    disponible = set(get_available_templates())

    if not match:
        validas = ", ".join(str(item) for item in sorted(disponible))
        await update.message.reply_text(
            f"❌ *'{texto}'* no es válido.\n\n"
            f"Escribe el número de plantilla disponible: {validas}",
            parse_mode="Markdown",
            reply_markup=seleccionar_plantilla(),
        )
        return PLANTILLA

    plantilla = int(match.group(1))
    if plantilla not in disponible:
        validas = ", ".join(str(item) for item in sorted(disponible))
        await update.message.reply_text(
            f"❌ La plantilla {plantilla} no está disponible.\n\n"
            f"Opciones válidas: {validas}",
            parse_mode="Markdown",
            reply_markup=seleccionar_plantilla(),
        )
        return PLANTILLA

    _datos(context)["plantilla"] = plantilla
    resumen = _resumen(_datos(context))
    await update.message.reply_text(
        f"{resumen}\n¿Los datos son correctos?",
        parse_mode="Markdown",
        reply_markup=confirmar_certificado(),
    )
    return CONFIRMAR


async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "cancelar":
        context.user_data.pop(_KEY, None)
        await query.edit_message_text("Operación cancelada.", reply_markup=menu_principal())
        return ConversationHandler.END

    datos = _datos(context)
    usuario_id = update.effective_user.id

    await query.edit_message_text("⏳ Guardando y generando el certificado...")

    try:
        schema = CertificateCreate(
            restaurante=datos["restaurante"],
            nit=datos["nit"],
            direccion=datos["direccion"],
            ciudad=datos["ciudad"],
            fecha_recoleccion=datos["fecha_recoleccion"],
            cantidad=datos["cantidad"],
            tipo=TipoCertificado(datos["tipo"]),
            plantilla=datos.get("plantilla", 1),
        )
        async with AsyncSessionLocal() as session:
            cert = await crear_certificado(session, schema, usuario_id)
            await session.commit()

        # Generar documento (DOCX o PDF)
        plantilla = datos.get("plantilla", 1)
        ruta_salida = generar_certificado_docx(cert, plantilla=plantilla)

        # Guardar ruta en la BD
        async with AsyncSessionLocal() as session:
            cert_db = await session.get(Certificate, cert.id)
            if cert_db:
                await actualizar_certificado(
                    session,
                    cert_db,
                    CertificateUpdate(archivo_generado=str(ruta_salida)),
                    usuario_id,
                )
                await session.commit()

        context.user_data.pop(_KEY, None)
        await query.edit_message_text(
            f"✅ *Certificado generado correctamente*\n\n"
            f"📄 Código: `{cert.codigo_certificado}`\n"
            f"🏪 {cert.restaurante}\n\n"
            f"El documento se envía a continuación 👇",
            parse_mode="Markdown",
        )

        with open(ruta_salida, "rb") as f:
            await update.effective_chat.send_document(
                document=f,
                filename=ruta_salida.name,
                caption=f"📄 {cert.codigo_certificado} — {cert.restaurante}",
            )

        logger.info("Certificado %s generado y enviado a usuario %s", cert.codigo_certificado, usuario_id)

    except Exception as e:
        logger.error("Error al generar certificado: %s", e, exc_info=True)
        context.user_data.pop(_KEY, None)
        await query.edit_message_text(
            "❌ Ocurrió un error al generar el certificado.\n"
            "Por favor intenta de nuevo con /nuevo.\n"
            "Si el error persiste, contacta al administrador."
        )

    return ConversationHandler.END


async def verificar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text(
            "Uso: /verificar CERT-AAAA-000001\nEjemplo: /verificar CERT-2026-000001",
            parse_mode="Markdown",
        )
        return

    codigo = args[0].strip().upper()
    async with AsyncSessionLocal() as session:
        cert = await obtener_por_codigo(session, codigo, incluir_eliminados=True)

    if not cert:
        await update.message.reply_text(
            f"❌ No se encontró el certificado `{codigo}`.",
            parse_mode="Markdown",
        )
        return

    estado = "✅ Válido" if not cert.is_deleted else "⚠️ Eliminado"
    await update.message.reply_text(
        "*Verificación de certificado*\n\n"
        f"🔑 Código: `{cert.codigo_certificado}`\n"
        f"🏪 Restaurante: {cert.restaurante}\n"
        f"🔢 NIT: `{cert.nit}`\n"
        f"📅 Fecha: {cert.fecha_recoleccion.strftime('%d/%m/%Y')}\n"
        f"⚖️ Cantidad: {cert.cantidad}\n"
        f"📊 Estado: {estado}",
        parse_mode="Markdown",
    )


# ── ConversationHandler ───────────────────────────────────────────────────────

def build_nuevo_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("nuevo", nuevo_start),
            MessageHandler(filters.Regex("^➕ Nuevo certificado$"), nuevo_start),
        ],
        states={
            RESTAURANTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_restaurante)],
            NIT:         [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nit)],
            DIRECCION:   [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_direccion)],
            CIUDAD:      [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_ciudad)],
            FECHA:       [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_fecha)],
            CANTIDAD:    [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_cantidad)],
            TIPO:        [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_tipo)],
            PLANTILLA:   [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_plantilla)],
            CONFIRMAR:   [CallbackQueryHandler(confirmar)],
        },
        fallbacks=[CommandHandler("cancelar", _cancelar_operacion)],
        allow_reentry=True,
    )
