from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Callable, Sequence
from datetime import datetime

try:
    from datetime import UTC
except ImportError:
    UTC = UTC
from dataclasses import asdict, dataclass, field
from dataclasses import replace as dataclasses_replace

from dominio.arbitraje.divulgacion import Señales
from dominio.diagnostico.clasificador import RespuestaAlItem
from dominio.modelo.contexto_de_uso import ContextoDeUso
from dominio.modelo.respuesta import RespuestaGenerada
from dominio.modelo.turno import ContextoTurno, TrazaFiltro
from dominio.orquestador import ErrorDeOrquestacion, Orquestador
from dominio.pedagogia.conversacion import EstadoDeConversacion
from dominio.pedagogia.estrategias import CAMBIO_DE_REPRESENTACION
from dominio.pedagogia.problema import Observacion, observar
from dominio.pedagogia.sondeo import DesenlaceDelSondeo, EstadoDeSondeo
from dominio.puertos.plantillas import PuertoPlantillas
from dominio.puertos.registro import (
    RELACION_OBSERVABLE,
    BloqueRegistrado,
    CitaRegistrada,
    RegistroAfectivo,
)


_registro = logging.getLogger(__name__)


_TEXTO_DE_FASE: dict[str, str] = {
    "leyendo": "Leyendo tu mensaje",
    "interpretando": "Interpretando la fórmula",
    "resolviendo": "Resolviendo el ejercicio",
    "recuperando": "Buscando material del curso",
    "redactando": "Redactando la respuesta",
    "comprobando": "Comprobando cada afirmación",
}


_FASE_POR_FILTRO: dict[str, str] = {
    "normalización de la entrada": "leyendo",
    "clasificación de intención": "interpretando",
    "recuperación filtrada por nodo": "recuperando",
    "generación": "redactando",
    "verificación simbólica": "comprobando",
    "juicio complementario": "comprobando",
}

_PROGRESO_POR_FILTRO = {
    **{nombre: (fase, _TEXTO_DE_FASE[fase]) for nombre, fase in _FASE_POR_FILTRO.items()},
    "contexto factual experimental de entrada": ("interpretando", "Recuperando el hilo de tu conversación"),
    "interpretación semántica experimental": ("interpretando", "Revisando qué ayuda necesitas"),
    "precómputo simbólico": ("resolviendo", "Preparando la comprobación del ejercicio"),
    "verificación del intento del estudiante": ("resolviendo", "Revisando el ejercicio y tu respuesta"),
    "selección de estrategia": ("redactando", "Eligiendo cómo explicártelo"),
    "contexto factual experimental del generador": ("redactando", "Organizando lo que hemos trabajado"),
    "generación": ("redactando", "Preparando una explicación para ti"),
    "verificación simbólica": ("comprobando", "Comprobando los pasos matemáticos"),
    "juicio complementario": ("comprobando", "Revisando la respuesta antes de mostrarla"),
}


def fase_al_iniciar(nombre: str):
    contenido = _PROGRESO_POR_FILTRO.get(nombre)
    return FaseEmitida(*contenido) if contenido else None

_NIVEL_POR_ENTERO: dict[int, str] = {1: "sondeo", 2: "regla", 3: "desarrollo"}

_PATRON_REFERENCIA = re.compile(r"\{\{\s*([A-Za-z0-9_-]+)\s*\}\}")


@dataclass(frozen=True)
class TurnoEntrante:

    sesion: str
    mensaje: str
    momento: str = ""
    señales: Señales | None = None

    clase: str = ""

    identificador_sujeto: str = ""

    estado_conversacion: EstadoDeConversacion | None = None

    escritura_longitudinal_permitida: bool = True

    identificador_titular: str = ""

    consentimiento_evento: int | None = None

    contexto_de_uso: str = ContextoDeUso.APRENDIZAJE_ESTUDIANTE

    respuesta_al_item: RespuestaAlItem | None = None

    estado_de_sondeo: EstadoDeSondeo | None = None

    expresion_previa: str = ""

    ejercicio_activo: dict[str, str] | None = None

    notacion: str = ""

    historial_reciente: tuple[dict, ...] = ()
    contexto_conversacional: dict = field(default_factory=dict)
    continuidad: dict | None = None

@dataclass(frozen=True)
class FaseEmitida:

    fase: str
    texto: str

@dataclass(frozen=True)
class Bloque:

    tipo: str
    contenido: str
    sello: str
    alternativo: str | None = None

    def __post_init__(self) -> None:
        if self.sello not in ("verificado", "generado"):
            raise ValueError(f"sello inválido «{self.sello}»: §5.1 admite solo dos")
        if self.tipo in ("notacion", "grafica") and not self.alternativo:
            raise ValueError(f"«{self.tipo}» exige `alternativo` (§5, accesibilidad)")

@dataclass(frozen=True)
class Concepto:

    id: str
    nombre: str

@dataclass(frozen=True)
class ContenidoDelCurso:

    banco: object | None = None
    catalogo: object | None = None

@dataclass(frozen=True)
class MaterialDelTurno:

    id: str
    obra: str
    titulo: str
    relacion: str = "recuperado"

