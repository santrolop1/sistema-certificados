from datetime import date


def generate_certificate_code(fecha: date | None = None, sequence: int = 1) -> str:
    """Genera un código único en formato: CERT-AAAA-000001"""
    fecha = fecha or date.today()
    return f"CERT-{fecha.year}-{sequence:06d}"
