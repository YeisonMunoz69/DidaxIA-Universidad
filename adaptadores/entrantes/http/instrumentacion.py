"""
instrumentacion.py — Los puntos canónicos del backend, y su red de seguridad
=============================================================================

Cinco hechos que este servidor **puede demostrar** sin depender del navegador:
que se envió un turno, que se respondió y con qué versiones, que se derivó a
supervisión, que un docente decidió sobre un elemento y que se actualizó el
contexto curricular de una clase.

No hay más, y la ausencia es la decisión. La autocorrección, la apertura del
panel de fuentes o la exportación de una gráfica ocurren en el navegador: el
servidor no las ve, y fabricar el evento aquí sería inventar una observación.
Para esos hechos existe el contrato, la API de `rutas/telemetria.py` y el emisor
mínimo del frontend; cada superficie declara únicamente lo que sí observó.

⚠️ EL FALLO SE ABSORBE, Y AQUÍ ESTÁ EL PORQUÉ
--------------------------------------------------------
`anotar()` captura el fallo de almacenamiento **y** el evento mal formado, y
sigue. La alternativa era dejar que subieran, y entonces un PostgreSQL saturado
—o un identificador con una forma inesperada— haría perder al estudiante el
turno que acaba de escribir. Ese intercambio está al revés: la medición existe
para observar el producto, no para condicionarlo.

Lo que **no** se hace es fingir que se midió. El evento no se guarda, el hueco
queda, y la superficie de calidad de datos lo ve como ausencia. Por eso las
definiciones del catálogo que se apoyan en `evento_telemetria` declaran que
pueden subestimar: un evento no se inventa, pero puede faltar.

⚠️ Esto **no** aplica a la auditoría. `auditoria_operacion` sí es atómica con lo
que audita (`EQ-023`), y esa escritura vive en `kpi_db.py` dentro de la misma
transacción que la lectura. Son dos cosas distintas y no comparten mecanismo:
la auditoría autoriza, la telemetría observa.

Por qué las claves de idempotencia se derivan y no se sortean
----------------------------------------------------------------------
Porque un reintento tiene que producir la misma clave. Un turno reenviado por un
cliente que no recibió respuesta vuelve con el mismo `turno`, así que
`_clave("turno.enviado", turno)` coincide y el `ON CONFLICT` del adaptador lo
convierte en un no-op. Con una clave aleatoria, cada reintento sería un envío
más y la actividad medida crecería con la mala conectividad.

Se resume con SHA-256 y no se concatenan los valores en claro por dos motivos:
la clave cabe siempre en el patrón que la migración 23 exige —un identificador
con caracteres inesperados no la rompe— y no expone en una columna indexada la
composición exacta de los identificadores de origen.


"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from dominio.modelo.contexto_de_uso import ContextoDeUso
from dominio.modelo.telemetria import EventoInvalido, EventoTelemetria, TipoDeEvento
from dominio.puertos.almacen import ErrorDeAlmacen

if TYPE_CHECKING:  # pragma: no cover
    from dominio.puertos.telemetria import PuertoTelemetria


def _clave(tipo: TipoDeEvento, *partes: str) -> str:
    """Una clave estable y opaca para este hecho.

    El prefijo legible sirve para depurar mirando la tabla; el resumen es lo
    que garantiza forma y longitud. Ver la cabecera sobre por qué no se
    concatenan los valores en claro.
    """
    resumen = hashlib.sha256("\x1f".join(partes).encode("utf-8")).hexdigest()[:32]
    return f"{tipo.value.replace('.', '-')}:{resumen}"


@dataclass(frozen=True, slots=True)
class SelloDelTurno:
    """A qué turno, conversación, clase y persona pertenece un hecho.

    Va junto porque los cinco eventos del backend lo necesitan entero y
    pasarlo suelto habría dejado cinco firmas de seis parámetros del mismo
    tipo, que es como se intercambian dos sin que nada falle.
    """

    sujeto: str
    conversacion: str
    turno: str
    contexto_de_uso: ContextoDeUso = ContextoDeUso.APRENDIZAJE_ESTUDIANTE
    clase: str | None = None


@dataclass(frozen=True, slots=True)
class ResultadoDelTurno:
    """Lo observable de una respuesta ya emitida.

    `version_modelo` es **la que respondió**, leída de la traza del filtro de
    generación, y no la que la configuración pidió: son distintas en cuanto un
    proveedor sirve un alias o hace una sustitución, y el encargo pide
    justamente «versión de modelo realmente respondida».
    """

    nivel: str = ""
    procedencia: str = ""
    degradado: bool = False
    version_modelo: str = ""
    version_corpus: str = ""


class Instrumentador:
    """Los puntos canónicos del backend, con el fallo absorbido.

    Recibe el puerto y, opcionalmente, de dónde sale la versión del corpus. Sin
    ninguno de los dos sigue siendo utilizable: `anotar()` no hace nada y el
    sistema funciona exactamente como antes de esta entrega.
    """

    def __init__(
        self,
        telemetria: PuertoTelemetria | None = None,
        version_del_corpus: object | None = None,
    ) -> None:
        self._telemetria = telemetria
        self._version_del_corpus = version_del_corpus

    # ── La red de seguridad ──────────────────────────────────────────────────

    def anotar(self, evento: EventoTelemetria) -> bool:
        """Persiste el hecho y devuelve si era nuevo. Nunca levanta.

        `EventoInvalido` se captura junto al fallo de almacén y no por
        descuido: la validación protege la tabla, pero un turno del estudiante
        no se pierde porque un identificador tenga una forma que el patrón no
        esperaba. El evento no entra, y eso es todo lo que ocurre.
        """
        if self._telemetria is None:
            return False
        try:
            return self._telemetria.registrar(evento)
        except (ErrorDeAlmacen, EventoInvalido, OSError):
            return False

    def version_del_corpus(self) -> str:
        """La huella del corpus indexado, o cadena vacía si no se puede leer."""
        if self._version_del_corpus is None:
            return ""
        try:
            return str(self._version_del_corpus.actual() or "")
        except (ErrorDeAlmacen, OSError):
            return ""

    # ── Los cinco hechos ─────────────────────────────────────────────────────

    def turno_enviado(
        self, sello: SelloDelTurno, notacion: str = "", ocurrido_en: datetime | None = None
    ) -> bool:
        """El envío. `ocurrido_en` se recibe porque el instante real es anterior.

        El identificador del turno lo genera el adaptador dentro de `manejar()`,
        así que este evento sólo se puede escribir cuando el turno terminó. Si
        además tomara la hora de entonces, el envío quedaría fechado al acabar
        la respuesta y el intervalo entre sesiones mediría de más. La ruta
        captura el instante antes de llamar a la cadena y lo pasa aquí.
        """
        metadatos = {"notacion": notacion} if notacion in ("sen", "sin") else {}
        return self._anotar_del_turno(
            TipoDeEvento.TURNO_ENVIADO, sello, metadatos, ocurrido_en=ocurrido_en
        )

    def turno_respondido(self, sello: SelloDelTurno, resultado: ResultadoDelTurno) -> bool:
        metadatos = {
            "nivel": resultado.nivel,
            "procedencia": resultado.procedencia,
            "degradado": resultado.degradado,
        }
        # Un nivel o una procedencia que el vocabulario no reconozca se retiran
        # en vez de tumbar el evento entero: el resto del hecho sigue valiendo,
        # y el catálogo ya distingue «no consta» de un valor.
        if metadatos["nivel"] not in ("sondeo", "regla", "desarrollo"):
            metadatos.pop("nivel")
        if metadatos["procedencia"] not in ("corpus", "sin-fuente", "mixta", ""):
            metadatos.pop("procedencia")
        return self._anotar_del_turno(
            TipoDeEvento.TURNO_RESPONDIDO,
            sello,
            metadatos,
            versiones=(resultado.version_modelo, resultado.version_corpus),
        )

    def supervision_derivada(
        self, sello: SelloDelTurno, item: str, tipo_de_item: str, urgencia: str = ""
    ) -> bool:
        metadatos: dict = {"tipo_de_item": tipo_de_item}
        if urgencia:
            metadatos["urgencia"] = urgencia
        return self._anotar(
            TipoDeEvento.SUPERVISION_DERIVADA,
            _clave(TipoDeEvento.SUPERVISION_DERIVADA, item),
            sello=sello,
            metadatos=metadatos,
        )

    def supervision_decidida(
        self, sello: SelloDelTurno, item: str, decision: str
    ) -> bool:
        """La decisión del docente. Un elemento se decide una vez.

        `cola_revision` no admite volver de aprobado/editado/rechazado a
        pendiente, así que la clave por elemento es suficiente y correcta: un
        segundo evento sobre el mismo elemento sería un reintento, no una
        decisión nueva.
        """
        return self._anotar(
            TipoDeEvento.SUPERVISION_DECIDIDA,
            _clave(TipoDeEvento.SUPERVISION_DECIDIDA, item),
            sello=sello,
            metadatos={"decision": decision, "item": item},
        )

    def curricular_actualizado(
        self, sujeto: str, clase: str, notacion: str, tiene_unidad: bool
    ) -> bool:
        """Cada guardado es un hecho distinto, y su marca temporal lo separa.

        La clave incluye el instante porque un docente puede actualizar el
        contexto varias veces: con una clave sólo por clase, la segunda
        actualización se descartaría como duplicado y el indicador de frescura
        curricular se quedaría anclado a la primera.
        """
        ahora = datetime.now(UTC)
        evento = self._construir(
            TipoDeEvento.CURRICULAR_ACTUALIZADO,
            _clave(TipoDeEvento.CURRICULAR_ACTUALIZADO, clase, ahora.isoformat()),
            identificador_sujeto=sujeto,
            ocurrido_en=ahora,
            clase=clase,
            contexto_de_uso=ContextoDeUso.CONSULTA_PROFESIONAL,
            metadatos={"notacion": notacion, "tiene_unidad": tiene_unidad},
        )
        return self.anotar(evento) if evento is not None else False

    # ── Construcción ─────────────────────────────────────────────────────────

    def _anotar_del_turno(
        self,
        tipo: TipoDeEvento,
        sello: SelloDelTurno,
        metadatos: dict,
        ocurrido_en: datetime | None = None,
        versiones: tuple[str, str] = ("", ""),
    ) -> bool:
        return self._anotar(
            tipo,
            _clave(tipo, sello.turno),
            sello=sello,
            metadatos=metadatos,
            ocurrido_en=ocurrido_en,
            versiones=versiones,
        )

    def _anotar(
        self,
        tipo: TipoDeEvento,
        clave: str,
        *,
        sello: SelloDelTurno,
        metadatos: dict,
        ocurrido_en: datetime | None = None,
        versiones: tuple[str, str] = ("", ""),
    ) -> bool:
        """`versiones` es `(modelo, corpus)` y viaja junta a propósito: son dos
        cadenas del mismo tipo y dos parámetros sueltos se intercambian sin que
        nada falle hasta que alguien lea un informe."""
        version_modelo, version_corpus = versiones
        evento = self._construir(
            tipo,
            clave,
            identificador_sujeto=sello.sujeto,
            ocurrido_en=ocurrido_en or datetime.now(UTC),
            clase=sello.clase,
            metadatos=metadatos,
            conversacion=sello.conversacion,
            turno=sello.turno,
            contexto_de_uso=sello.contexto_de_uso,
            version_modelo=version_modelo,
            version_corpus=version_corpus,
        )
        return self.anotar(evento) if evento is not None else False

    @staticmethod
    def _construir(
        tipo: TipoDeEvento, clave: str, **campos: object
    ) -> EventoTelemetria | None:
        """El evento, o `None` si no se pudo construir.

        Construir también puede fallar —una referencia con forma inesperada— y
        ese fallo se absorbe igual que el de escritura, por el mismo motivo.
        """
        try:
            return EventoTelemetria(clave_idempotencia=clave, tipo=tipo, **campos)  # type: ignore[arg-type]
        except (EventoInvalido, TypeError):
            # ⚠️ `TypeError` está aquí por un fallo real, encontrado por
            # `pruebas/unidad/test_instrumentacion.py` antes de integrar: este
            # método construía el evento con `sujeto=` cuando el modelo lo llama
            # `identificador_sujeto=`. `EventoInvalido` no lo cubría, y el
            # `TypeError` habría subido hasta la ruta del turno — es decir, la
            # red de seguridad de este módulo tenía un agujero justo del tamaño
            # de un error de escritura en su propia llamada.
            return None


#: Un instrumentador que no instrumenta. Es lo que reciben las rutas cuando la
#: composición no cableó telemetría, para que ninguna tenga que comprobar `None`
#: antes de cada llamada ni repetir la misma guarda.
SIN_INSTRUMENTAR = Instrumentador()