@dataclass(frozen=True)
class Procedencia:

    origen: str
    referencia: str = ""

    material: tuple[MaterialDelTurno, ...] = ()

@dataclass(frozen=True)
class RazonOfrecida:

    id: str
    texto: str

@dataclass(frozen=True)
class ItemOfrecido:

    nodo: str
    enunciado: str
    razones: tuple[RazonOfrecida, ...]

@dataclass(frozen=True)
class CuerpoTurno:

    turno: str
    bloques: tuple[Bloque, ...]
    nivel: str
    procedencia: Procedencia
    conceptos: tuple[Concepto, ...] = ()

    sondeo: ItemOfrecido | None = None

@dataclass(frozen=True)
class Degradado:

    ultima_fase: str = ""
    explicacion: str = ""

    turno: str = ""

@dataclass(frozen=True)
class RespuestaTurno:

    fases: tuple[FaseEmitida, ...] = ()
    cuerpo: CuerpoTurno | None = None
    degradado: Degradado | None = None

    estado_conversacion: EstadoDeConversacion | None = None

    desenlace_del_sondeo: DesenlaceDelSondeo = field(default_factory=DesenlaceDelSondeo)

    version_modelo: str = ""

    trazas_contexto: tuple[dict, ...] = ()
    continuidad: dict | None = None

class AdaptadorTurno:

    def __init__(
        self,
        orquestador: Orquestador,
        generador_de_id: Callable[[], str] | None = None,
        reloj: Callable[[], str] | None = None,
        adaptador_perfil=None,
        plantillas: PuertoPlantillas | None = None,
        contenido: ContenidoDelCurso | None = None,
        contexto_reforzado: bool = False,
        continuidad: bool = False,
    ) -> None:
        self._orquestador = orquestador
        self.continuidad = continuidad

        self._generador_de_id = generador_de_id or (lambda: uuid.uuid4().hex)

        self._reloj = reloj or (
            lambda: datetime.now(UTC).isoformat(timespec="milliseconds")
        )

        self._adaptador_perfil = adaptador_perfil

        self._plantillas = plantillas

        self._contenido = contenido or ContenidoDelCurso()
        self.contexto_reforzado = contexto_reforzado

    def manejar_con_progreso(self, entrante: TurnoEntrante, al_iniciar) -> RespuestaTurno:
        return self.manejar(entrante, al_iniciar=al_iniciar)

    def manejar(self, entrante: TurnoEntrante, *, al_iniciar=None) -> RespuestaTurno:
        turno_id = self._generador_de_id()
        ctx = ContextoTurno(
            texto_estudiante=entrante.mensaje,
            identificador_sesion=entrante.sesion,
            identificador_turno=turno_id,

            identificador_sujeto=entrante.identificador_titular,

            consentimiento_evento=entrante.consentimiento_evento,

            momento=self._reloj(),
            señales=entrante.señales,
            clase=entrante.clase,

            contexto_de_uso=entrante.contexto_de_uso,
            estado_conversacion=entrante.estado_conversacion,
            sin_adaptacion=bool(
                entrante.estado_conversacion and entrante.estado_conversacion.sin_adaptacion
            ),
            estrategia_previa=(
                entrante.estado_conversacion.estrategia_previa
                if entrante.estado_conversacion
                else ""
            ),

            perfil_previo=self._cargar_perfil(entrante.identificador_sujeto),
            respuesta_al_item=entrante.respuesta_al_item,

            sondeos_ofrecidos=(
                entrante.estado_de_sondeo.ofrecidos if entrante.estado_de_sondeo else ()
            ),

            sondeos_contestados=(
                entrante.estado_de_sondeo.contestados if entrante.estado_de_sondeo else ()
            ),
            estado_de_sondeo=entrante.estado_de_sondeo,
            expresion_previa=entrante.expresion_previa,
            ejercicio_activo=entrante.ejercicio_activo,
            notacion=entrante.notacion,
            historial_reciente=entrante.historial_reciente,
            contexto_conversacional=entrante.contexto_conversacional,
            continuidad=entrante.continuidad,
        )

        try:
            salida = (self._orquestador.ejecutar(ctx, al_iniciar=al_iniciar)
                      if al_iniciar is not None else self._orquestador.ejecutar(ctx))
        except ErrorDeOrquestacion as exc:

            explicacion = f"no se pudo generar una respuesta: {exc.causa}"
            self._registrar_en_frio(
                entrante.identificador_sujeto,
                dataclasses_replace(exc.ctx_parcial, degradacion=explicacion),
                entrante.escritura_longitudinal_permitida,
            )
            fases_parciales = _fases_desde_trazas(exc.ctx_parcial.trazas)
            return RespuestaTurno(
                fases=fases_parciales,
                degradado=Degradado(
                    ultima_fase=fases_parciales[-1].fase if fases_parciales else "",
                    explicacion=explicacion,
                    turno=turno_id,
                ),
                estado_conversacion=cerrar_estado(entrante, exc.ctx_parcial),
                desenlace_del_sondeo=exc.ctx_parcial.desenlace_del_sondeo,
                version_modelo=_modelo_que_respondio(exc.ctx_parcial),
                trazas_contexto=_trazas_para_contexto(exc.ctx_parcial),
            )

        fases = _fases_desde_trazas(salida.trazas)

        if not salida.respuesta.strip():
            explicacion = "el sistema no generó una respuesta emitible"
            self._registrar_en_frio(
                entrante.identificador_sujeto,
                dataclasses_replace(salida, degradacion=explicacion),
                entrante.escritura_longitudinal_permitida,
            )
            return RespuestaTurno(
                fases=fases,
                degradado=Degradado(
                    ultima_fase=fases[-1].fase if fases else "",
                    explicacion=explicacion,
                    turno=turno_id,
                ),
                estado_conversacion=cerrar_estado(entrante, salida),
                desenlace_del_sondeo=salida.desenlace_del_sondeo,
                version_modelo=_modelo_que_respondio(salida),
                trazas_contexto=_trazas_para_contexto(salida),
            )

        cuerpo = _cuerpo(salida, turno_id, self._contenido)

        cuerpo = _con_sondeo(cuerpo, salida)
        respuesta = RespuestaTurno(
            fases=fases,
            cuerpo=cuerpo,
            estado_conversacion=cerrar_estado(entrante, salida),
            desenlace_del_sondeo=salida.desenlace_del_sondeo,
            version_modelo=_modelo_que_respondio(salida),
            trazas_contexto=_trazas_para_contexto(salida),
            continuidad=salida.continuidad,
        )

        self._registrar_en_frio(
            entrante.identificador_sujeto,
            _como_registro(salida, cuerpo),
            entrante.escritura_longitudinal_permitida,
        )
        return respuesta

    def _cargar_perfil(self, identificador_sujeto: str):
        if self._adaptador_perfil is None or not identificador_sujeto:
            return None
        try:
            return self._adaptador_perfil.reconstruir_perfil(identificador_sujeto)
        except Exception:
            return None

    def _registrar_en_frio(
        self, identificador_sujeto: str, ctx: ContextoTurno, permitida: bool = True
    ) -> None:

        if self._adaptador_perfil is not None and identificador_sujeto and permitida:
            try:
                self._guardar_perfil(identificador_sujeto, ctx)
            except Exception:
                _registro.exception(
                    "no se pudo guardar el perfil del turno %s (sesión %s)",
                    ctx.identificador_turno or "sin identificador",
                    ctx.identificador_sesion or "sin sesión",
                )
        try:
            self._orquestador.ejecutar_fria(ctx)
        except Exception:
            _registro.exception(
                "no se pudo registrar el turno %s (sesión %s) en la ruta fría",
                ctx.identificador_turno or "sin identificador",
                ctx.identificador_sesion or "sin sesión",
            )

    def _guardar_perfil(self, identificador_sujeto: str, ctx: ContextoTurno) -> None:
        traza = next(
            (t for t in ctx.trazas if t.filtro == "extracción de indicadores conductuales"),
            None,
        )
        if traza is None:
            return
        for entrada in traza.metadatos.get("entradas_de_auditoria", ()):
            self._adaptador_perfil.registrar_afectivo(
                identificador_sujeto,
                RegistroAfectivo(
                    turno=entrada["turno"],
                    subcomponente=entrada["subcomponente"],
                    senal=entrada["senal"],
                    regla_aplicada=entrada["regla_aplicada"],
                    valor_previo=entrada["valor_previo"],
                    valor_nuevo=entrada["valor_nuevo"],
                    lambda_aplicado=entrada["lambda_aplicado"],
                    certeza=entrada["certeza"],
                    alcance=entrada["alcance"],
                ),
            )

