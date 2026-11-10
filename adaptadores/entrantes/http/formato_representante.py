from __future__ import annotations

import hashlib
import io
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen.canvas import Canvas

ZONA_DEL_PILOTO = ZoneInfo("America/Bogota")
NOMBRE_DEL_ARCHIVO = "Autorizacion-representante-menor-v0.1"
DIRECTORIO = Path(__file__).with_name("recursos") / "representante"
PLANTILLA_WORD = DIRECTORIO / f"{NOMBRE_DEL_ARCHIVO}.docx"
BASE_PDF = DIRECTORIO / f"{NOMBRE_DEL_ARCHIVO}-base.pdf"
TEXTO_CANONICO = DIRECTORIO / f"{NOMBRE_DEL_ARCHIVO}-texto.md"


SHA256_WORD = "3f6567e88f115923e467b352402dc693ce07e626a811bab191b69103e46e48db"
SHA256_BASE_PDF = "41e715e31fc59ff592a869210db9d8f3b7efd047d4293bbb876cae67b1bbdb22"
SHA256_TEXTO_CANONICO = "0b00e3e430b42fd951c65ffe0fa4cd6695abde7dc299f6ccbcdc8c7cf936b9e3"

MESES = (
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


class FormatoNoDisponible(RuntimeError):
    pass

def fecha_del_piloto() -> date:
    return datetime.now(ZONA_DEL_PILOTO).date()

def fecha_en_espanol(valor: date) -> str:
    return f"{valor.day} de {MESES[valor.month]} de {valor.year}"

def _leer_base_verificada() -> bytes:
    try:
        word = PLANTILLA_WORD.read_bytes()
        base = BASE_PDF.read_bytes()
        texto = TEXTO_CANONICO.read_bytes()
    except OSError as error:
        raise FormatoNoDisponible("la plantilla de autorización no está disponible") from error

    if hashlib.sha256(word).hexdigest() != SHA256_WORD:
        raise FormatoNoDisponible("la plantilla Word no coincide con la versión aprobada")
    if hashlib.sha256(base).hexdigest() != SHA256_BASE_PDF:
        raise FormatoNoDisponible("la base PDF no coincide con la exportación aprobada")
    if hashlib.sha256(texto).hexdigest() != SHA256_TEXTO_CANONICO:
        raise FormatoNoDisponible("el texto canónico no coincide con el documento aprobado")
    return base

def disponibilidad(version) -> str:
    if version is None:
        return "sin_version"
    if version.huella_contenido != SHA256_TEXTO_CANONICO:
        return "version_no_corresponde"
    try:
        _leer_base_verificada()
    except FormatoNoDisponible:
        return "plantilla_no_disponible"
    return "disponible"

def _capa_de_fecha(ancho: float, alto: float, texto: str) -> bytes:
    memoria = io.BytesIO()
    lienzo = Canvas(memoria, pagesize=(ancho, alto), pageCompression=1)
    lienzo.setFillColorRGB(80 / 255, 101 / 255, 116 / 255)
    lienzo.setFont("Helvetica", 8)

    lienzo.drawCentredString(ancho / 2, 45, texto)
    lienzo.save()
    return memoria.getvalue()

def generar_pdf(fecha: date | None = None) -> bytes:
    fecha_efectiva = fecha or fecha_del_piloto()
    texto = fecha_en_espanol(fecha_efectiva)
    origen = PdfReader(io.BytesIO(_leer_base_verificada()))
    salida = PdfWriter()

    for pagina in origen.pages:
        ancho = float(pagina.mediabox.width)
        alto = float(pagina.mediabox.height)
        capa = PdfReader(io.BytesIO(_capa_de_fecha(ancho, alto, texto))).pages[0]
        salida.add_page(pagina)

        salida.pages[-1].merge_page(capa)

    salida.add_metadata(
        {
            "/Title": "Autorización del representante legal de estudiante menor",
            "/Subject": "Piloto DidaxIA",
            "/DidaxIAFechaDescarga": fecha_efectiva.isoformat(),
            "/DidaxIAPlantilla": NOMBRE_DEL_ARCHIVO,
        }
    )
    memoria = io.BytesIO()
    salida.write(memoria)
    return memoria.getvalue()
