r"""
instantanea_consentimiento.py — El texto exacto que se leyó, y su huella
===========================================================================

Lo que este módulo cierra, y por qué hacía falta
---------------------------------------------------
`DecisionConjunta.svelte` le dice a la persona, literalmente:

    «La huella identifica el texto exacto que estás leyendo. La calcula el
    servidor y queda guardada con tu decisión.»

**Esa afirmación no era cierta**, y la revisión R2 lo comprobó leyendo las dos
puntas:

1. `consentimiento_version` guarda `huella_contenido` y **no** guarda el texto.
   `version_como_json()` lo dice sin rodeos: *«El texto no viaja porque no
   existe: `consentimiento_version` guarda la huella de lo publicado, no lo
   publicado»*.
2. Lo único que la pantalla ofrece **leer** son cuatro enlaces —privacidad,
   condiciones, investigación— a las páginas públicas del sitio, construidas
   con `enlacePublico()`. Son páginas genéricas y editables, no el artefacto
   que se hasheó.
3. La única huella que existe hoy la calcula `infraestructura/demostracion/
   semilla.py` sobre un archivo que escribe en una **carpeta privada fuera del
   repositorio**, que la persona no abre desde la aplicación.

Es decir: el texto mostrado y el texto hasheado eran **dos artefactos
distintos**. La huella era verificable —el archivo existe y se puede recalcular
su SHA-256— pero no era la huella de lo que la pantalla enseñaba, y la frase de
la interfaz prometía justo eso. Una huella que no identifica lo leído no
demuestra qué se aceptó, que es lo único para lo que sirve.

Lo que este módulo aporta: **una instantánea canónica**
----------------------------------------------------------
Una instantánea es el cuerpo completo del documento, inmutable, guardado junto
a su versión, y **la huella se calcula sobre sus bytes canónicos**. El mismo
artefacto que la persona lee es el que se hashea, y por eso la frase de la
pantalla pasa a ser verdad en vez de una intención.

No se guarda una ruta ni una URL: se guarda **el cuerpo**. Una ruta apunta a
algo que puede cambiar sin que la huella cambie, que es exactamente el fallo
que se está cerrando.

Qué son los «bytes canónicos», y por qué tan pocos
------------------------------------------------------
La huella tiene que ser **reproducible por un tercero**: alguien que reciba el
texto años después debe poder recalcular el SHA-256 y obtener el mismo valor.
Eso exige decir sin ambigüedad qué bytes se hashean. Aquí son:

1. **NFC** (`unicodedata.normalize`). Sin esto, «í» escrita como un carácter y
   como `i` + tilde combinante son dos secuencias de bytes distintas del mismo
   texto visible, y el mismo documento tendría dos huellas según con qué editor
   se guardó.
2. **Saltos de línea `LF`**. `CRLF` y `CR` se convierten. Un documento editado
   en Windows y otro en Linux son el mismo documento; que Git o un editor
   cambien los finales de línea no puede cambiar lo que la persona aceptó.
3. **Exactamente un `\n` final**, y ninguno de más. Es la diferencia clásica
   entre dos copias del mismo archivo.
4. **UTF-8** al codificar.

⚠️ **Y nada más. Lo que NO se toca es tan deliberado como lo que sí.** No se
recortan espacios al final de cada línea, no se colapsan líneas en blanco, no
se reindenta y no se normaliza el ancho de los espacios. Dos motivos:

- en Markdown, **dos espacios al final de una línea son un salto de línea**;
  recortarlos cambiaría el documento que la persona lee mientras se afirma que
  se está canonicalizando su forma, no su contenido;
- cada transformación de más es una forma de que dos textos distintos produzcan
  la misma huella. Una canonicalización agresiva **acerca** documentos, y aquí
  se quiere lo contrario: que cambiar una coma cambie la huella.

Cambiar una coma exige una versión nueva · `§8.5`
------------------------------------------------------
Es una consecuencia de lo anterior y no una regla aparte: si el cuerpo cambia,
la huella cambia, y una versión publicada **no se edita**. Quien quiera
corregir una coma publica otro código. Lo que sostiene esa regla no es este
módulo sino la base —la instantánea es inmutable por disparador— y la
herramienta de publicación, que se detiene si encuentra el mismo código con
otro contenido en vez de sobrescribirlo.

Este módulo no habla con la base ni con HTTP
------------------------------------------------
Son funciones puras sobre texto. La instantánea se guarda por
`dominio/puertos/instantaneas.py`, se sirve por
`adaptadores/entrantes/http/rutas/consentimiento.py` y se publica con
`infraestructura/operacion/publicar_consentimiento.py`. Aquí sólo está **qué se
hashea**, que es la definición de la que dependen las otras tres.


"""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass
from datetime import datetime