def _trazas_para_contexto(ctx: ContextoTurno) -> tuple[dict, ...]:
    nombres = {"clasificación de intención", "verificación del intento del estudiante",
               "verificación simbólica"}
    return tuple(asdict(t) for t in ctx.trazas if t.filtro in nombres)

def _modelo_que_respondio(ctx: ContextoTurno) -> str:
    return getattr(ctx.generacion, "modelo", "") or ""

def _fases_desde_trazas(trazas: Sequence[TrazaFiltro]) -> tuple[FaseEmitida, ...]:
    fases: list[FaseEmitida] = []
    for t in trazas:
        if t.metadatos.get("omitido"):
            continue
        fase_id = _FASE_POR_FILTRO.get(t.filtro)
        if fase_id is None:
            continue
        fases.append(FaseEmitida(fase=fase_id, texto=_TEXTO_DE_FASE[fase_id]))
    return tuple(fases)

def _como_registro(ctx: ContextoTurno, cuerpo: CuerpoTurno) -> ContextoTurno:
    return dataclasses_replace(
        ctx,

        respuesta=(
            ctx.respuesta_generada.narracion
            if ctx.respuesta_generada is not None
            else ctx.respuesta
        ),
        bloques_emitidos=tuple(
            BloqueRegistrado(
                tipo=b.tipo,
                contenido=b.contenido,
                sello=b.sello,
                alternativo=b.alternativo or "",
            )
            for b in cuerpo.bloques
        ),
        citas_emitidas=(

            *(
                CitaRegistrada(marca=c.identificador, expresion=c.expresion)
                for c in (
                    ctx.respuesta_generada.citadas
                    if ctx.respuesta_generada is not None
                    else ()
                )
            ),

            *(
                CitaRegistrada(
                    marca=a.identificador,
                    expresion=f"{a.izquierda} {a.relacion} {a.derecha}",
                )
                for a in (
                    ctx.respuesta_generada.afirmaciones
                    if ctx.respuesta_generada is not None
                    else ()
                )
            ),
        ),
        conceptos_emitidos=tuple(concepto.id for concepto in cuerpo.conceptos),
        nivel_emitido=cuerpo.nivel,
        procedencia_origen=cuerpo.procedencia.origen,
        procedencia_referencia=cuerpo.procedencia.referencia,
    )

