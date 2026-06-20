# ── Fase /nuevo (0-8) ─────────────────────────────────────────────────────────
(
    RESTAURANTE,
    NIT,
    DIRECCION,
    CIUDAD,
    FECHA,
    CANTIDAD,
    TIPO,
    CONFIRMAR,
) = range(8)

PLANTILLA = 8

# ── Fase /buscar (20-29) ──────────────────────────────────────────────────────
(
    BUSCAR_TERMINO,
    BUSCAR_CAMPO,
    BUSCAR_FECHA_DESDE,
    BUSCAR_FECHA_HASTA,
) = range(20, 24)

# ── Fase /historial (30-31) ───────────────────────────────────────────────────
HISTORIAL_CODIGO = 30

# ── Fase /restaurar (40-41) ───────────────────────────────────────────────────
(
    RESTAURAR_CODIGO,
    CONFIRMAR_RESTAURAR,
) = range(40, 42)