from dominio.modelo.consentimiento import (
    FINALIDADES_OBLIGATORIAS,
    Alcance,
    ConsentimientoInvalido,
    Finalidad,
)

#: El medio de la instantánea. Uno solo, y declarado: servir un cuerpo cuyo tipo
#: se adivina es la vía corta a que un navegador lo interprete como otra cosa.
#: Si algún día hay otro, se añade aquí y en el `CHECK` de la migración — no se
#: acepta lo que venga en un manifiesto.
MEDIO_MARKDOWN = "text/markdown"

MEDIOS_ADMITIDOS = (MEDIO_MARKDOWN,)

#: Tope del cuerpo de una instantánea. Un documento de consentimiento son
#: páginas, no megabytes; el límite existe para que un manifiesto equivocado
#: —un PDF, un volcado— se detenga aquí y no en la base.
LIMITE_BYTES = 512 * 1024


def canonicalizar(texto: str) -> str:
    """El texto en su forma canónica. Ver «bytes canónicos» en la cabecera.

    Cuatro transformaciones, ni una más: NFC, saltos `LF`, exactamente un salto
    final y —al codificar— UTF-8. Lo que no se toca está enumerado arriba y es
    igual de deliberado: recortar espacios al final de línea cambiaría el
    documento en Markdown, y cada transformación de más es una forma de que dos
    textos distintos acaben con la misma huella.
    """
    if not isinstance(texto, str):
        raise ConsentimientoInvalido("la instantánea tiene que ser texto")
    # El orden importa poco entre estas dos, pero se fija para que sea
    # reproducible: primero los saltos, después la normalización Unicode.
    plano = texto.replace("\r\n", "\n").replace("\r", "\n")
    plano = unicodedata.normalize("NFC", plano)
    return plano.rstrip("\n") + "\n"


def bytes_canonicos(texto: str) -> bytes:
    """Los bytes exactos sobre los que se calcula la huella.

    Se expone aparte de `huella_de()` a propósito: es lo que hay que servir al
    navegador para que lo que se lee sean **estos** bytes y no una reserialización
    con otras comillas o con otro final de línea. La ruta HTTP lo usa.
    """
    return canonicalizar(texto).encode("utf-8")


def huella_de(texto: str) -> str:
    """El SHA-256 de los bytes canónicos, en minúsculas.

    Es el valor que se guarda en `consentimiento_version.huella_contenido` y el
    que la pantalla enseña. Un tercero que reciba el cuerpo puede recalcularlo
    con `sha256` sobre el archivo tal cual, siempre que el archivo esté ya en
    forma canónica — y lo está, porque es lo que se guardó.
    """
    return hashlib.sha256(bytes_canonicos(texto)).hexdigest()