def _cuerpo(
    ctx: ContextoTurno, turno_id: str, contenido: ContenidoDelCurso | None = None
) -> CuerpoTurno:
    nivel_str = _NIVEL_POR_ENTERO.get(ctx.nivel_divulgacion, "sondeo")

    aprobada = ctx.informe is not None and ctx.informe.aprobada

    verificable = ctx.nivel_divulgacion > 1 and aprobada

    if ctx.respuesta_generada is None:

        bloques: tuple[Bloque, ...] = (
            Bloque(tipo="prosa", contenido=ctx.respuesta, sello="generado"),
        )
    else:
        bloques = _bloques_desde_respuesta(ctx.respuesta_generada, verificable) or (
            Bloque(tipo="prosa", contenido=ctx.respuesta, sello="generado"),
        )

    bloque_grafica = _bloque_grafica(ctx, verificable)
    if bloque_grafica is not None:
        bloques = (*bloques, bloque_grafica)

    return CuerpoTurno(
        turno=turno_id,
        bloques=bloques,
        nivel=nivel_str,
        procedencia=_procedencia(ctx.recuperacion, (contenido or ContenidoDelCurso()).catalogo),
        conceptos=_conceptos_invocados(
            ctx.recuperacion, (contenido or ContenidoDelCurso()).banco
        ),
    )

def cerrar_estado(entrante: TurnoEntrante, ctx: ContextoTurno) -> EstadoDeConversacion | None:
    estado = entrante.estado_conversacion or EstadoDeConversacion()
    intencion = ctx.intencion_detalle
    if intencion is None:
        return estado

    from dominio.pedagogia.confirmacion import base_de_ejercicio

    intento = next((t.metadatos for t in reversed(ctx.trazas)
                    if t.filtro == "verificación del intento del estudiante"), {})

    problema, _evento = observar(
        estado.problema,
        Observacion(
            intencion=intencion,
            expresiones=ctx.expresiones,

            expresiones_heredadas=ctx.expresiones_heredadas,
            nodo=ctx.nodo_activo,

            item=(
                ctx.desenlace_del_sondeo.nodo
                if ctx.desenlace_del_sondeo.admitida
                else ""
            ),
            veredicto=ctx.veredicto_del_intento,
            base=base_de_ejercicio(ctx.ejercicio_activo),
            propuesta=str(intento.get("propuesta") or ""),
            correccion_comprobada=bool(ctx.retroalimentacion_del_intento and ctx.informe and ctx.informe.aprobada),
            estrategia=(
                ctx.decision_pedagogica.estrategia if ctx.decision_pedagogica else ""
            ),
        ),
    )
    return EstadoDeConversacion(

        afectivo=(ctx.estado_conversacion or estado).afectivo,
        problema=problema,

        sin_adaptacion=(
            False
            if intencion.reactiva_adaptacion and not intencion.sin_adaptacion
            else (estado.sin_adaptacion or intencion.sin_adaptacion)
        ),
        estrategia_previa=(
            ctx.decision_pedagogica.estrategia
            if ctx.decision_pedagogica
            else estado.estrategia_previa
        ),
    )

def _bloques_desde_respuesta(
    respuesta: RespuestaGenerada, verificable: bool = True
) -> tuple[Bloque, ...]:

    por_id = {a.identificador: a for a in respuesta.afirmaciones}
    citadas = {c.identificador: c for c in respuesta.citadas}
    partes = _PATRON_REFERENCIA.split(respuesta.narracion)

    bloques: list[Bloque] = []
    for i, parte in enumerate(partes):
        if i % 2 == 0:

            if parte.strip():
                bloques.append(Bloque(tipo="prosa", contenido=parte, sello="generado"))
            continue

        citada = citadas.get(parte)
        if citada is not None:
            bloques.append(
                Bloque(
                    tipo="expresion-citada",
                    contenido=citada.expresion,
                    sello="generado",
                    alternativo=f"expresión mencionada: {citada.expresion}",
                )
            )
            continue

        afirmacion = por_id.get(parte)
        if afirmacion is None:
            continue
        original = f"{afirmacion.izquierda} {afirmacion.relacion} {afirmacion.derecha}"
        if verificable:
            from adaptadores.entrantes.http.notacion_verificada import latex_de_afirmacion
            contenido = latex_de_afirmacion(
                afirmacion.izquierda, afirmacion.relacion, afirmacion.derecha,
            )
        else:
            contenido = original
        sello = "verificado" if verificable else "generado"
        adjetivo = "verificada" if verificable else "sin verificar"
        bloques.append(
            Bloque(
                tipo="notacion",
                contenido=contenido,
                sello=sello,
                alternativo=f"expresión matemática {adjetivo}: {original}",
            )
        )
    return _sin_espacios_en_los_extremos(bloques)

