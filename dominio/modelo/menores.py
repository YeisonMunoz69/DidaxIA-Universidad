"""
menores.py — Asentimiento y autorización del representante (`EQ-016`, `EQ-021`)
================================================================================

Las **otras dos** dimensiones. `EQ-016` las declara independientes del
consentimiento y entre sí, y el encargo de la sesión 2 lo repite en negativo:
*«no conviertas “pendiente_representante” en un sustituto de las tres
dimensiones»*. Por eso aquí hay dos enumerados y no uno: un menor puede tener la
autorización aprobada y no haber dado su asentimiento, y ese caso tiene que poder
representarse sin que ninguna de las dos lo tape.

Asentimiento · el menor habla por sí mismo
---------------------------------------------------
Mismo mecanismo que el consentimiento del titular —eventos inmutables, `pendiente`
como ausencia— y un estado más: `NO_REQUERIDO`, para quien no es menor. Se deriva
de la edad, no se escribe: `EstadoAsentimiento.NO_REQUERIDO` no está en
`ESTADOS_REGISTRABLES` ni en el CHECK de `asentimiento_evento`.

Representante · el estado se deriva de los intentos, no se edita
------------------------------------------------------------------------
`EstadoRepresentante` no tiene tabla propia y es deliberado. Sus seis valores son
una función de tres cosas que sí están persistidas: si hace falta autorización,
qué intentos de carga hay y cómo se revisó el último. Una columna `estado` habría
sido una séptima verdad que puede quedarse vieja respecto de las revisiones.

El plazo de siete días
-----------------------------
`EQ-016`: siete días para **entregar** la autorización, no para usar el tutor.
Aquí se deriva `VENCIDO` cuando el plazo pasó sin ninguna carga de la versión
requerida.

✅ **Corregido en el cierre V-B.** Aquí decía que «nada la hace cumplir en esta
sesión» y que este módulo «no decide si el reloj arranca al declarar la edad o al
aceptar el consentimiento». Lo primero dejó de ser cierto y lo segundo era el
hueco por el que el plazo nunca vencía: lo fijaba el borde **al recibir el primer
PDF**, así que quien no subía ninguno —justo el caso que el plazo acota— conservaba
`representante_limite` en `NULL` para siempre.

Ahora el reloj arranca al declarar la minoría de edad, en la misma sentencia que
la escribe (`identidad_db.declarar_perfil()`), y `estado_representante()` deriva
`VENCIDO` de verdad. Lo que sigue sin existir es una **tarea programada**: nada
recorre la tabla buscando plazos vencidos, y no hace falta — el estado se calcula
al consultarlo, así que no hay ventana en la que la pantalla diga una cosa y la
base otra.

Vencer **no habilita ni deshabilita** por sí solo: un menor no queda habilitado
ni antes ni después del plazo, porque `dominio/modelo/acceso.py` siempre exige
autorización aprobada. Lo que cambia es lo que la pantalla puede explicar.

El archivo no vive en PostgreSQL
----------------------------------------
`EQ-021` deja el PDF en almacenamiento privado del equipo. `IntentoDeEvidencia`
guarda la **referencia opaca**, la huella, el tipo, el tamaño, el momento y **la
versión del documento firmado** — y rechaza una URL `http(s)` porque un enlace
mutable del Drive personal del estudiante no es evidencia definitiva. Las mismas
reglas están en el CHECK y en la clave foránea compuesta de
`representante_evidencia`, para que la base no dependa de que este tipo se use.

⚠️ No hay ni un campo de cédula, teléfono o correo del representante (`EQ-021`).


"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from dominio.modelo.comprobante import SHA256
from dominio.puertos.almacen import TransicionInvalida

_ENLACE = re.compile(r"^https?://", re.IGNORECASE)

#: `EQ-021`: PDF validado y 10 MB de límite inicial. Los dos se comprueban aquí y
#: otra vez en la base; el borde de la sesión 3 los comprobará una tercera vez
#: antes de aceptar la subida, que es donde el mensaje puede ser útil.
TIPO_MIME_ESPERADO = "application/pdf"
TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024

#: `EQ-016`. Días para cargar la autorización, contados **desde que la persona
#: declara ser menor de edad** (hito R4). El momento lo fija `persona.
#: representante_limite` con el reloj de PostgreSQL, dentro del mismo `UPDATE`
#: que escribe la edad; ver `identidad_db.declarar_perfil()`.
PLAZO_REPRESENTANTE_DIAS = 7


class EvidenciaInvalida(ValueError):
    """Un metadato de evidencia que el sistema no puede aceptar."""


class EstadoAsentimiento(StrEnum):
    """Los cinco de `EQ-016`. `NO_REQUERIDO` y `PENDIENTE` se derivan."""

    NO_REQUERIDO = "no_requerido"
    PENDIENTE = "pendiente"
    OTORGADO = "otorgado"
    RECHAZADO = "rechazado"
    REVOCADO = "revocado"


ESTADOS_ASENTIMIENTO_REGISTRABLES: frozenset[EstadoAsentimiento] = frozenset(
    {
        EstadoAsentimiento.OTORGADO,
        EstadoAsentimiento.RECHAZADO,
        EstadoAsentimiento.REVOCADO,
    }
)


class EstadoRepresentante(StrEnum):
    """Los seis de `EQ-016`, derivados de intentos y revisiones."""

    NO_REQUERIDO = "no_requerido"
    PENDIENTE_DOCUMENTO = "pendiente_documento"
    DOCUMENTO_RECIBIDO = "documento_recibido"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    VENCIDO = "vencido"


class ResultadoDeRevision(StrEnum):
    """Lo que un investigador autorizado puede decidir sobre un intento."""

    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


#: Transiciones del asentimiento. Idénticas en forma a las del consentimiento, y
#: escritas aparte porque son dimensiones distintas: si algún día una cambia, la
#: otra no debe cambiar por compartir tabla.
TRANSICIONES_ASENTIMIENTO: dict[EstadoAsentimiento, frozenset[EstadoAsentimiento]] = {
    # De `NO_REQUERIDO` no se sale con un evento: se sale declarando una edad
    # menor de 18, y entonces el estado derivado pasa a `PENDIENTE`.
    EstadoAsentimiento.NO_REQUERIDO: frozenset(),
    EstadoAsentimiento.PENDIENTE: frozenset(
        {EstadoAsentimiento.OTORGADO, EstadoAsentimiento.RECHAZADO}
    ),
    EstadoAsentimiento.OTORGADO: frozenset({EstadoAsentimiento.REVOCADO}),
    EstadoAsentimiento.RECHAZADO: frozenset({EstadoAsentimiento.OTORGADO}),
    EstadoAsentimiento.REVOCADO: frozenset({EstadoAsentimiento.OTORGADO}),
}

#: Transiciones del representante. No gobiernan una columna —el estado se
#: deriva—: gobiernan qué movimientos son coherentes, y por eso las usan las
#: pruebas y el borde para rechazar una revisión imposible antes de escribirla.
TRANSICIONES_REPRESENTANTE: dict[EstadoRepresentante, frozenset[EstadoRepresentante]] = {
    EstadoRepresentante.NO_REQUERIDO: frozenset({EstadoRepresentante.PENDIENTE_DOCUMENTO}),
    EstadoRepresentante.PENDIENTE_DOCUMENTO: frozenset(
        {EstadoRepresentante.DOCUMENTO_RECIBIDO, EstadoRepresentante.VENCIDO}
    ),
    EstadoRepresentante.DOCUMENTO_RECIBIDO: frozenset(
        {EstadoRepresentante.APROBADO, EstadoRepresentante.RECHAZADO}
    ),
    # Una carga nueva conserva el intento anterior y devuelve la dimensión a
    # «documento recibido»; nunca al revés.
    EstadoRepresentante.APROBADO: frozenset({EstadoRepresentante.DOCUMENTO_RECIBIDO}),
    EstadoRepresentante.RECHAZADO: frozenset({EstadoRepresentante.DOCUMENTO_RECIBIDO}),
    EstadoRepresentante.VENCIDO: frozenset({EstadoRepresentante.DOCUMENTO_RECIBIDO}),
}


def transicion_asentimiento_admitida(
    desde: EstadoAsentimiento, hacia: EstadoAsentimiento
) -> bool:
    if hacia not in ESTADOS_ASENTIMIENTO_REGISTRABLES:
        return False
    return hacia in TRANSICIONES_ASENTIMIENTO[desde]


def exigir_transicion_asentimiento(
    desde: EstadoAsentimiento, hacia: EstadoAsentimiento
) -> None:
    if not transicion_asentimiento_admitida(desde, hacia):
        raise TransicionInvalida(
            f"el asentimiento no puede pasar de {desde.value!r} a {hacia.value!r}"
        )


def exigir_transicion_representante(
    desde: EstadoRepresentante, hacia: EstadoRepresentante
) -> None:
    if hacia not in TRANSICIONES_REPRESENTANTE[desde]:
        raise TransicionInvalida(
            f"la autorización del representante no puede pasar de "
            f"{desde.value!r} a {hacia.value!r}"
        )


def fecha_limite(desde: datetime, dias: int = PLAZO_REPRESENTANTE_DIAS) -> datetime:
    """`desde` + siete días. Una función y no un cálculo repetido en cada sitio."""
    return desde + timedelta(days=dias)


@dataclass(frozen=True, slots=True)
class EventoAsentimiento:
    """Un acto del menor sobre su propio asentimiento. Mismo contrato que
    `EventoConsentimiento`: inmutable, con versión y comprobante."""

    sujeto_google: str
    version: str
    estado: EstadoAsentimiento
    comprobante: str
    momento: datetime
    secuencia: int = 0

    def __post_init__(self) -> None:
        for campo in ("sujeto_google", "version"):
            valor = getattr(self, campo)
            if not isinstance(valor, str) or not valor.strip():
                raise EvidenciaInvalida(f"{campo} no puede quedar vacío")
            object.__setattr__(self, campo, valor.strip())
        estado = EstadoAsentimiento(self.estado)
        if estado not in ESTADOS_ASENTIMIENTO_REGISTRABLES:
            raise EvidenciaInvalida(f"{estado.value!r} no es un acto de asentimiento")
        object.__setattr__(self, "estado", estado)
        if not SHA256.fullmatch(self.comprobante or ""):
            raise EvidenciaInvalida("comprobante tiene que ser un SHA-256 en minúsculas")
        if not isinstance(self.momento, datetime):
            raise EvidenciaInvalida("momento tiene que ser una fecha")


@dataclass(frozen=True, slots=True)
class HistorialDeAsentimiento:
    """Los eventos de asentimiento ya ordenados, y el estado que se deriva.

    `requerido` viene de la edad y no de los eventos: sin él, un menor sin
    eventos y un adulto sin eventos darían el mismo estado, y no son lo mismo.
    """

    sujeto_google: str
    requerido: bool
    eventos: tuple[EventoAsentimiento, ...] = field(default_factory=tuple)

    @property
    def ultimo(self) -> EventoAsentimiento | None:
        return self.eventos[-1] if self.eventos else None

    @property
    def estado(self) -> EstadoAsentimiento:
        """`NO_REQUERIDO` para un adulto, **aunque tenga eventos**.

        Esa precedencia es la corrección que pidió la revisión. Quien dio su
        asentimiento a los 17 conserva la fila —es historia y no se borra— pero al
        cumplir 18 esa dimensión deja de corresponderle: si el último evento
        siguiera mandando, un asentimiento rechazado o revocado de cuando era
        menor bloquearía para siempre a una persona mayor de edad a la que ya
        nadie le pide asentimiento.

        Para un menor sin eventos es `PENDIENTE`, que es distinto de
        `NO_REQUERIDO`: hace falta y todavía no está.
        """
        if not self.requerido:
            return EstadoAsentimiento.NO_REQUERIDO
        ultimo = self.ultimo
        return ultimo.estado if ultimo is not None else EstadoAsentimiento.PENDIENTE

    @property
    def version_vigente(self) -> str | None:
        """La versión del último acto, o `None`. Para un adulto no hay ninguna
        vigente aunque queden filas históricas."""
        if not self.requerido:
            return None
        ultimo = self.ultimo
        return ultimo.version if ultimo is not None else None


@dataclass(frozen=True, slots=True)
class RevisionDeEvidencia:
    """Quién resolvió un intento, cuándo y por qué.

    El motivo es obligatorio al rechazar (`EQ-021`: «motivo comprensible de
    rechazo») y se rechaza vacío aquí y en el CHECK de la tabla: un rechazo sin
    motivo deja a quien cargó el documento sin saber qué corregir.
    """

    resultado: ResultadoDeRevision
    revisada_por: str
    revisada_en: datetime
    motivo: str = ""
    secuencia: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "resultado", ResultadoDeRevision(self.resultado))
        if not isinstance(self.revisada_por, str) or not self.revisada_por.strip():
            raise EvidenciaInvalida("una revisión conserva quién la realizó")
        object.__setattr__(self, "revisada_por", self.revisada_por.strip())
        if not isinstance(self.revisada_en, datetime):
            raise EvidenciaInvalida("una revisión conserva cuándo se realizó")
        motivo = (self.motivo or "").strip()
        if self.resultado is ResultadoDeRevision.RECHAZADA and not motivo:
            raise EvidenciaInvalida("un rechazo exige un motivo comprensible")
        object.__setattr__(self, "motivo", motivo)


@dataclass(frozen=True, slots=True)
class IntentoDeEvidencia:
    """Los metadatos de una carga. El archivo está en otro sitio.

    `referencia` es opaca y estable: un identificador del almacenamiento privado
    del equipo, no una dirección navegable. Se rechaza cualquier `http(s)://`
    porque es exactamente la forma que tiene el enlace de Drive que `EQ-021`
    descarta como evidencia definitiva.
    """

    sujeto_google: str
    intento: int
    #: Qué versión del documento del representante se firmó. Obligatoria desde la
    #: corrección de la revisión: sin ella, una autorización firmada sobre un
    #: texto retirado parecería cubrir el que rige hoy. La base exige además que
    #: sea de alcance `representante`, con clave foránea compuesta.
    version: str
    referencia: str
    sha256: str
    tamano_bytes: int
    tipo_mime: str = TIPO_MIME_ESPERADO
    recibido_en: datetime | None = None
    revision: RevisionDeEvidencia | None = None
    secuencia: int = 0

    def __post_init__(self) -> None:
        for campo in ("sujeto_google", "version"):
            valor = getattr(self, campo)
            if not isinstance(valor, str) or not valor.strip():
                raise EvidenciaInvalida(f"{campo} no puede quedar vacío")
            object.__setattr__(self, campo, valor.strip())
        if isinstance(self.intento, bool) or not isinstance(self.intento, int) or self.intento < 1:
            raise EvidenciaInvalida("el número de intento empieza en 1")
        referencia = (self.referencia or "").strip()
        if not referencia:
            raise EvidenciaInvalida("una evidencia sin referencia no se puede recuperar")
        if _ENLACE.match(referencia):
            raise EvidenciaInvalida(
                "la referencia no puede ser un enlace http(s): EQ-021 descarta un "
                "enlace mutable como evidencia definitiva"
            )
        object.__setattr__(self, "referencia", referencia)
        if not SHA256.fullmatch(self.sha256 or ""):
            raise EvidenciaInvalida("sha256 tiene que ser un SHA-256 en minúsculas")
        if self.tipo_mime != TIPO_MIME_ESPERADO:
            raise EvidenciaInvalida(f"la evidencia se recibe como {TIPO_MIME_ESPERADO}")
        if (
            isinstance(self.tamano_bytes, bool)
            or not isinstance(self.tamano_bytes, int)
            or not 0 < self.tamano_bytes <= TAMANO_MAXIMO_BYTES
        ):
            raise EvidenciaInvalida(
                f"el tamaño tiene que estar entre 1 y {TAMANO_MAXIMO_BYTES} bytes"
            )


def estado_representante(
    intentos: tuple[IntentoDeEvidencia, ...],
    *,
    requerido: bool,
    version_requerida: str | None = None,
    limite: datetime | None = None,
    ahora: datetime | None = None,
) -> EstadoRepresentante:
    """Los seis estados de `EQ-016`, derivados y no almacenados.

    El orden de las preguntas es el contrato:

    1. si no hace falta autorización, `NO_REQUERIDO` y se acaba — y se acaba
       **antes** de mirar los intentos, para que una evidencia cargada cuando la
       persona era menor no siga hablando después de que cumpla 18;
    2. sin una versión requerida vigente no hay documento que firmar, así que
       nada puede estar aprobado: `PENDIENTE_DOCUMENTO`;
    3. sólo cuentan los intentos **de esa versión**. Es la corrección que pidió la
       revisión: una autorización firmada sobre un texto anterior no autoriza el
       que rige hoy, y publicar una versión nueva del documento del representante
       exige una carga nueva;
    4. sin intentos de la versión requerida, `PENDIENTE_DOCUMENTO` — o `VENCIDO`
       si el plazo pasó, que sigue sin habilitar nada y sólo cambia lo que la
       pantalla explica;
    5. con intentos manda **el último**, y su revisión decide: sin revisar es
       `DOCUMENTO_RECIBIDO`, revisado es `APROBADO` o `RECHAZADO`.

    Que mande el último intento es lo que hace que volver a cargar después de un
    rechazo sirva de algo, **sin borrar** el rechazo anterior: sigue estando en
    la lista y en la base.
    """
    if not requerido:
        return EstadoRepresentante.NO_REQUERIDO
    if version_requerida is None:
        return EstadoRepresentante.PENDIENTE_DOCUMENTO
    de_la_version = tuple(i for i in intentos if i.version == version_requerida)
    if not de_la_version:
        if limite is not None and ahora is not None and ahora > limite:
            return EstadoRepresentante.VENCIDO
        return EstadoRepresentante.PENDIENTE_DOCUMENTO
    ultimo = max(de_la_version, key=lambda intento: intento.intento)
    if ultimo.revision is None:
        return EstadoRepresentante.DOCUMENTO_RECIBIDO
    if ultimo.revision.resultado is ResultadoDeRevision.APROBADA:
        return EstadoRepresentante.APROBADO
    return EstadoRepresentante.RECHAZADO
