from __future__ import annotations

from dataclasses import dataclass, field, replace

from dominio.arbitraje.divulgacion import Señales
from dominio.diagnostico.clasificador import Diagnostico, RespuestaAlItem
from dominio.modelo.contexto_de_uso import ContextoDeUso
from dominio.modelo.estudiante import PerfilEstudiante
from dominio.modelo.matematica import InformeVerificacion, Precomputo
from dominio.modelo.respuesta import RespuestaGenerada
from dominio.pedagogia.conversacion import EstadoDeConversacion
from dominio.pedagogia.intenciones import Intencion
from dominio.pedagogia.politica import DecisionPedagogica
from dominio.pedagogia.sondeo import DesenlaceDelSondeo, EstadoDeSondeo, ItemOfrecido
from dominio.puertos.corpus import Recuperacion
from dominio.puertos.generacion import RespuestaDeGeneracion
from dominio.puertos.plantillas import ItemDosNiveles
from dominio.puertos.registro import BloqueRegistrado, CitaRegistrada


@dataclass(frozen=True)
class TrazaFiltro:

    filtro: str
    latencia_ms: float
    ruta: str = "caliente"
    metadatos: dict = field(default_factory=dict)

@dataclass(frozen=True)
class ContextoTurno:

    texto_estudiante: str
    identificador_sesion: str = ""

    identificador_turno: str = ""

    identificador_sujeto: str = ""

    consentimiento_evento: int | None = None

    momento: str = ""

    degradacion: str = ""

    bloques_emitidos: tuple[BloqueRegistrado, ...] = ()
    citas_emitidas: tuple[CitaRegistrada, ...] = ()

    conceptos_emitidos: tuple[str, ...] = ()

    nivel_emitido: str = ""
    procedencia_origen: str = ""
    procedencia_referencia: str = ""

    clase: str = ""

    contexto_de_uso: str = ContextoDeUso.APRENDIZAJE_ESTUDIANTE

    expresiones: tuple[str, ...] = ()

    expresion_previa: str = ""

    ejercicio_activo: dict[str, str] | None = None

    expresiones_heredadas: bool = False
    precomputo: Precomputo | None = None

    intencion: str = ""

    intencion_origen: str = ""

    intencion_detalle: Intencion | None = None

    es_limite: bool = False

    limite_expresion: str = ""

    limite_variable: str = "x"

    limite_destino: str = ""

    nodo_activo: str = ""

    procede_recuperar: bool = True

    recuperacion: Recuperacion | None = None

    prompt: str = ""

    generacion: RespuestaDeGeneracion | None = None
    respuesta: str = ""

    respuesta_generada: RespuestaGenerada | None = None
    informe: InformeVerificacion | None = None
    nivel_divulgacion: int = 1

    alcance_divulgacion: str = "ejercicio_activo"

    señales: Señales | None = None

    nivel_intervencion: int = 5

    perfil_previo: PerfilEstudiante | None = None

    perfil_actualizado: PerfilEstudiante | None = None

    respuesta_al_item: RespuestaAlItem | None = None

    sondeos_ofrecidos: tuple[ItemOfrecido, ...] = ()

    sondeos_contestados: tuple[str, ...] = ()

    estado_de_sondeo: EstadoDeSondeo | None = None

    desenlace_del_sondeo: DesenlaceDelSondeo = field(default_factory=DesenlaceDelSondeo)

    item_ofrecido: ItemDosNiveles | None = None

    notacion: str = ""

    historial_reciente: tuple[dict, ...] = ()

    contexto_conversacional: dict | None = None

    diagnostico: Diagnostico | None = None

    veredicto_del_intento: str = ""

    resultado_verificado: str = ""

    transformacion_verificada: str = ""

    paso_pendiente: dict | None = None
    paso_verificado: str = ""

    sin_adaptacion: bool = False

    estado_conversacion: EstadoDeConversacion | None = None

    estrategia_previa: str = ""

    decision_pedagogica: DecisionPedagogica | None = None

    retroalimentacion_del_intento: RespuestaGenerada | None = None
    necesidad_pedagogica: str = ""
    trazas: tuple[TrazaFiltro, ...] = ()

    continuidad: dict | None = None
    actos_conversacionales: tuple[dict, ...] = ()
    siguiente_objetivo: dict | None = None
    mensajes_generacion: tuple[dict, ...] = ()

    def con_traza(self, traza: TrazaFiltro, **cambios) -> ContextoTurno:
        return replace(self, trazas=self.trazas + (traza,), **cambios)

    @property
    def hay_item_ofrecible(self) -> bool:
        return self.item_ofrecido is not None

    @property
    def latencia_total_ms(self) -> float:
        return sum(t.latencia_ms for t in self.trazas)

    @property
    def latencia_por_ruta(self) -> dict:
        out: dict = {}
        for t in self.trazas:
            out[t.ruta] = out.get(t.ruta, 0.0) + t.latencia_ms
        return out