def _sin_espacios_en_los_extremos(bloques: list[Bloque]) -> tuple[Bloque, ...]:
    if not bloques:
        return ()
    salida = list(bloques)
    for indice, recorte in ((0, "izquierda"), (-1, "derecha")):
        b = salida[indice]
        if b.tipo != "prosa":
            continue
        limpio = b.contenido.lstrip() if recorte == "izquierda" else b.contenido.rstrip()
        if limpio != b.contenido:
            salida[indice] = Bloque(
                tipo=b.tipo, contenido=limpio, sello=b.sello, alternativo=b.alternativo
            )
    return tuple(salida)

def _con_sondeo(cuerpo: CuerpoTurno, ctx: ContextoTurno) -> CuerpoTurno:
    item = ctx.item_ofrecido
    if item is None:
        return cuerpo

    return dataclasses_replace(
        cuerpo,
        sondeo=ItemOfrecido(
            nodo=item.nodo,
            enunciado=item.enunciado,

            razones=tuple(
                RazonOfrecida(id=o.identificador, texto=o.texto) for o in item.opciones
            ),
        ),
    )

_PIDE_GRAFICA = re.compile(
    r"\b(?:gr[aá]fic\w*|dib[uú]j\w*|traz\w*|curva|representa\w*|superpon\w*)\b", re.I,
)
_PIDE_COMPARACION_GRAFICA = re.compile(
    r"\b(?:a[nñ]ad\w*|agreg\w*|superpon\w*|compar\w*|pon\s+al\s+lado)\b", re.I,
)


def _funcion_declarada(texto: str, letra: str | None = None) -> str:
    from dominio.modelo.notacion_entrada import (
        normalizar_escritura_matematica,
        normalizar_frase_matematica,
    )

    normalizado = normalizar_escritura_matematica(texto)
    nombre = "[a-zA-Z]" if letra is None else re.escape(letra)
    etiqueta = rf"{nombre}\s*(?:\\left\s*)?\(\s*x\s*(?:\\right\s*)?\)"
    if letra is None:
        etiqueta = rf"(?:{etiqueta}|y)"
    encontrada = re.search(rf"\b{etiqueta}\s*=\s*(.+)", normalizado, re.I | re.S)
    if encontrada is None:
        return ""
    formula = encontrada.group(1)
    nivel = 0
    for indice, caracter in enumerate(formula):
        if caracter in "({[":
            nivel += 1
        elif caracter in ")}]":
            nivel -= 1
        elif nivel == 0 and caracter in ",;?.!":
            decimal = caracter in ",." and indice > 0 and formula[indice-1].isdigit() and formula[indice+1:indice+2].isdigit()
            if not decimal:
                formula = formula[:indice]
                break
    expresion = re.split(
        r"\s+(?:y\s+(?:su|la|el|para|que|dime)\b|cerca\b|para\b|pero\b|como\b|"
        r"temporalmente\b|alrededor\b|y\s+(?=[a-zA-Z]\s*(?:\\left\s*)?\(\s*x\s*(?:\\right\s*)?\)\s*=)|"
        r"y\s+(?:expl[ií]ca\w*|mu[eé]stra\w*|cu[eé]nta\w*|c[oó]mo|qu[eé])\b|por\s+favor\b)", formula, maxsplit=1, flags=re.I,
    )[0].strip().strip('$')
    return normalizar_frase_matematica(expresion)

def _nombre_funcion(ctx: ContextoTurno, fuente: str) -> str:
    from dominio.modelo.notacion_entrada import normalizar_escritura_matematica
    textos = [ctx.texto_estudiante, *(str(t.get("estudiante", "")) for t in reversed(ctx.historial_reciente))]
    for texto in textos:
        normalizado = normalizar_escritura_matematica(texto)
        for letra in re.findall(r"\b([a-zA-Z])\s*(?:\\left\s*)?\(\s*x\s*(?:\\right\s*)?\)\s*=", normalizado):
            if _funcion_declarada(texto, letra) == fuente:
                return letra
    return "f"

def _formula_para_grafica(texto: str) -> str:
    from dominio.filtros.normalizacion import segmentar
    from dominio.modelo.notacion_entrada import normalizar_escritura_matematica

    for expresion in segmentar(normalizar_escritura_matematica(texto))[0]:
        formula = expresion.strip().rstrip(".,; ")
        if "x" in formula.lower() and not re.fullmatch(r"x\s*=\s*[-+]?\d+(?:[.,]\d+)?", formula, re.I):
            return formula
    return ""

def _principal_del_historial(ctx: ContextoTurno) -> str:
    for anterior in reversed(ctx.historial_reciente):
        if _PIDE_COMPARACION_GRAFICA.search(str(anterior.get("estudiante", ""))):
            continue
        fuente = _funcion_declarada(str(anterior.get("estudiante", "")))
        if fuente:
            return fuente
    for anterior in reversed(ctx.historial_reciente):
        texto = str(anterior.get("estudiante", ""))
        if _PIDE_COMPARACION_GRAFICA.search(texto):
            continue
        fuente = _formula_para_grafica(texto)
        if fuente:
            return fuente
    return ""

