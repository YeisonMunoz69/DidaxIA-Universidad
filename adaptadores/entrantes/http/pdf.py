from __future__ import annotations


class PdfInutilizable(ValueError):
    pass

FIRMA = b"%PDF-"


def exigir_pdf_utilizable(contenido: bytes) -> None:
    if not contenido.startswith(FIRMA):
        raise PdfInutilizable("el archivo no empieza por la firma de un PDF")

    from io import BytesIO

    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        lector = PdfReader(BytesIO(contenido))
    except (PyPdfError, ValueError, OSError, RecursionError) as error:

        raise PdfInutilizable(
            f"el archivo no se puede abrir como PDF ({type(error).__name__})"
        ) from None

    if getattr(lector, "is_encrypted", False):

        raise PdfInutilizable(
            "el archivo está cifrado y el equipo no podría abrirlo para verificarlo"
        )

    try:
        paginas = len(lector.pages)
    except (PyPdfError, ValueError, OSError, RecursionError) as error:

        raise PdfInutilizable(
            f"el árbol de páginas del PDF no es utilizable ({type(error).__name__})"
        ) from None

    if paginas < 1:
        raise PdfInutilizable("el PDF no tiene ninguna página")
