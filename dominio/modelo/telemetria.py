"""
telemetria.py — El vocabulario cerrado de eventos y su validación
==================================================================

Un evento de telemetría es un **hecho histórico**: ocurrió, se registra una vez
y no se corrige. Este módulo define qué hechos existen, qué puede acompañarlos
y quién puede declararlos.

Las cuatro validaciones que el encargo pide, y por qué cada una
-------------------------------------------------------------------------
1. **Vocabulario.** `TipoDeEvento` es cerrado. Un tipo libre convierte la
   telemetría en un cajón: dos emisores escriben `grafica_export` y
   `graficaExportada` y el KPI cuenta la mitad.
2. **Esquema.** Cada tipo declara qué metadatos admite y con qué valores. Lo
   que no está declarado se rechaza; no se guarda «por si acaso».
3. **Propiedad.** El origen lo decide el tipo, no quien envía. Un evento de
   `backend` no entra por la API de la interfaz aunque alguien lo intente, y
   el sujeto y el contexto de uso los pone el servidor desde la sesión
   autenticada.
4. **Referencias.** Los identificadores tienen forma y tope de longitud. El
   adaptador comprueba además que la clase exista y sea del alcance de quien
   escribe; aquí se comprueba lo que se puede comprobar sin base.

Lo que un evento NO lleva, y es la regla más dura
--------------------------------------------------------
Ni texto de conversación, ni correo, ni nombre. La telemetría se conserva para
agregar, y agregar no necesita saber qué escribió nadie: para eso ya está
`historial_turno`, que es la fuente canónica y tiene su propia cascada de
supresión. `_exigir_metadato()` acota cada valor a 64 caracteres y rechaza `@`
justamente para que un correo no quepa ni por descuido.

Por qué la clave de idempotencia es del emisor
-------------------------------------------------------
Porque el reintento también es suyo. Un cliente que no recibe la respuesta
vuelve a enviar el mismo evento; si la clave la generara el servidor, el
segundo intento crearía una fila nueva y la métrica contaría dos aperturas de
fuentes donde hubo una. Con la clave del emisor, el `ON CONFLICT DO NOTHING`
del adaptador convierte el reintento en un no-op observable.


"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Final

from dominio.modelo.contexto_de_uso import ContextoDeUso


class EventoInvalido(ValueError):
    """El evento no cumple el contrato. No se guarda y se dice por qué."""


class ConflictoDeIdempotencia(EventoInvalido):
    """La clave ya identifica otro hecho; por tanto no es un reintento."""


class OrigenDeEvento(StrEnum):
    """Quién declara el hecho.

    `BACKEND` lo emite este servidor desde un punto canónico que ya existe.
    `INTERFAZ` llega por API autenticada porque el hecho sólo ocurre en el
    navegador —abrir un panel, copiar un texto— y el servidor no puede verlo.
    """

    BACKEND = "backend"
    INTERFAZ = "interfaz"


class TipoDeEvento(StrEnum):
    """El vocabulario cerrado. Añadir uno es cambiar la migración y el catálogo."""

    #: El estudiante envió un turno. Punto canónico: `rutas/turno.py`.
    TURNO_ENVIADO = "turno.enviado"
    #: El sistema respondió, con la versión de corpus y de modelo que usó.
    TURNO_RESPONDIDO = "turno.respondido"
    #: El turno entró en la cola de revisión docente.
    SUPERVISION_DERIVADA = "supervision.derivada"
    #: El docente aprobó, editó o rechazó un elemento de la cola.
    SUPERVISION_DECIDIDA = "supervision.decidida"
    #: Un docente guardó el contexto curricular de una clase suya.
    CURRICULAR_ACTUALIZADO = "curricular.actualizado"

    #: A partir de aquí, hechos del navegador, emitidos por el cliente web.
    FUENTES_ABIERTAS = "fuentes.abiertas"
    RESPUESTA_COPIADA = "respuesta.copiada"
    GRAFICA_GENERADA = "grafica.generada"
    GRAFICA_ABIERTA = "grafica.abierta"
    GRAFICA_INTERACCION = "grafica.interaccion"
    GRAFICA_RANGO_CAMBIADO = "grafica.rango_cambiado"
    GRAFICA_EXPORTADA = "grafica.exportada"
    SUPERVISION_ABIERTA = "supervision.abierta"
    INFORME_GENERADO = "informe.generado"
    INFORME_DESCARGADO = "informe.descargado"
    #: La interfaz detectó una autocorrección candidata del estudiante.
    AUTOCORRECCION_DETECTADA = "autocorreccion.detectada"
    #: El estudiante confirmó explícitamente que corrigió su procedimiento.
    AUTOCORRECCION_CONFIRMADA = "autocorreccion.confirmada"


#: Qué origen corresponde a cada tipo. No es una convención: `validar()` la
#: impone, así que la API de la interfaz no puede fabricar un hecho del backend.
ORIGEN_DE: Final[dict[TipoDeEvento, OrigenDeEvento]] = {
    TipoDeEvento.TURNO_ENVIADO: OrigenDeEvento.BACKEND,
    TipoDeEvento.TURNO_RESPONDIDO: OrigenDeEvento.BACKEND,
    TipoDeEvento.SUPERVISION_DERIVADA: OrigenDeEvento.BACKEND,
    TipoDeEvento.SUPERVISION_DECIDIDA: OrigenDeEvento.BACKEND,
    TipoDeEvento.CURRICULAR_ACTUALIZADO: OrigenDeEvento.BACKEND,
    TipoDeEvento.FUENTES_ABIERTAS: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.RESPUESTA_COPIADA: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.GRAFICA_GENERADA: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.GRAFICA_ABIERTA: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.GRAFICA_INTERACCION: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.GRAFICA_RANGO_CAMBIADO: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.GRAFICA_EXPORTADA: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.SUPERVISION_ABIERTA: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.INFORME_GENERADO: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.INFORME_DESCARGADO: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.AUTOCORRECCION_DETECTADA: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.AUTOCORRECCION_CONFIRMADA: OrigenDeEvento.INTERFAZ,
}

#: Los tipos que la API autenticada de eventos admite. Es exactamente el
#: conjunto de origen `INTERFAZ`, derivado y no repetido a mano.
TIPOS_DE_INTERFAZ: Final[frozenset[TipoDeEvento]] = frozenset(
    tipo for tipo, origen in ORIGEN_DE.items() if origen is OrigenDeEvento.INTERFAZ
)

#: Metadatos admitidos por tipo, con sus valores cerrados cuando los tiene.
#: Una clave que no aparezca aquí se rechaza: es la mitad «esquema» de la
#: validación, y lo que impide que la telemetría acabe siendo un cajón.
#:
#: `None` como valor significa «escalar corto, sin lista cerrada» —un
#: identificador de gráfica, por ejemplo—.
METADATOS_ADMITIDOS: Final[dict[TipoDeEvento, dict[str, frozenset[str] | None]]] = {
    TipoDeEvento.TURNO_ENVIADO: {"notacion": frozenset({"sen", "sin"})},
    TipoDeEvento.TURNO_RESPONDIDO: {
        "nivel": frozenset({"sondeo", "regla", "desarrollo"}),
        "procedencia": frozenset({"corpus", "sin-fuente", "mixta", ""}),
        "degradado": None,
    },
    TipoDeEvento.SUPERVISION_DERIVADA: {
        "tipo_de_item": frozenset({"respuesta", "sin-fuente", "degradado"}),
        "urgencia": None,
    },
    TipoDeEvento.SUPERVISION_DECIDIDA: {
        "decision": frozenset({"aprobado", "editado", "rechazado"}),
        "item": None,
    },
    TipoDeEvento.CURRICULAR_ACTUALIZADO: {
        "notacion": frozenset({"sen", "sin"}),
        "tiene_unidad": None,
    },
    TipoDeEvento.FUENTES_ABIERTAS: {"materiales": None},
    TipoDeEvento.RESPUESTA_COPIADA: {"alcance": frozenset({"bloque", "respuesta"})},
    TipoDeEvento.GRAFICA_GENERADA: {"grafica": None},
    TipoDeEvento.GRAFICA_ABIERTA: {"grafica": None, "vista": frozenset({"normal", "ampliada"})},
    TipoDeEvento.GRAFICA_INTERACCION: {
        "grafica": None,
        "gesto": frozenset({"desplazar", "acercar", "alejar", "puntero"}),
    },
    TipoDeEvento.GRAFICA_RANGO_CAMBIADO: {
        "grafica": None,
        "eje": frozenset({"x", "y", "ambos"}),
    },
    TipoDeEvento.GRAFICA_EXPORTADA: {
        "grafica": None,
        # Los cinco formatos que ofrece `Grafica.svelte`. CSV no se anuncia:
        # la interfaz no exporta una serie tabular y aceptarlo aquí fingiría un
        # productor que no existe.
        "formato": frozenset({"png", "jpg", "svg", "html", "pdf"}),
        "tema": frozenset({"claro", "oscuro"}),
    },
    TipoDeEvento.SUPERVISION_ABIERTA: {"item": None},
    TipoDeEvento.INFORME_GENERADO: {
        "informe": frozenset({"indicador", "completo"}),
        "codigo": None,
    },
    TipoDeEvento.INFORME_DESCARGADO: {
        "informe": frozenset({"indicador", "completo"}),
        "formato": frozenset({"pdf"}),
    },
    TipoDeEvento.AUTOCORRECCION_DETECTADA: {},
    TipoDeEvento.AUTOCORRECCION_CONFIRMADA: {},
}

#: Tope de longitud de un identificador. Generoso para los que existen —los
#: turnos y las sesiones son UUID— y muy corto para un texto de conversación.
TOPE_IDENTIFICADOR: Final = 128

#: Tope de un valor de metadato. Un correo institucional cabe en 64, así que
#: además se rechaza `@`: las dos reglas juntas son las que impiden que un dato
#: personal entre por aquí.
TOPE_METADATO: Final = 64

#: Cuántos metadatos admite un evento. El esquema ya limita las claves; esto
#: acota además el tamaño total de la fila.
TOPE_METADATOS = 8

#: La clave de idempotencia. Opaca, imprimible y acotada: no se interpreta, sólo
#: se compara. El patrón excluye espacios para que no quepa una frase.
PATRON_CLAVE = re.compile(r"^[A-Za-z0-9:._~-]{8,160}$")

#: Un identificador de clase, conversación, turno o concepto.
PATRON_REFERENCIA = re.compile(r"^[A-Za-z0-9:._~-]{1,128}$")


def _exigir_referencia(valor: str | None, campo: str) -> str | None:
    """Una referencia con forma, o `None`. Nunca una cadena en blanco.

    Se normaliza `""` a `None` a propósito: una cadena vacía en una columna que
    admite nulo produce dos representaciones de «no consta», y los agregados
    tendrían que acordarse de las dos.
    """
    if valor is None:
        return None
    limpio = valor.strip()
    if not limpio:
        return None
    if not PATRON_REFERENCIA.fullmatch(limpio):
        raise EventoInvalido(f"{campo} no tiene la forma de un identificador")
    return limpio


def _exigir_metadato(tipo: TipoDeEvento, clave: str, valor: object) -> None:
    """Que este metadato esté declarado para este tipo y valga lo que puede valer."""
    admitidos = METADATOS_ADMITIDOS.get(tipo, {})
    if clave not in admitidos:
        raise EventoInvalido(
            f"«{clave}» no es un metadato de «{tipo.value}»: el esquema no "
            f"admite metadatos arbitrarios"
        )
    cerrados = admitidos[clave]
    if cerrados is not None:
        if not isinstance(valor, str) or valor not in cerrados:
            raise EventoInvalido(f"«{valor}» no es un valor admitido de «{clave}»")
        return
    if isinstance(valor, float) and not math.isfinite(valor):
        raise EventoInvalido(f"«{clave}» tiene que ser un número finito")
    if isinstance(valor, bool | int | float):
        return
    if not isinstance(valor, str):
        raise EventoInvalido(f"«{clave}» tiene que ser un escalar, no {type(valor).__name__}")
    if len(valor) > TOPE_METADATO or "@" in valor:
        raise EventoInvalido(
            f"«{clave}» excede lo que un metadato puede llevar: la telemetría "
            f"no transporta texto libre ni datos de contacto"
        )


@dataclass(frozen=True, slots=True)
class EventoTelemetria:
    """Un hecho histórico, validado en el constructor.

    Se valida al construir y no al guardar porque el mismo tipo viaja por dos
    caminos —el punto canónico del backend y la API de la interfaz— y una
    validación que viviera en el adaptador dejaría uno de los dos sin cubrir.
    """

    clave_idempotencia: str
    tipo: TipoDeEvento
    ocurrido_en: datetime
    identificador_sujeto: str
    contexto_de_uso: ContextoDeUso = ContextoDeUso.APRENDIZAJE_ESTUDIANTE
    clase: str | None = None
    conversacion: str | None = None
    turno: str | None = None
    concepto: str | None = None
    version_corpus: str = ""
    version_modelo: str = ""
    metadatos: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not PATRON_CLAVE.fullmatch(self.clave_idempotencia or ""):
            raise EventoInvalido(
                "la clave de idempotencia tiene que ser opaca, imprimible y de "
                "entre 8 y 160 caracteres"
            )
        if self.ocurrido_en.tzinfo is None:
            raise EventoInvalido("un evento sin zona horaria no es un instante inequívoco")
        sujeto = (self.identificador_sujeto or "").strip()
        if not sujeto or len(sujeto) > TOPE_IDENTIFICADOR:
            raise EventoInvalido("el evento no declara un sujeto utilizable")
        object.__setattr__(self, "identificador_sujeto", sujeto)
        for campo in ("clase", "conversacion", "turno", "concepto"):
            object.__setattr__(self, campo, _exigir_referencia(getattr(self, campo), campo))
        for campo in ("version_corpus", "version_modelo"):
            valor = (getattr(self, campo) or "").strip()
            if len(valor) > TOPE_METADATO:
                raise EventoInvalido(f"{campo} excede {TOPE_METADATO} caracteres")
            object.__setattr__(self, campo, valor)
        if len(self.metadatos) > TOPE_METADATOS:
            raise EventoInvalido(f"un evento no lleva más de {TOPE_METADATOS} metadatos")
        for clave, valor in self.metadatos.items():
            _exigir_metadato(self.tipo, clave, valor)

    @property
    def origen(self) -> OrigenDeEvento:
        """Quién puede declarar este hecho. Lo decide el tipo, no el emisor."""
        return ORIGEN_DE[self.tipo]

    @property
    def alimenta_kpi(self) -> bool:
        """`EQ-031` · el uso profesional se registra y no se agrega.

        Se conserva la fila —es operación real y sirve para diagnóstico— y se
        marca su contexto, que es lo que permite excluirla de todo KPI sin
        volver a preguntar por el rol de nadie, que un rol revocable no podría
        contestar hacia atrás.
        """
        return self.contexto_de_uso is ContextoDeUso.APRENDIZAJE_ESTUDIANTE


def exigir_tipo_de_interfaz(nombre: str) -> TipoDeEvento:
    """El tipo que la API de eventos admite, o un rechazo con motivo.

    Existe aquí y no en la ruta porque es la mitad «propiedad» de la
    validación: sin esto, un cliente podría declarar `turno.respondido` con la
    versión de modelo que quisiera y envenenar un indicador institucional.
    """
    try:
        tipo = TipoDeEvento(nombre)
    except ValueError:
        raise EventoInvalido(f"«{nombre}» no es un evento del vocabulario") from None
    if tipo not in TIPOS_DE_INTERFAZ:
        raise EventoInvalido(
            f"«{nombre}» lo declara el servidor desde su punto canónico y no "
            f"se acepta desde la interfaz"
        )
    return tipo