@dataclass(frozen=True, slots=True)
class InstantaneaDeVersion:
    """El documento publicado de una versión: su cuerpo exacto y su huella.

    El cuerpo se canonicaliza **al construirla**, así que una instantánea mal
    formada no existe: no hay un momento en el que el objeto tenga un cuerpo sin
    normalizar y una huella calculada sobre otra cosa.

    `huella` no es un campo que se pase: se **deriva**. Recibirla desde fuera
    permitiría construir una instantánea cuya huella no fuera la de su cuerpo,
    que es precisamente lo que este módulo existe para impedir.
    """

    codigo: str
    alcance: Alcance
    cuerpo: str
    medio: str = MEDIO_MARKDOWN

    def __post_init__(self) -> None:
        if not isinstance(self.codigo, str) or not self.codigo.strip():
            raise ConsentimientoInvalido("la instantánea necesita el código de su versión")
        object.__setattr__(self, "codigo", self.codigo.strip())
        object.__setattr__(self, "alcance", Alcance(self.alcance))
        if self.medio not in MEDIOS_ADMITIDOS:
            raise ConsentimientoInvalido(
                f"medio «{self.medio}» no admitido; los admitidos son "
                f"{', '.join(MEDIOS_ADMITIDOS)}"
            )
        cuerpo = canonicalizar(self.cuerpo)
        if not cuerpo.strip():
            # Una instantánea vacía habilitaría una decisión sobre nada, que es
            # la misma situación que el sistema evita cuando no hay versión.
            raise ConsentimientoInvalido(
                "la instantánea no puede estar vacía: sin texto no hay nada que leer"
            )
        if len(cuerpo.encode("utf-8")) > LIMITE_BYTES:
            raise ConsentimientoInvalido(
                f"la instantánea supera {LIMITE_BYTES} bytes; un documento de "
                "consentimiento son páginas, no un volcado"
            )
        object.__setattr__(self, "cuerpo", cuerpo)

    @property
    def huella(self) -> str:
        """La huella de **este** cuerpo. Derivada, nunca recibida."""
        return huella_de(self.cuerpo)

    @property
    def bytes_canonicos(self) -> bytes:
        return bytes_canonicos(self.cuerpo)

    def coincide_con(self, huella: str) -> bool:
        """Si una huella publicada es la de este cuerpo.

        Lo usa la ruta que sirve la instantánea: enseñar un cuerpo cuya huella
        no es la que la versión declara sería volver al defecto de partida, con
        el agravante de que ahora la pantalla afirmaría haberlo comprobado.
        """
        return isinstance(huella, str) and huella.lower() == self.huella


@dataclass(frozen=True, slots=True)
class PublicacionDeVersion:
    """Todo lo que hace falta para publicar una versión, ya validado.

    Junta la instantánea con los metadatos que van a `consentimiento_version`.
    Existe para que la herramienta de publicación no tenga que llevar seis
    variables sueltas de un lado a otro y para que «lo que se va a publicar»
    sea **un** objeto que se puede enseñar en un `--dry-run` y comparar con lo
    que la base ya tiene.
    """

    instantanea: InstantaneaDeVersion
    finalidades: frozenset[Finalidad]
    vigente_desde: datetime
    vigente_hasta: datetime | None = None

    def __post_init__(self) -> None:
        finalidades = frozenset(Finalidad(f) for f in self.finalidades)
        faltan = FINALIDADES_OBLIGATORIAS - finalidades
        if faltan:
            # La misma regla que `VersionDeConsentimiento` y por el mismo
            # motivo (`EQ-021`): una versión que no cubre las finalidades
            # obligatorias habilitaría el tutor autorizando menos de lo que el
            # sistema hace. Se comprueba **aquí y no sólo al escribir** para que
            # un `--dry-run` la detecte antes de que nadie confirme nada.
            raise ConsentimientoInvalido(
                "una versión publicada tiene que cubrir todas las finalidades "
                f"obligatorias; faltan {sorted(f.value for f in faltan)}"
            )
        object.__setattr__(self, "finalidades", finalidades)
        if not isinstance(self.vigente_desde, datetime):
            raise ConsentimientoInvalido("vigente_desde tiene que ser una fecha")
        if self.vigente_hasta is not None and self.vigente_hasta <= self.vigente_desde:
            raise ConsentimientoInvalido(
                "vigente_hasta tiene que ser posterior a vigente_desde"
            )

    @property
    def codigo(self) -> str:
        return self.instantanea.codigo

    @property
    def alcance(self) -> Alcance:
        return self.instantanea.alcance

    @property
    def huella(self) -> str:
        return self.instantanea.huella
