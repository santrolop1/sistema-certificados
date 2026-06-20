from datetime import date, datetime, timezone
import re

from sqlalchemy import select, or_, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certificate import Certificate
from app.models.history import AccionHistorial, HistorialCambio
from app.schemas.certificate import CertificateCreate, CertificateSearch, CertificateUpdate
from app.utils.code_generator import generate_certificate_code
from app.utils.logger import get_logger

_CODE_PATTERN = re.compile(r"^CERT-(\d{4})-(\d{6})$")

logger = get_logger(__name__)


def _to_snapshot(cert: Certificate) -> dict:
    return {
        "id": cert.id,
        "codigo_certificado": cert.codigo_certificado,
        "restaurante": cert.restaurante,
        "nit": cert.nit,
        "direccion": cert.direccion,
        "ciudad": cert.ciudad,
        "fecha_recoleccion": str(cert.fecha_recoleccion),
        "cantidad": str(cert.cantidad),
        "tipo": cert.tipo,
        "plantilla": cert.plantilla,
        "observaciones": cert.observaciones,
        "archivo_generado": cert.archivo_generado,
        "campos_extra": cert.campos_extra,
    }


async def _registrar_historial(
    session: AsyncSession,
    accion: AccionHistorial,
    cert: Certificate,
    usuario_id: int,
    snapshot_antes: dict | None = None,
) -> None:
    entrada = HistorialCambio(
        entidad="certificado",
        entidad_id=cert.id,
        accion=accion.value,
        usuario_id=usuario_id,
        snapshot_antes=snapshot_antes,
        snapshot_despues=_to_snapshot(cert),
    )
    session.add(entrada)


async def _next_certificate_code(session: AsyncSession, fecha: date) -> str:
    year = fecha.year
    stmt = select(Certificate.codigo_certificado).where(
        Certificate.codigo_certificado.like(f"CERT-{year}-%")
    )
    result = await session.execute(stmt)
    codes = result.scalars().all()

    max_sequence = 0
    for codigo in codes:
        match = _CODE_PATTERN.match(codigo)
        if match:
            max_sequence = max(max_sequence, int(match.group(2)))

    return generate_certificate_code(fecha, max_sequence + 1)


async def crear_certificado(
    session: AsyncSession,
    data: CertificateCreate,
    usuario_id: int,
) -> Certificate:
    attempt = 0
    while True:
        attempt += 1
        codigo = await _next_certificate_code(session, data.fecha_recoleccion)
        cert = Certificate(
            codigo_certificado=codigo,
            restaurante=data.restaurante,
            nit=data.nit,
            direccion=data.direccion,
            ciudad=data.ciudad,
            fecha_recoleccion=data.fecha_recoleccion,
            cantidad=data.cantidad,
            tipo=data.tipo.value,
            plantilla=data.plantilla,
            observaciones=data.observaciones,
            usuario_creador=usuario_id,
            campos_extra=data.campos_extra,
            fecha_generacion=datetime.now(timezone.utc),
        )
        session.add(cert)

        try:
            await session.flush()  # obtiene el id sin hacer commit
            break
        except IntegrityError as exc:
            await session.rollback()
            if attempt >= 5:
                raise RuntimeError(
                    "No se pudo generar un código único para el certificado."
                ) from exc
            continue

    await _registrar_historial(session, AccionHistorial.CREAR, cert, usuario_id)
    logger.info("Certificado creado: %s por usuario %s", cert.codigo_certificado, usuario_id)
    return cert


async def obtener_por_codigo(
    session: AsyncSession,
    codigo: str,
    incluir_eliminados: bool = False,
) -> Certificate | None:
    stmt = select(Certificate).where(Certificate.codigo_certificado == codigo)
    if not incluir_eliminados:
        stmt = stmt.where(Certificate.deleted_at.is_(None))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def obtener_por_id(
    session: AsyncSession,
    cert_id: int,
    incluir_eliminados: bool = False,
) -> Certificate | None:
    stmt = select(Certificate).where(Certificate.id == cert_id)
    if not incluir_eliminados:
        stmt = stmt.where(Certificate.deleted_at.is_(None))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def actualizar_certificado(
    session: AsyncSession,
    cert: Certificate,
    data: CertificateUpdate,
    usuario_id: int,
) -> Certificate:
    snapshot_antes = _to_snapshot(cert)

    update_data = data.model_dump(exclude_none=True)
    for campo, valor in update_data.items():
        if campo == "tipo" and hasattr(valor, "value"):
            valor = valor.value
        setattr(cert, campo, valor)

    await session.flush()
    await _registrar_historial(
        session, AccionHistorial.ACTUALIZAR, cert, usuario_id, snapshot_antes
    )
    logger.info("Certificado actualizado: %s por usuario %s", cert.codigo_certificado, usuario_id)
    return cert


async def eliminar_certificado(
    session: AsyncSession,
    cert: Certificate,
    usuario_id: int,
) -> Certificate:
    snapshot_antes = _to_snapshot(cert)
    cert.deleted_at = datetime.now(timezone.utc)

    await session.flush()
    await _registrar_historial(
        session, AccionHistorial.ELIMINAR, cert, usuario_id, snapshot_antes
    )
    logger.info("Certificado eliminado: %s por usuario %s", cert.codigo_certificado, usuario_id)
    return cert


async def restaurar_certificado(
    session: AsyncSession,
    cert: Certificate,
    usuario_id: int,
) -> Certificate:
    snapshot_antes = _to_snapshot(cert)
    cert.deleted_at = None

    await session.flush()
    await _registrar_historial(
        session, AccionHistorial.RESTAURAR, cert, usuario_id, snapshot_antes
    )
    logger.info("Certificado restaurado: %s por usuario %s", cert.codigo_certificado, usuario_id)
    return cert


async def buscar_certificados(
    session: AsyncSession,
    filtros: CertificateSearch,
    limite: int = 50,
    offset: int = 0,
) -> list[Certificate]:
    stmt = select(Certificate)

    if not filtros.incluir_eliminados:
        stmt = stmt.where(Certificate.deleted_at.is_(None))

    if filtros.restaurante:
        stmt = stmt.where(Certificate.restaurante.ilike(f"%{filtros.restaurante}%"))
    if filtros.nit:
        stmt = stmt.where(Certificate.nit == filtros.nit)
    if filtros.ciudad:
        stmt = stmt.where(Certificate.ciudad.ilike(f"%{filtros.ciudad}%"))
    if filtros.tipo:
        stmt = stmt.where(Certificate.tipo == filtros.tipo.value)
    if filtros.fecha_desde:
        stmt = stmt.where(Certificate.fecha_recoleccion >= filtros.fecha_desde)
    if filtros.fecha_hasta:
        stmt = stmt.where(Certificate.fecha_recoleccion <= filtros.fecha_hasta)

    stmt = stmt.order_by(Certificate.creado_en.desc()).limit(limite).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def historial_certificado(
    session: AsyncSession,
    cert_id: int,
) -> list[HistorialCambio]:
    stmt = (
        select(HistorialCambio)
        .where(
            HistorialCambio.entidad == "certificado",
            HistorialCambio.entidad_id == cert_id,
        )
        .order_by(HistorialCambio.cambiado_en.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
