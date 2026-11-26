"""Generación de PDF a partir de HTML con respaldo sin librerías del sistema.

Se intenta primero WeasyPrint, que conserva mejor el diseño. Si no está
disponible (por ejemplo, en Windows sin GTK o en un entorno sin las
bibliotecas nativas), se usa xhtml2pdf, que es puramente Python.
"""

from io import BytesIO


def _resumen_error(exc):
    """Devuelve una línea breve y legible para mostrar en la interfaz."""
    texto = str(exc).strip().splitlines()
    mensaje = texto[0] if texto else type(exc).__name__
    return f"{type(exc).__name__}: {mensaje}"[:300]


def html_a_pdf(html, presentational_hints=False):
    """Devuelve ``(pdf_bytes, error)``.

    Si la generación funciona, ``error`` es ``None``. Si fallan ambos
    motores, ``pdf_bytes`` es ``None`` y ``error`` reúne los dos motivos.
    """
    errores = []

    try:
        from weasyprint import HTML

        pdf = HTML(string=html).write_pdf(presentational_hints=presentational_hints)
        if not pdf:
            raise RuntimeError("WeasyPrint devolvió un PDF vacío")
        return pdf, None
    except Exception as exc:  # noqa: BLE001 - se informa el motivo en la interfaz
        errores.append("WeasyPrint → " + _resumen_error(exc))

    try:
        from xhtml2pdf import pisa

        buffer = BytesIO()
        resultado = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
        if resultado.err:
            raise RuntimeError(f"xhtml2pdf informó {resultado.err} error(es)")
        pdf = buffer.getvalue()
        if not pdf:
            raise RuntimeError("xhtml2pdf devolvió un PDF vacío")
        return pdf, None
    except Exception as exc:  # noqa: BLE001 - se informa el motivo en la interfaz
        errores.append("xhtml2pdf → " + _resumen_error(exc))

    return None, " | ".join(errores)