def _bloque_grafica(ctx: ContextoTurno, verificable: bool) -> Bloque | None:
    sin_grafica = bool(re.search(
        r"\bsin\s+(?:(?:volver\s+a\s+)?(?:depender|usar)\s+d(?:e|el)\s+)?"
        r"(?:la\s+|el\s+)?(?:gr[aá]fica|dibujo|curva)\b",
        ctx.texto_estudiante, re.I,
    ))
    if sin_grafica:
        return None
    pide_grafica = bool(_PIDE_GRAFICA.search(ctx.texto_estudiante))
    if re.search(r"\btangente\b", ctx.texto_estudiante, re.I) and pide_grafica:
        fuente = _funcion_declarada(ctx.texto_estudiante) or _principal_del_historial(ctx)
        if fuente:
            try:
                from adaptadores.salientes.simbolico.adaptador import AdaptadorSimbolico
                from adaptadores.salientes.simbolico.graficadora import preparar_curvas
                from dominio.modelo.matematica import BloqueVerificable
                cas = AdaptadorSimbolico()
                pre = cas.precomputar(fuente)
                if pre.ok and pre.derivada_js and cas.verificar((BloqueVerificable(
                    identificador="tangente", izquierda=f"d/dx ({fuente})",
                    derecha=pre.resultado_corriente,
                ),)).aprobada:
                    curva = preparar_curvas([{"expresion": fuente, "variable": "x", "tipo": "funcion"}])[0]
                    punto = re.search(r"\bx\s*=\s*([-+]?\d+(?:[.,]\d+)?)", ctx.texto_estudiante)
                    verbal = re.search(r"\ben\s+(?:el\s+)?(cero|uno|dos|tres)\b", ctx.texto_estudiante, re.I)
                    puntos_verbales = {"cero": 0, "uno": 1, "dos": 2, "tres": 3}
                    contenido = {
                        "funcion_js": curva["funcion_js"], "derivada_js": pre.derivada_js,
                        "expresion": fuente, "mostrar_tangente": True,
                        "punto_x": (float(punto.group(1).replace(",", ".")) if punto
                                    else puntos_verbales[verbal.group(1).lower()] if verbal else 0),
                    }
                    return Bloque(
                        tipo="grafica", contenido=json.dumps(contenido, ensure_ascii=False),
                        sello="verificado", alternativo=f"Gráfica y tangente de f(x) = {fuente}.",
                    )
            except ValueError:
                pass

    if re.search(r"\b(?:los\s+)?tres\b", ctx.texto_estudiante, re.I) and re.search(
        r"\b(?:tabla|gr[aá]fica|dibujo|representaci[oó]n)\b", ctx.texto_estudiante, re.I,
    ):
        from adaptadores.salientes.simbolico.graficadora import preparar_curvas
        from dominio.modelo.notacion_entrada import normalizar_escritura_matematica

        candidatas: list[str] = []
        for anterior in ctx.historial_reciente[-5:]:
            texto = normalizar_escritura_matematica(str(anterior.get("estudiante", "")))
            texto = re.sub(r"\bx\s+(?:al\s+)?cuadrado\b", "x^2", texto, flags=re.I)
            texto = re.sub(r"\bsobre\b", "/", texto, flags=re.I)
            texto = re.sub(r"\s*/\s*", "/", texto)
            for expresion in re.findall(r"(?<![\w])x(?:\^\(?\d+\)?)?/x(?:\^\(?\d+\)?)?", texto):
                if expresion not in candidatas:
                    candidatas.append(expresion)
        if len(candidatas) >= 3:
            try:
                curvas = preparar_curvas([
                    {"expresion": expresion, "variable": "x", "tipo": "funcion"}
                    for expresion in candidatas[:4]
                ])
                return Bloque(
                    tipo="grafica", contenido=json.dumps({"curvas": curvas, "expresion": candidatas[0]}, ensure_ascii=False),
                    sello="generado", alternativo="Gráficas comparadas de " + ", ".join(candidatas[:4]) + ".",
                )
            except ValueError:
                pass
    comparacion_retroactiva = bool(
        re.search(r"\b(?:tabla|gr[aá]fica)\b", ctx.texto_estudiante, re.I)
        and re.search(r"\b(?:diferencia|comparar|comparaci[oó]n)\b", ctx.texto_estudiante, re.I)
        and not _formula_para_grafica(ctx.texto_estudiante)
    )
    if (pide_grafica or _PIDE_COMPARACION_GRAFICA.search(ctx.texto_estudiante)) and not comparacion_retroactiva:
        from adaptadores.salientes.simbolico.graficadora import preparar_curvas

        activo = ctx.ejercicio_activo or {}

        nombres = re.findall(r"\b([a-zA-Z])\s*(?:\\left\s*)?\(\s*x\s*(?:\\right\s*)?\)\s*=", ctx.texto_estudiante)
        comparar = bool(_PIDE_COMPARACION_GRAFICA.search(ctx.texto_estudiante)) or len(nombres) > 1
        declarada = _funcion_declarada(ctx.texto_estudiante)
        previa = activo.get("expresion", "") or _principal_del_historial(ctx)
        principal = (previa or declarada) if comparar and len(nombres) < 2 else (declarada or previa)
        nueva = ""
        if comparar:
            for nombre in reversed(nombres):
                candidata = _funcion_declarada(ctx.texto_estudiante, nombre)
                if candidata and candidata != principal:
                    nueva = candidata
                    break
            if not nueva:
                nueva = _formula_para_grafica(ctx.texto_estudiante)
        if nueva and principal and nueva != principal:
            try:
                curvas = preparar_curvas([
                    {"expresion": principal, "variable": "x", "tipo": "funcion"},
                    {"expresion": nueva, "variable": "x", "tipo": "funcion"},
                ])
                for curva in curvas:
                    nombre = _nombre_funcion(ctx, curva["expresion"])
                    if nombre != "f":
                        curva["nombre_funcion"] = nombre
                return Bloque(
                    tipo="grafica", contenido=json.dumps({"curvas": curvas, "expresion": principal}, ensure_ascii=False),
                    sello="generado", alternativo=f"Gráficas de {curvas[0].get('nombre_funcion', 'f')}(x) = {principal} y {curvas[1].get('nombre_funcion', 'g')}(x) = {nueva}.",
                )
            except ValueError:
                pass

        if pide_grafica and not nueva:
            from dominio.filtros.intencion import extraer_curva_solicitada
            fuente = (_funcion_declarada(ctx.texto_estudiante)
                      or extraer_curva_solicitada(ctx.texto_estudiante)
                      or _formula_para_grafica(ctx.texto_estudiante) or principal)
            if fuente:
                try:
                    curva = preparar_curvas([{"expresion": fuente, "variable": "x", "tipo": "funcion"}])[0]
                    contenido = {"funcion_js": curva["funcion_js"], "expresion": fuente}
                    nombre = _nombre_funcion(ctx, fuente)
                    if nombre != "f":
                        contenido["nombre_funcion"] = nombre
                    if activo.get("tipo") == "limite" and fuente == activo.get("expresion"):
                        contenido.update(limite_destino=activo.get("destino", ""), variable=activo.get("variable", "x"))
                    return Bloque(
                        tipo="grafica", contenido=json.dumps(contenido, ensure_ascii=False),
                        sello="generado", alternativo=f"Gráfica de {nombre}(x) = {fuente}.",
                    )
                except ValueError:
                    pass
    from dominio.filtros.intencion import extraer_curva_solicitada
    solicitada = extraer_curva_solicitada(ctx.texto_estudiante)
    if solicitada:
        try:
            from adaptadores.salientes.simbolico.graficadora import preparar_curvas
            principal = (ctx.ejercicio_activo or {}).get("expresion", "")
            if not principal and re.search(r"\b(?:a[nñ]ade|agrega)\b", ctx.texto_estudiante, re.I):
                for turno in reversed(ctx.historial_reciente):
                    principal = extraer_curva_solicitada(str(turno.get("estudiante", "")))
                    if principal and principal != solicitada:
                        break
            if principal and principal != solicitada:
                curvas = preparar_curvas([
                    {
                        "expresion": principal, "variable": "x",
                        "tipo": "limite" if (ctx.ejercicio_activo or {}).get("tipo") == "limite" else "funcion",
                        "destino": (ctx.ejercicio_activo or {}).get("destino", ""),
                    },
                    {"expresion": solicitada, "variable": "x", "tipo": "funcion"},
                ])
                return Bloque(
                    tipo="grafica",
                    contenido=json.dumps({"curvas": curvas, "expresion": principal}, ensure_ascii=False),
                    sello="generado",
                    alternativo=f"Gráfica de f(x) = {principal} y g(x) = {solicitada}.",
                )
            curva = preparar_curvas([{"expresion": solicitada, "variable": "x", "tipo": "funcion"}])[0]
            contenido = {"funcion_js": curva["funcion_js"], "expresion": solicitada}
            if ctx.es_limite and solicitada == ctx.limite_expresion:
                contenido.update(limite_destino=ctx.limite_destino, variable=ctx.limite_variable)
            return Bloque(
                tipo="grafica", contenido=json.dumps(contenido, ensure_ascii=False),
                sello="generado", alternativo=f"Gráfica de f(x) = {solicitada}.",
            )
        except ValueError:
            pass
    if re.search(r"\b(?:tabla|gr[aá]fica)\b", ctx.texto_estudiante, re.I) and re.search(
        r"\b(?:diferencia|comparar|comparaci[oó]n)\b", ctx.texto_estudiante, re.I,
    ):
        from dominio.modelo.notacion_entrada import normalizar_escritura_matematica
        candidatas: list[str] = []
        for anterior in ctx.historial_reciente[-5:]:
            texto = normalizar_escritura_matematica(str(anterior.get("estudiante", "")))
            for expresion in re.findall(
                r"(?<![\w])x(?:\^\(?\d+\)?)?/x(?:\^\(?\d+\)?)?", texto,
            ):
                if expresion not in candidatas:
                    candidatas.append(expresion)
        if len(candidatas) >= 2:
            try:
                from adaptadores.salientes.simbolico.graficadora import preparar_curvas
                curvas = preparar_curvas([
                    {"expresion": expresion, "variable": "x", "tipo": "funcion"}
                    for expresion in candidatas[:4]
                ])
                return Bloque(
                    tipo="grafica",
                    contenido=json.dumps({"curvas": curvas, "expresion": candidatas[0]}, ensure_ascii=False),
                    sello="generado", alternativo="Gráficas comparadas de " + ", ".join(candidatas[:4]) + ".",
                )
            except ValueError:
                pass

    if ctx.ejercicio_activo:
        from dominio.filtros.intencion import extraer_ejercicio_explicito
        pide_grafica_actual = bool(
            ctx.intencion_detalle
            and ctx.intencion_detalle.estrategia_solicitada == CAMBIO_DE_REPRESENTACION
        )
        if not pide_grafica_actual and extraer_ejercicio_explicito(ctx.texto_estudiante) is None:
            return None

    precomputo = ctx.precomputo
    if precomputo is None or not precomputo.ok or not precomputo.funcion_js:

        pide_grafica = bool(
            ctx.intencion_detalle
            and ctx.intencion_detalle.estrategia_solicitada == CAMBIO_DE_REPRESENTACION
        )
        fuente = ctx.limite_expresion if ctx.es_limite else (
            ctx.expresiones[0] if ctx.expresiones else ctx.expresion_previa or ""
        )
        if not pide_grafica or not fuente:
            return None
        try:
            from adaptadores.salientes.simbolico.graficadora import preparar_curvas

            curva = preparar_curvas([{
                "expresion": fuente,
                "variable": ctx.limite_variable if ctx.es_limite else "x",
                "tipo": "limite" if ctx.es_limite else "funcion",
                "destino": ctx.limite_destino if ctx.es_limite else "",
            }])[0]
        except ValueError:
            return None
        contenido = {
            "funcion_js": curva["funcion_js"],
            "expresion": fuente,
        }
        if ctx.es_limite:
            contenido["limite_destino"] = ctx.limite_destino
            contenido["variable"] = ctx.limite_variable
        return Bloque(
            tipo="grafica",
            contenido=json.dumps(contenido, ensure_ascii=False),
            sello="generado",
            alternativo=f"Gráfica de f({curva['variable']}) = {fuente}.",
        )

    expresion = precomputo.expresion_fuente or (
        ctx.expresiones[0] if ctx.expresiones else "la función de este turno"
    )
    if not ctx.es_limite and "x" not in expresion:
        return None
    contenido: dict[str, str] = {
        "funcion_js": precomputo.funcion_js,

        "expresion": expresion,
    }
    if ctx.es_limite:
        contenido["limite_destino"] = ctx.limite_destino
        contenido["variable"] = ctx.limite_variable
    elif verificable and precomputo.derivada_js:
        contenido["derivada_js"] = precomputo.derivada_js

    alternativo = (
        f"Gráfica de f(x) = {expresion} y su derivada."
        if "derivada_js" in contenido
        else (
            f"Gráfica de f({ctx.limite_variable}) = {expresion} cerca de {ctx.limite_variable} → {ctx.limite_destino}."
            if ctx.es_limite else f"Gráfica de f(x) = {expresion}."
        )
    )

    return Bloque(
        tipo="grafica",
        contenido=json.dumps(contenido, ensure_ascii=False),
        sello="verificado" if "derivada_js" in contenido else "generado",
        alternativo=alternativo,
    )

