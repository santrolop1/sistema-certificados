from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.bot.pagination import Pagina
from app.services.document_service import get_available_templates


def menu_principal() -> ReplyKeyboardMarkup:
    teclado = [
        ["➕ Nuevo certificado", "🔍 Buscar"],
        ["📜 Historial", "♻ Restaurar"],
    ]
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True)


def tipo_certificado() -> ReplyKeyboardMarkup:
    teclado = [["Pimpina", "Kg"]]
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True, one_time_keyboard=True)


def seleccionar_plantilla() -> ReplyKeyboardMarkup:
    opciones = []
    for plantilla_id, nombre in get_available_templates().items():
        label = f"📄 Plantilla {plantilla_id}"
        opciones.append(label)

    teclado = [opciones[i:i + 2] for i in range(0, len(opciones), 2)]
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True, one_time_keyboard=True)


def confirmar_certificado() -> InlineKeyboardMarkup:
    botones = [
        [
            InlineKeyboardButton("✅ Confirmar", callback_data="confirmar"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancelar"),
        ]
    ]
    return InlineKeyboardMarkup(botones)


# ── búsqueda ──────────────────────────────────────────────────────────────────

def criterios_busqueda() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏪 Restaurante/NIT", callback_data="buscar_campo:texto"),
            InlineKeyboardButton("🌆 Ciudad",           callback_data="buscar_campo:ciudad"),
        ],
        [
            InlineKeyboardButton("🪣 Tipo",             callback_data="buscar_campo:tipo"),
            InlineKeyboardButton("📅 Rango de fechas",  callback_data="buscar_campo:fechas"),
        ],
        [InlineKeyboardButton("🔍 Búsqueda general",   callback_data="buscar_campo:texto")],
    ])


def resultados_paginados(pagina: Pagina, ids_con_codigo: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """
    ids_con_codigo: [(cert_id, codigo_certificado), ...]
    """
    filas = []

    # Un botón por resultado
    for cert_id, codigo in ids_con_codigo:
        filas.append([InlineKeyboardButton(f"📄 {codigo}", callback_data=f"b_det:{cert_id}")])

    # Navegación
    nav = []
    if pagina.hay_anterior:
        nav.append(InlineKeyboardButton("⬅ Anterior", callback_data="b_prev"))
    nav.append(InlineKeyboardButton(
        f"{pagina.pagina + 1}/{pagina.total_paginas}", callback_data="b_noop"
    ))
    if pagina.hay_siguiente:
        nav.append(InlineKeyboardButton("Siguiente ➡", callback_data="b_next"))

    if nav:
        filas.append(nav)

    return InlineKeyboardMarkup(filas)


def detalle_certificado(cert_id: int, esta_eliminado: bool) -> InlineKeyboardMarkup:
    filas = [
        [InlineKeyboardButton("📜 Historial", callback_data=f"b_hist:{cert_id}")],
    ]
    if esta_eliminado:
        filas.append([InlineKeyboardButton("♻ Restaurar", callback_data=f"b_rest:{cert_id}")])

    filas.append([InlineKeyboardButton("⬅ Volver a resultados", callback_data="b_volver")])
    return InlineKeyboardMarkup(filas)


def confirmar_restaurar(cert_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Sí, restaurar", callback_data=f"b_conf:{cert_id}"),
            InlineKeyboardButton("❌ Cancelar",      callback_data="b_cancel_rest"),
        ]
    ])


# ── backups ───────────────────────────────────────────────────────────────────

def lista_backups(backups: list) -> InlineKeyboardMarkup:
    """
    backups: lista de InfoBackup.
    Genera un botón por backup con acciones inline.
    """
    filas = []
    for bk in backups:
        fecha_str = bk.creado_en.strftime("%d/%m/%Y %H:%M")
        # Etiqueta del backup
        filas.append([
            InlineKeyboardButton(
                f"📦 {fecha_str} ({bk.tamanio_mb})",
                callback_data=f"bk_info:{bk.nombre}",
            )
        ])
        # Acciones por backup
        filas.append([
            InlineKeyboardButton("📥 Descargar", callback_data=f"bk_dl:{bk.nombre}"),
            InlineKeyboardButton("♻ Restaurar",  callback_data=f"bk_rest:{bk.nombre}"),
            InlineKeyboardButton("🗑 Eliminar",  callback_data=f"bk_del:{bk.nombre}"),
        ])
    return InlineKeyboardMarkup(filas)


def confirmar_accion_backup(accion: str, nombre: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirmar", callback_data=f"bk_conf_{accion}:{nombre}"),
            InlineKeyboardButton("❌ Cancelar",  callback_data="bk_cancel"),
        ]
    ])
