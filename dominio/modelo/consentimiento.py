"""
consentimiento.py — Estados, finalidades, versiones y eventos (`EQ-016`, `EQ-021`)
===================================================================================

El consentimiento versionado como tipos, no como cadenas sueltas. Es la mitad
del contrato de la Fase 3 · sesión 1 que el sistema **no** podía expresar hasta
hoy: `consentimiento_usuario` (`07-consentimiento-usuario.sql`) tiene una fila
por titular con `decision IN ('otorgado','rechazado')` y un `ON CONFLICT DO
UPDATE`, así que no hay versión, no hay finalidades, no hay revocación y no hay
historial —reaceptar pisaba el rechazo anterior—.

⚠️ **Esto no reemplaza todavía a aquello.** El puerto heredado
(`dominio/puertos/consentimiento.py`) y sus dos adaptadores siguen intactos y
son los que las rutas HTTP consumen. Conectar las rutas al modelo nuevo es la
sesión 3.

Cuatro estados, tres registrables
------------------------------------
`pendiente` es la **ausencia** de eventos, no un evento. No se puede escribir, y
por eso `ESTADOS_REGISTRABLES` tiene tres valores y el enumerado cuatro. Guardar
un `pendiente` habría creado un estado escribible que un error de código podría
confundir con una decisión tomada — y `EQ-016` es explícito en que no existe un
valor por defecto que equivalga a otorgado.

Por qué la versión es un tipo y no un número de serie
-------------------------------------------------------------
`EQ-021` exige que el evento conserve versión, alcance, finalidades, fecha y
comprobante. Versión, alcance y finalidades no son del evento: son del
**documento** que se aceptó, iguales para todas las personas que aceptaron esa
versión. Repetirlos en cada evento los habría dejado divergir.

⚠️ **Ninguna versión se define aquí.** El texto final del consentimiento sigue
en `DECISIONES.md` § Decisiones abiertas. Este módulo describe la forma que
tendrá una versión cuando exista; construir una con un código inventado sería
fabricar la autorización.

`alcance` · tres documentos que no son el mismo
--------------------------------------------------------
`EQ-016` y `EQ-021` describen el consentimiento del titular, el asentimiento del
menor y la autorización del representante como piezas distintas. Cada dimensión
referencia una versión de **su** alcance; sin esta distinción, aceptar el
consentimiento parecería aceptar los tres.


"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from dominio.modelo.comprobante import SHA256
from dominio.modelo.identidad import CategoriaDeEdad
from dominio.puertos.almacen import TransicionInvalida


class ConsentimientoInvalido(ValueError):
    """Un valor que no puede formar parte de una versión o de un evento."""


class EstadoConsentimiento(StrEnum):
    """Los cuatro de `EQ-016`. `PENDIENTE` no se escribe: se deriva."""

    PENDIENTE = "pendiente"
    OTORGADO = "otorgado"
    RECHAZADO = "rechazado"
    REVOCADO = "revocado"


#: Lo que sí es un acto y por tanto una fila. El CHECK de `consentimiento_evento`
#: en `11-identidad-consentimiento.sql` admite exactamente estos tres.
ESTADOS_REGISTRABLES: frozenset[EstadoConsentimiento] = frozenset(
    {
        EstadoConsentimiento.OTORGADO,
        EstadoConsentimiento.RECHAZADO,
        EstadoConsentimiento.REVOCADO,
    }
)


class Finalidad(StrEnum):
    """Las seis de `EQ-021`, ni una más.

    Enumerado y no `str` libre porque el encargo lo pide con todas las letras:
    «no almacenes estas finalidades como texto libre sin validación». El catálogo
    equivalente en la base es la tabla `consentimiento_finalidad`, y
    `pruebas/unidad/test_dominio_consentimiento.py` comprueba que los dos digan
    lo mismo.
    """

    AUTENTICACION_Y_SEGURIDAD = "autenticacion_y_seguridad"
    HISTORIAL_CONVERSACIONAL = "historial_conversacional"
    PERFIL_CONDUCTUAL = "perfil_conductual"
    PERSONALIZACION_PEDAGOGICA = "personalizacion_pedagogica"
    INVESTIGACION = "investigacion"
    VISUALIZACION_DOCENTE = "visualizacion_docente"


#: Las finalidades que `EQ-021` declara **obligatorias** para la aceptación
#: única de la versión inicial. Hoy son las seis del enumerado entero, y se
#: nombran aparte porque son cosas distintas: `Finalidad` es el vocabulario que
#: existe, esto es lo que una versión publicada tiene que cubrir para habilitar
#: el tutor.
#:
#: Una versión que declarara menos autorizaría menos de lo que el sistema hace
#: —historial, perfil conductual, visualización docente—, que es la forma más
#: silenciosa de incumplir. El mismo mínimo lo exige un disparador diferido sobre
#: `consentimiento_version`, para que no dependa de que la escritura pase por
#: este tipo.
FINALIDADES_OBLIGATORIAS: frozenset[Finalidad] = frozenset(Finalidad)


class Alcance(StrEnum):
    """A cuál de las tres dimensiones pertenece una versión publicada."""

    TITULAR = "titular"
    ASENTIMIENTO = "asentimiento"
    REPRESENTANTE = "representante"


#: Qué transición admite cada estado vigente, con la MISMA versión.
#:
#: - de `PENDIENTE` sólo se sale decidiendo; no se revoca lo que no se dio;
#: - `OTORGADO` sólo se deshace revocando (`EQ-022`: revocar bloquea, no borra);
#: - `RECHAZADO` y `REVOCADO` se deshacen volviendo a otorgar, y eso es un evento
#:   nuevo, nunca una corrección del anterior.
TRANSICIONES: dict[EstadoConsentimiento, frozenset[EstadoConsentimiento]] = {
    EstadoConsentimiento.PENDIENTE: frozenset(
        {EstadoConsentimiento.OTORGADO, EstadoConsentimiento.RECHAZADO}
    ),
    EstadoConsentimiento.OTORGADO: frozenset({EstadoConsentimiento.REVOCADO}),
    EstadoConsentimiento.RECHAZADO: frozenset({EstadoConsentimiento.OTORGADO}),
    EstadoConsentimiento.REVOCADO: frozenset({EstadoConsentimiento.OTORGADO}),
}


def transicion_admitida(
    desde: EstadoConsentimiento,
    hacia: EstadoConsentimiento,
    *,
    cambia_version: bool = False,
    cambia_categoria: bool = False,
) -> bool:
    """Si `hacia` puede seguir a `desde`.

    Las dos puertas de renovación son las dos que `EQ-021` enumera, y no una
    conveniencia:

    - **`cambia_version`** · «se vuelve a solicitar autorización ante cambios
      sustanciales de finalidad, categoría de datos, … destinatario o proveedor».
    - **`cambia_categoria`** · «…y cuando una persona participante cumple 18
      años». Ese caso ocurre con la MISMA versión vigente, así que sin esta
      segunda puerta el modelo rechazaría precisamente la reaceptación que la
      decisión obliga a pedir.

    Sin ninguna de las dos, repetir `otorgado` no es una decisión nueva: es un
    doble clic, y se rechaza.
    """
    if hacia not in ESTADOS_REGISTRABLES:
        return False
    if hacia in TRANSICIONES[desde]:
        return True
    return (
        (cambia_version or cambia_categoria)
        and desde in (EstadoConsentimiento.OTORGADO, EstadoConsentimiento.RECHAZADO)
        and hacia in (EstadoConsentimiento.OTORGADO, EstadoConsentimiento.RECHAZADO)
    )


def exigir_transicion(
    desde: EstadoConsentimiento,
    hacia: EstadoConsentimiento,
    *,
    cambia_version: bool = False,
    cambia_categoria: bool = False,
) -> None:
    """`transicion_admitida()`, pero levantando `TransicionInvalida`.

    Los repositorios llaman a ésta dentro de la transacción de escritura, de modo
    que un rechazo por transición se distingue de un fallo del almacén sin que
    quien llama tenga que comparar estados.
    """
    if not transicion_admitida(
        desde, hacia, cambia_version=cambia_version, cambia_categoria=cambia_categoria
    ):
        motivo = (
            ""
            if cambia_version or cambia_categoria
            else " sin un cambio de versión ni de categoría de edad"
        )
        raise TransicionInvalida(
            f"el consentimiento no puede pasar de {desde.value!r} a {hacia.value!r}{motivo}"
        )


def _huella_valida(valor: str, campo: str) -> str:
    if not isinstance(valor, str) or not SHA256.fullmatch(valor):
        raise ConsentimientoInvalido(f"{campo} tiene que ser un SHA-256 en minúsculas")
    return valor


def _codigo_valido(valor: str, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ConsentimientoInvalido(f"{campo} no puede quedar vacío")
    return valor.strip()


@dataclass(frozen=True, slots=True)
class VersionDeConsentimiento:
    """Un documento publicado: qué cubre, qué texto exacto y desde cuándo rige.

    `huella_contenido` es lo que permite demostrar años después qué leyó quien
    aceptó. Es obligatoria y con forma comprobada: una versión sin huella no
    prueba nada, y con una huella inventada probaría algo falso.
    """

    codigo: str
    alcance: Alcance
    finalidades: frozenset[Finalidad]
    huella_contenido: str
    vigente_desde: datetime
    vigente_hasta: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "codigo", _codigo_valido(self.codigo, "codigo"))
        object.__setattr__(self, "alcance", Alcance(self.alcance))
        finalidades = frozenset(Finalidad(f) for f in self.finalidades)
        faltan = FINALIDADES_OBLIGATORIAS - finalidades
        if faltan:
            # `EQ-021`: la aceptación cubre las finalidades obligatorias. Una
            # versión parcial habilitaría el tutor autorizando menos de lo que el
            # sistema hace. La misma regla la exige un disparador diferido, para
            # que no dependa de que la escritura pase por este tipo.
            raise ConsentimientoInvalido(
                "una versión publicada tiene que cubrir todas las finalidades "
                f"obligatorias; faltan {sorted(f.value for f in faltan)}"
            )
        object.__setattr__(self, "finalidades", finalidades)
        object.__setattr__(
            self, "huella_contenido", _huella_valida(self.huella_contenido, "huella_contenido")
        )
        if not isinstance(self.vigente_desde, datetime):
            raise ConsentimientoInvalido("vigente_desde tiene que ser una fecha")
        if self.vigente_hasta is not None and self.vigente_hasta <= self.vigente_desde:
            raise ConsentimientoInvalido("vigente_hasta tiene que ser posterior a vigente_desde")

    def vigente_en(self, momento: datetime) -> bool:
        if momento < self.vigente_desde:
            return False
        return self.vigente_hasta is None or momento < self.vigente_hasta


@dataclass(frozen=True, slots=True)
class EventoConsentimiento:
    """Un acto, no un estado que cambia.

    `secuencia` es el identificador monótono que asigna el almacén. Vale `0`
    mientras el evento no se ha persistido, y es lo que permite ordenar dos
    eventos con el mismo `momento` sin empate — ver
    `consentimiento_evento_por_sujeto` en la migración 11.
    """

    sujeto_google: str
    version: str
    estado: EstadoConsentimiento
    comprobante: str
    momento: datetime
    secuencia: int = 0
    #: La categoría de edad con la que se emitió el acto. **La deriva el almacén**
    #: desde `persona`, dentro de la misma transacción, y nunca la recibe de quien
    #: llama: `EQ-016` hace depender el régimen entero de la edad, y aceptarla
    #: como texto del borde habría dejado la regla de los 18 años en manos del
    #: cliente. Es `None` mientras el evento no está persistido.
    #:
    #: `NO_DECLARADA` no es un valor admisible: sin edad no hay régimen que
    #: aplicar y el consentimiento no se registra.
    categoria_edad: CategoriaDeEdad | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "sujeto_google", _codigo_valido(self.sujeto_google, "sujeto_google"))
        object.__setattr__(self, "version", _codigo_valido(self.version, "version"))
        if self.categoria_edad is not None:
            categoria = CategoriaDeEdad(self.categoria_edad)
            if categoria is CategoriaDeEdad.NO_DECLARADA:
                raise ConsentimientoInvalido(
                    "no se registra consentimiento sin edad declarada"
                )
            object.__setattr__(self, "categoria_edad", categoria)
        estado = EstadoConsentimiento(self.estado)
        if estado not in ESTADOS_REGISTRABLES:
            raise ConsentimientoInvalido(
                f"{estado.value!r} no es un acto: sólo se registran "
                f"{sorted(e.value for e in ESTADOS_REGISTRABLES)}"
            )
        object.__setattr__(self, "estado", estado)
        object.__setattr__(self, "comprobante", _huella_valida(self.comprobante, "comprobante"))
        if not isinstance(self.momento, datetime):
            raise ConsentimientoInvalido("momento tiene que ser una fecha")


@dataclass(frozen=True, slots=True)
class HistorialDeConsentimiento:
    """Los eventos de un titular, ya ordenados, y el estado que se deriva de ellos.

    El orden lo fija quien construye el historial —el repositorio, con
    `ORDER BY momento, id`— y este tipo lo conserva. Derivar el estado aquí y no
    en el repositorio hace que memoria y PostgreSQL no puedan discrepar.
    """

    sujeto_google: str
    eventos: tuple[EventoConsentimiento, ...] = field(default_factory=tuple)

    @property
    def ultimo(self) -> EventoConsentimiento | None:
        return self.eventos[-1] if self.eventos else None

    @property
    def estado(self) -> EstadoConsentimiento:
        """`PENDIENTE` sin eventos. Nunca `OTORGADO` por omisión."""
        ultimo = self.ultimo
        return ultimo.estado if ultimo is not None else EstadoConsentimiento.PENDIENTE

    @property
    def version_vigente(self) -> str | None:
        ultimo = self.ultimo
        return ultimo.version if ultimo is not None else None

    @property
    def categoria_edad_vigente(self) -> CategoriaDeEdad | None:
        """Con qué categoría de edad se emitió el último acto.

        Es lo que permite detectar que alguien cumplió 18 después de aceptar:
        `dominio/modelo/acceso.py` la compara con la categoría actual del perfil y
        deja el acceso pendiente de una nueva aceptación cuando difieren.
        """
        ultimo = self.ultimo
        return ultimo.categoria_edad if ultimo is not None else None
