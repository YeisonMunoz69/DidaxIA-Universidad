"""
acceso.py — El acceso se CALCULA, y se calcula sin HTTP
=========================================================

La tabla de «Estados y acceso aprobados» de la Fase 3 · sesión 1, hecha función.
Siete estados calculados, ninguno editable: no existe una columna `acceso` que
alguien pueda poner en `habilitado`, y no puede existir sin cambiar este archivo.

Por qué vive en el dominio y no en una guarda de FastAPI
------------------------------------------------------------------
Porque la misma regla la necesitan sitios que no son una petición HTTP: la
pantalla de la sesión 5, el panel de la sesión 3, la cascada de la sesión 4 y las
pruebas. Escrita como dependencia de una ruta, cada uno habría acabado con su
propia versión — que es como el sistema llegó a tener `puede_participar()` en un
adaptador entrante y `consentimiento` en un `dict` de sesión, respondiendo a la
misma pregunta con criterios distintos.

El orden de las preguntas ES el contrato
-------------------------------------------------
1. **`MANTENIMIENTO`** si el almacén no responde. Va primero porque sin datos no
   se puede afirmar nada: `EQ-024` prohíbe explícitamente inventar el estado
   cuando PostgreSQL no está disponible, y «no lo sé» no puede parecerse a «no
   ha consentido».
2. **`ELIMINACION_SOLICITADA`** mientras dure el trámite de `EQ-022`.
3. **Bloqueos**: una revocación o un rechazo en cualquier dimensión bloquean, y
   lo hacen antes de mirar si el perfil está completo. Quien revocó no vuelve al
   onboarding: vuelve a una pantalla que le explica que revocó.
4. **`ONBOARDING_PENDIENTE`** si falta perfil, si falta la decisión, si la
   versión aceptada ya no es la que rige —o no rige ninguna— o si la persona
   cambió de categoría de edad desde que aceptó (`EQ-021`).
5. **`ESPERANDO_REPRESENTANTE`** para el menor al que le falta autorización
   aprobada o asentimiento otorgado.
6. **`HABILITADO`** sólo si nada de lo anterior se cumplió.

Un menor no se habilita ni por descuido
------------------------------------------------
`_menor_habilitado()` exige `APROBADO` **y** `OTORGADO`, y lo exige a partir de
la edad declarada — no de que el estado guardado diga que hacía falta. Si un
`EstadoVigente` llegara con `representante = no_requerido` para alguien de 15
años, el cálculo sigue pidiendo la autorización: un dato viejo no puede conceder
un acceso que la regla niega.

Y al revés, desde la corrección de la revisión: las dimensiones de menores dejan
de intervenir en cuanto la persona deja de serlo. Un asentimiento revocado a los
17 no bloquea a los 18; lo que sí ocurre a los 18 es que el consentimiento
otorgado como menor deja de estar al día y hay que volver a aceptarlo.

Lo que esta sesión deja preparado y no implementa
----------------------------------------------------------
`ELIMINACION_SOLICITADA` y `MANTENIMIENTO` son estados de pleno derecho aquí, y
sus dos entradas son parámetros —`eliminacion_solicitada` y
`almacen_disponible`— en vez de tablas. Es deliberado: el trámite de supresión es
la sesión 4 y la degradación visible es la sesión 3, así que ninguna de las dos
tiene todavía un consumidor que justifique una tabla. Cuando lo tengan, el
cálculo no cambia.


"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from dominio.modelo.consentimiento import EstadoConsentimiento
from dominio.modelo.identidad import CategoriaDeEdad, PerfilOnboarding
from dominio.modelo.menores import EstadoAsentimiento, EstadoRepresentante


class AccesoCalculado(StrEnum):
    """Los siete de la tabla aprobada. Ninguno se escribe: todos se derivan."""

    ONBOARDING_PENDIENTE = "onboarding_pendiente"
    ESPERANDO_REPRESENTANTE = "esperando_representante"
    HABILITADO = "habilitado"
    BLOQUEADO_POR_RECHAZO = "bloqueado_por_rechazo"
    BLOQUEADO_POR_REVOCACION = "bloqueado_por_revocacion"
    ELIMINACION_SOLICITADA = "eliminacion_solicitada"
    MANTENIMIENTO = "mantenimiento"


#: El acceso ordinario al Tutor sigue exigiendo el recorrido completo. La
#: excepción acotada por una rectificación de edad se conserva como un hecho
#: separado en ``EstadoVigente``: no convierte un rechazo cualquiera en acceso.
ACCESOS_CON_TUTOR: frozenset[AccesoCalculado] = frozenset({AccesoCalculado.HABILITADO})


@dataclass(frozen=True, slots=True)
class VersionesRequeridas:
    """Qué versión rige AHORA en cada dimensión, o `None` si no rige ninguna.

    Es el resultado de la consulta que `EQ-021` obliga a hacer y que la primera
    entrega no hacía: un consentimiento otorgado sobre una versión retirada no es
    un consentimiento vigente, y presentarlo como tal habilitaría el tutor con
    una autorización que ya nadie firmaría.

    `None` no es un detalle: si el equipo todavía no ha publicado la versión de
    una dimensión —que es el estado real de este árbol— no hay nada que aceptar,
    y el acceso no puede presentarse como habilitado.
    """

    titular: str | None = None
    asentimiento: str | None = None
    representante: str | None = None


@dataclass(frozen=True, slots=True)
class EstadoVigente:
    """El resultado determinista de leer los eventos de una persona.

    Es lo que un repositorio devuelve y lo que `calcular_acceso()` consume. Los
    valores por defecto son los conservadores —`PENDIENTE`, `NO_REQUERIDO`, sin
    perfil— porque el encargo pide que **ninguna construcción predeterminada
    produzca autorización**: `EstadoVigente(sujeto_google="x")` da
    `ONBOARDING_PENDIENTE`, nunca `HABILITADO`.

    `perfil` es `None` cuando la persona existe pero no ha declarado nada. Que la
    persona **no exista** no se representa aquí: lo dice el repositorio
    devolviendo `None` en lugar de un `EstadoVigente`, que es la distinción entre
    «no hay registro» y «hay registro y está pendiente» que
    `dominio/puertos/almacen.py` describe.
    """

    sujeto_google: str
    perfil: PerfilOnboarding | None = None
    consentimiento: EstadoConsentimiento = EstadoConsentimiento.PENDIENTE
    version_consentimiento: str | None = None
    #: El identificador del último evento de consentimiento, para que cada turno
    #: pueda referenciarlo (`EQ-016`, hito B3). `None` cuando no hay ninguno.
    #:
    #: Es el `id` que asignó la base, no un dato derivado: quien lo escriba en
    #: `registro_turno` necesita una clave foránea real.
    evento_consentimiento: int | None = None
    #: Con qué categoría de edad se emitió el último consentimiento. La deriva la
    #: base desde `persona`; aquí sólo se compara con la actual.
    categoria_edad_consentimiento: CategoriaDeEdad | None = None
    representante: EstadoRepresentante = EstadoRepresentante.NO_REQUERIDO
    #: Motivo de la última revisión rechazada del documento del representante.
    #: Se expone sólo al propio estudiante para que sepa qué corregir.
    motivo_representante: str = ""
    asentimiento: EstadoAsentimiento = EstadoAsentimiento.NO_REQUERIDO
    version_asentimiento: str | None = None
    #: Lo que rige hoy en cada dimensión. Por defecto, nada — y por defecto, por
    #: tanto, nadie queda habilitado.
    requeridas: VersionesRequeridas = field(default_factory=VersionesRequeridas)
    limite_representante: datetime | None = None
    #: La entrada del trámite de `EQ-022`. La sesión 4 la conectará a su almacén;
    #: aquí es un parámetro para que el estado exista sin inventar una tabla.
    eliminacion_solicitada: bool = False
    #: Una rectificación que cambió el régimen de edad puede exigir decidir de
    #: nuevo sin retirar la ayuda académica. Es un permiso acotado a Tutor: no
    #: equivale a consentimiento ni habilita perfiles, KPI o exportaciones.
    tutoria_academica_sin_investigacion: bool = False

    @property
    def es_menor(self) -> bool:
        """Sólo con una edad declarada por debajo de 18. Sin perfil, `False` — y
        sin perfil el acceso ya es `ONBOARDING_PENDIENTE` por otra razón."""
        return self.perfil is not None and self.perfil.es_menor

    @property
    def perfil_completo(self) -> bool:
        return self.perfil is not None and self.perfil.completo

    @property
    def consentimiento_al_dia(self) -> bool:
        """Si el consentimiento otorgado sigue autorizando lo que hoy se pide.

        Tres condiciones, y las tres son de `EQ-021`:

        1. está **otorgado** —ni pendiente, ni rechazado, ni revocado—;
        2. es de la **versión que rige ahora**. Si el equipo publicó una versión
           nueva, o si no hay ninguna vigente, lo aceptado antes no vale para lo
           que hoy se hace;
        3. se emitió con la **misma categoría de edad** que la persona tiene hoy.
           Cumplir 18 cambia el régimen entero y `EQ-021` obliga a volver a pedir
           autorización.

        Cuando falla cualquiera de las tres, el acceso queda pendiente de una
        nueva aceptación — no bloqueado: la persona no hizo nada malo, hay algo
        nuevo que aceptar.
        """
        return (
            self.consentimiento is EstadoConsentimiento.OTORGADO
            and self.requeridas.titular is not None
            and self.version_consentimiento == self.requeridas.titular
            and self.perfil is not None
            and self.categoria_edad_consentimiento is not None
            and self.categoria_edad_consentimiento is self.perfil.categoria_de_edad
        )

    @property
    def asentimiento_al_dia(self) -> bool:
        """Mismo criterio de versión para el asentimiento del menor.

        Sin categoría de edad: quien deja de ser menor deja de necesitarlo, y eso
        lo resuelve `requerido` en la derivación, no una comparación aquí.
        """
        return (
            self.asentimiento is EstadoAsentimiento.OTORGADO
            and self.requeridas.asentimiento is not None
            and self.version_asentimiento == self.requeridas.asentimiento
        )


def _hay_revocacion(estado: EstadoVigente) -> bool:
    """Las dimensiones de menores sólo intervienen si la persona ES menor.

    Es la corrección que pidió la revisión: una revocación de asentimiento de
    cuando alguien tenía 17 años no puede seguir bloqueándole a los 18, porque a
    esa edad nadie le pide asentimiento. La fila se conserva —es historia— y deja
    de intervenir.
    """
    if estado.consentimiento is EstadoConsentimiento.REVOCADO:
        return True
    return estado.es_menor and estado.asentimiento is EstadoAsentimiento.REVOCADO


def _hay_rechazo(estado: EstadoVigente) -> bool:
    """Mismo criterio que la revocación: las dos dimensiones de menores sólo
    cuentan mientras la persona lo sea."""
    if estado.consentimiento is EstadoConsentimiento.RECHAZADO:
        return True
    if not estado.es_menor:
        return False
    return (
        estado.asentimiento is EstadoAsentimiento.RECHAZADO
        or estado.representante is EstadoRepresentante.RECHAZADO
    )


def _menor_habilitado(estado: EstadoVigente) -> bool:
    """`EQ-016`: autorización aprobada **y** asentimiento otorgado. Las dos.

    Se comprueban las dos dimensiones por separado y no un estado combinado
    porque el encargo lo prohíbe: `pendiente_representante` no puede sustituir a
    tres dimensiones independientes.

    `estado.representante` ya viene derivado contra la versión requerida del
    documento del representante —ver `estado_representante()`—, así que una
    evidencia aprobada de una versión anterior no llega aquí como `APROBADO`.
    `asentimiento_al_dia` hace lo propio con la versión del asentimiento.
    """
    return estado.representante is EstadoRepresentante.APROBADO and estado.asentimiento_al_dia


def calcular_acceso(
    estado: EstadoVigente, *, almacen_disponible: bool = True
) -> AccesoCalculado:
    """El estado calculado de la tabla aprobada. Ver el orden en la cabecera."""
    if not almacen_disponible:
        return AccesoCalculado.MANTENIMIENTO
    if estado.eliminacion_solicitada:
        return AccesoCalculado.ELIMINACION_SOLICITADA
    if _hay_revocacion(estado):
        return AccesoCalculado.BLOQUEADO_POR_REVOCACION
    if _hay_rechazo(estado):
        return AccesoCalculado.BLOQUEADO_POR_RECHAZO
    if not estado.perfil_completo:
        return AccesoCalculado.ONBOARDING_PENDIENTE
    # Cubre las tres formas de no estar al día: sin otorgar, sobre una versión
    # que ya no rige —o sin ninguna vigente— y con una categoría de edad que
    # cambió. Las tres se resuelven aceptando de nuevo, no desbloqueando.
    if not estado.consentimiento_al_dia:
        return AccesoCalculado.ONBOARDING_PENDIENTE
    if estado.es_menor and not _menor_habilitado(estado):
        return AccesoCalculado.ESPERANDO_REPRESENTANTE
    return AccesoCalculado.HABILITADO


def permite_tutor(acceso: AccesoCalculado) -> bool:
    """Si el tutor se puede usar. Un solo sitio donde se responde."""
    return acceso in ACCESOS_CON_TUTOR


def permite_tutoria_academica(estado: EstadoVigente) -> bool:
    """La rectificación conserva tutoría sólo con registro y clase completos.

    La bandera histórica no sustituye matrícula, protección de menores ni
    el cierre de una solicitud de supresión. Tampoco habilita investigación.
    """
    return (
        estado.tutoria_academica_sin_investigacion
        and estado.perfil_completo
        and not estado.eliminacion_solicitada
        and (not estado.es_menor or _menor_habilitado(estado))
    )


def permite_escritura_longitudinal(acceso: AccesoCalculado) -> bool:
    """`EQ-016`: el consentimiento gobierna qué perfil longitudinal se actualiza.

    La tutoría excepcional de una rectificación tampoco habilita esta escritura;
    este método recibe el acceso investigativo ordinario, no el modo académico.
    """
    return acceso is AccesoCalculado.HABILITADO
