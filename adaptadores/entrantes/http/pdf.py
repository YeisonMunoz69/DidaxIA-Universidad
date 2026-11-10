"""
pdf.py — ¿Es esto un PDF de verdad? (`EQ-021`, hito R4)
========================================================

`EQ-021` dice que *«la evidencia firmada se recibe como PDF validado»*. Hasta el
cierre V-B, «validado» significaba esto:

    if not contenido.startswith(b"%PDF-"):

Cinco bytes. Cualquier archivo que empiece por `%PDF-` pasaba: un `.txt`, medio
PDF cortado a mitad de la subida, un documento cifrado que el equipo no puede
abrir. La auditoría V-B lo devolvió dentro de su séptimo invariante, y el motivo
es concreto: **una autorización de representante legal que no se puede abrir no
es evidencia de nada**, y descubrirlo dentro de seis meses —cuando alguien vaya a
verificarla— es descubrirlo cuando ya no hay a quién pedirle otra copia.

La comprobación tiene que ocurrir **antes** de reservar el archivo. Aceptar y
rechazar después dejaría una carga provisional que compensar por algo que se
podía haber visto al llegar.

Por qué una dependencia y no un lector propio
--------------------------------------------------------
`pypdf` está en `requirements.txt` desde este hito. Escribir un lector de la
estructura de un PDF a mano —tabla de referencias cruzadas, objetos indirectos,
flujos comprimidos, versiones incrementales— sería reimplementar mal una
biblioteca mantenida, y hacerlo sobre un archivo que llega de fuera. `EQ-021`
pide validar, no tener un analizador propio.

⚠️ Se abre para comprobar que se abre, y nada más
--------------------------------------------------------
**No se extrae texto, no se cuentan palabras, no se leen metadatos y no se
registra nada de lo que hay dentro.** `EQ-021` manda custodiar el documento, no
analizarlo: cualquier cosa que se sacara de él sería una superficie de dato nueva
—con nombres, firmas y datos de un tercero que ni siquiera es usuario del
sistema— creada por el acto de validar. Lo único que sale de aquí es «sirve» o
«no sirve, por esto».

Por la misma razón **no hay `logging`**: un mensaje de error de un analizador de
PDF puede llevar dentro fragmentos del archivo, y ese mensaje acabaría en una
consola y en un registro. Los motivos que este módulo devuelve son suyos, escritos
aquí, y ninguno interpola nada del contenido.

Qué se rechaza, y por qué cada cosa
-----------------------------------------------
- **no abre** · truncado, corrupto o simplemente no es un PDF;
- **cifrado que no se puede abrir** · el equipo no tendría cómo verificarlo, y
  guardar algo ilegible es guardar un problema para más tarde;
- **sin páginas** · un PDF estructuralmente válido y vacío no contiene ninguna
  firma.

Lo que **no** se comprueba es que el contenido *sea* una autorización: eso lo
verifica una persona (`EQ-016`: «un investigador autorizado verifica la
evidencia»), y un sistema que lo decidiera solo estaría inventando un criterio
que el equipo no ha dado.


"""

from __future__ import annotations


class PdfInutilizable(ValueError):
    """El archivo no es un PDF que el equipo pueda abrir y verificar.

    Un solo tipo para los tres casos: al cliente le llegan como el mismo 415 —el
    archivo no sirve— y distinguirlos en el tipo sólo habría servido para que
    alguien los tratara distinto sin motivo. El **mensaje** sí los distingue,
    porque quien sube el documento necesita saber qué corregir.
    """


#: Los cinco bytes de la firma. Se siguen comprobando **antes** de abrir nada:
#: es una comparación de bytes contra una llamada a un analizador, y descarta lo
#: obvio sin pagar el coste. Lo que cambió es que ya no son la única comprobación.
FIRMA = b"%PDF-"


def exigir_pdf_utilizable(contenido: bytes) -> None:
    """Levanta `PdfInutilizable` si el archivo no sirve como evidencia.

    No devuelve nada: no hay ninguna información del documento que este módulo
    deba entregar. Ver la cabecera.
    """
    if not contenido.startswith(FIRMA):
        raise PdfInutilizable("el archivo no empieza por la firma de un PDF")

    # Importación tardía, mismo criterio que `conexion.py` con Psycopg: quien no
    # vaya a validar un PDF no debería tropezar con la dependencia al importar el
    # borde HTTP entero.
    from io import BytesIO  # noqa: PLC0415

    from pypdf import PdfReader  # noqa: PLC0415
    from pypdf.errors import PyPdfError  # noqa: PLC0415

    try:
        lector = PdfReader(BytesIO(contenido))
    except (PyPdfError, ValueError, OSError, RecursionError) as error:
        # El texto del analizador **no** viaja: puede llevar fragmentos del
        # archivo. Se encadena con `from None` por la misma razón que
        # `base_postgres._traducir()`.
        raise PdfInutilizable(
            f"el archivo no se puede abrir como PDF ({type(error).__name__})"
        ) from None

    if getattr(lector, "is_encrypted", False):
        # `pypdf` abre un PDF cifrado con contraseña vacía, así que llegar aquí
        # con `is_encrypted` significa que hay cifrado de verdad. No se intenta
        # descifrarlo: el equipo no tiene la clave y adivinarla no es validar.
        raise PdfInutilizable(
            "el archivo está cifrado y el equipo no podría abrirlo para verificarlo"
        )

    try:
        paginas = len(lector.pages)
    except (PyPdfError, ValueError, OSError, RecursionError) as error:
        # Un PDF puede abrir y romperse al recorrer su árbol de páginas: la
        # cabecera y la tabla de referencias están, y el catálogo no. Es el caso
        # de un archivo truncado que conservó su cola.
        raise PdfInutilizable(
            f"el árbol de páginas del PDF no es utilizable ({type(error).__name__})"
        ) from None

    if paginas < 1:
        raise PdfInutilizable("el PDF no tiene ninguna página")