def _procedencia(recuperacion, catalogo=None) -> Procedencia:
    if recuperacion is None or not recuperacion.utilizable:
        return Procedencia(origen="sin-fuente")

    return Procedencia(
        origen="corpus",
        referencia=", ".join(f.identificador for f in recuperacion.fragmentos),
        material=tuple(
            MaterialDelTurno(
                id=f.identificador,
                obra=f.procedencia.obra,
                titulo=_titulo_del_material(f, catalogo),
                relacion=RELACION_OBSERVABLE,
            )
            for f in recuperacion.fragmentos
        ),
    )

def _titulo_del_material(fragmento, catalogo) -> str:
    if catalogo is None:
        return fragmento.identificador
    try:
        return catalogo.titulo_de_fragmento(fragmento.identificador)
    except Exception:
        return fragmento.identificador

def _conceptos_invocados(recuperacion, banco) -> tuple[Concepto, ...]:
    if banco is None or recuperacion is None or not recuperacion.utilizable:
        return ()

    nodos: list[str] = []
    for fragmento in recuperacion.fragmentos:
        nodo = getattr(fragmento, "nodo_grafo", None)
        if nodo and nodo not in nodos:
            nodos.append(nodo)

    invocados: dict[str, Concepto] = {}
    for nodo in nodos:
        for pagina in banco.por_nodo(nodo):

            invocados.setdefault(pagina.identificador, Concepto(
                id=pagina.identificador,
                nombre=pagina.nombre,
            ))
    return tuple(invocados.values())
