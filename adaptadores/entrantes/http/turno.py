"""
turno.py — La ruta del turno (`PM-B14`)
===========================================

Recibe lo que el estudiante escribió y emite la respuesta **en dos tiempos**,
según `DD-11`: primero la secuencia de fases, al final el cuerpo con sus
bloques y sellos. El contrato completo está en
`OE3-Implementacion/08-Contrato-del-Turno.md`; este módulo es lo que lo hace
cierto contra la cadena real.

Qué traduce, y por qué aquí y no en el dominio
------------------------------------------------
`ADR-001` §7.2: el dominio no conoce el borde. `ContextoTurno` no tiene
`fases`, ni `bloques`, ni `sello` — tiene `trazas`, `respuesta_generada` e
`informe`, que son los tipos del núcleo. Este adaptador es la única frontera
donde uno se convierte en el otro, que es exactamente lo que la regla **N2**
de `pruebas/arquitectura/` vigila.

Las tres reglas que se aplican aquí y no se delegan
--------------------------------------------------------
1. **Emisión por partes (`DD-11`).** Las fases se derivan de `ctx.trazas`
   —qué filtro corrió, en qué orden— contra el **catálogo cerrado** de seis.
   Un filtro sin fase asociada no inventa una: enrutamiento (4) y
   construcción del prompt (7) son trabajo interno y no tienen entrada en el
   catálogo, así que no emiten fase propia. Se anuncia qué hace el sistema,
   nunca qué infiere sobre el estudiante.
2. **Separación por rol (`RP-17`).** Esta función solo construye lo que el
   árbol del **estudiante** puede ver. Ningún campo de `ContextoTurno` que
   §9 del contrato prohíbe —precómputo, informe crudo, nombre de filtro,
   traza— cruza a `RespuestaTurno`. No hay una lista de exclusión que
   mantener: la traducción solo lee los campos que el contrato admite, así
   que lo prohibido nunca se toca para empezar.
3. **Traducción de tipos.** `RespuestaGenerada`, `InformeVerificacion` y
   `Recuperacion` no salen de aquí. Lo que sale son `Bloque`, `Procedencia` y
   `CuerpoTurno`, con sus campos de texto plano.

**`PM-B26` · el bloque `grafica`.** `_bloque_grafica()` es la cuarta
traducción: `ctx.precomputo.funcion_js`/`derivada_js` (`dominio/modelo/
matematica.py`) a un `Bloque` cuyo `contenido` es JSON —`{"funcion_js": …}`,
con `"derivada_js"` solo si el nivel ya lo permite—, documentado en
`08-Contrato-del-Turno.md` §6.ter.

Lo que este módulo NO hace, y por qué se queda corto a propósito
--------------------------------------------------------------------
**No mecaniza la emisión por partes.** `08-Contrato-del-Turno.md` §12 dice
que la tecnología que transporta las fases «es una decisión posterior y no
cambia nada de este documento». `manejar()` es una llamada síncrona que
devuelve las dos partes ya construidas; conectarlas a un flujo real
—*server-sent events*, *websocket*— es del adaptador HTTP concreto, que
todavía no existe.

**`ultima_fase` ya se reconstruye.** `Orquestador.ejecutar` (2026-08-08)
envuelve la excepción de un filtro en `ErrorDeOrquestacion`, con el
`ContextoTurno` tal como quedó justo antes del filtro que falló. Este
adaptador lee sus trazas para derivar las fases que sí llegaron a correr, y
la última de ellas es `ultima_fase`. Antes de ese cambio, la excepción se
propagaba desnuda y el contexto parcial se perdía con la pila.

**No detecta `fuera-de-dominio` ni `fuera-de-alcance` (§8.1, §8.2).** Ningún
filtro de la cadena de hoy clasifica el turno como ajeno al cálculo
diferencial ni detecta señales de riesgo — esas son responsabilidades de
filtros que no existen todavía. `RespuestaTurno` tiene sitio para que un
filtro futuro los alimente; nada los produce hoy, y no se fabrica una
detección para llenar el hueco.

**No autentica.** `PM-B15` tiene su propia sesión. `TurnoEntrante` no lleva
identidad más allá de `sesion`, que `RP-02` ya obliga a asignar y conservar
antes de este adaptador.

**`PM-B10`/`PM-B11`, enganchados el 2026-08-12.** `AdaptadorTurno` ahora
CARGA `perfil_previo` antes de correr la cadena y GUARDA las entradas de
auditoría del filtro 3 después, con el mismo `adaptador_perfil` (`PM-B11`)
que `aplicacion.py` ya usaba para `RP-19` — un objeto, dos consumidores. Las
dos operaciones son opcionales por diseño: sin `adaptador_perfil` (sin
`AGENTE_BD`) o sin `identificador_sujeto` —hoy sólo cuando `RL-09` deshabilita
el módulo conductual; la «sesión anónima» que aquí se citaba desapareció con
`EQ-020` en el hito B1—, el filtro 3 corre igual —no hace I/O, ver su
docstring— pero no persiste. Un
fallo al guardar **no tumba la respuesta ya construida**: se captura y se
ignora, la misma disciplina que `dominio/filtros/registro.py` declara para
el filtro 12.

**`PM-B20`, enganchado el mismo día.** `Orquestador.ejecutar_fria(ctx)` se
llama aquí, después de que `salida`/`exc.ctx_parcial` ya tienen todas las
trazas de la ruta caliente — nunca antes de saber si el turno se degradó, y
siempre envuelto para que un fallo del registro en frío no tumbe una
respuesta que el estudiante ya recibió.

**No mide `momento`.** El contrato lo declara —marca de tiempo del
cliente— pero ningún filtro de hoy lo consume: `RP-03` (latencia del
estudiante frente a la del sistema) es del filtro 3, que depende del modelo
del estudiante y no existe en este incremento. Se recibe y se conserva en
`TurnoEntrante` para no romper el contrato, sin usarlo todavía.
"""

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

#: `A4`, 2026-08-18 · el primer registrador del árbol, y va aquí porque es
#: aquí donde hay algo que se traga. La ruta fría **puede** fallar en silencio
#: para el estudiante —la respuesta ya se emitió— pero nunca para quien opera
#: el sistema (`CONTEXTO-MAESTRO.md` §5.1, cero modo mock silencioso).
#:
#: No se configura nivel ni manejador: eso es de quien despliega, y fijarlo
#: aquí se lo quitaría. Uvicorn ya trae la suya.
_registro = logging.getLogger(__name__)

# ── El catálogo cerrado de fases · `DD-11` ────────────────────────────────
#
# Seis y no más. Ampliarlo es modificar `DD-11`, no añadir una constante.

_TEXTO_DE_FASE: dict[str, str] = {
    "leyendo": "Leyendo tu mensaje",
    "interpretando": "Interpretando la fórmula",
    "resolviendo": "Resolviendo el ejercicio",
    "recuperando": "Buscando material del curso",
    "redactando": "Redactando la respuesta",
    "comprobando": "Comprobando cada afirmación",
}

#: Qué fase del catálogo corresponde a cada filtro de la cadena, por su
#: nombre de traza. Es una decisión de esta sesión y no del contrato: un
#: filtro que no aparece aquí no tiene fase propia y no aparece en la
#: emisión —enrutamiento (4) y construcción del prompt (7) son trabajo
#: interno—. El filtro 10 (juez), cuando exista, se suma a `comprobando`:
#: los dos juzgan la respuesta antes de emitirla.
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

#: `08-Contrato-del-Turno.md` §6: el dominio usa un entero, el contrato una
#: palabra. `sondeo` es el piso seguro si algún día apareciera un nivel que
#: esta tabla no anticipa — no debería ocurrir, `RespuestaGenerada.problemas()`
#: ya rechaza un nivel fuera de la escala antes de llegar aquí.
_NIVEL_POR_ENTERO: dict[int, str] = {1: "sondeo", 2: "regla", 3: "desarrollo"}

_PATRON_REFERENCIA = re.compile(r"\{\{\s*([A-Za-z0-9_-]+)\s*\}\}")


# ── Lo que entra ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TurnoEntrante:
    """§3 del contrato. Tres campos del estudiante, y ninguno más.

    `señales` **no viene del estudiante**: la pone el servidor a partir de lo
    que sabe de la sesión —cuántos intentos lleva en este paso, si confirmó que
    quería ver la solución— y por eso no incumple §3, que enumera lo que *el
    cliente envía*. Si viajara desde el navegador, el estudiante podría
    escalarse a sí mismo al nivel 3 escribiendo un campo, y la escala de
    `RF-GEN-05` dejaría de ser del dominio.
    """

    sesion: str
    mensaje: str
    momento: str = ""
    señales: Señales | None = None
    #: `PM-B21` · igual que `señales`, lo pone el servidor y no el estudiante:
    #: qué clase de `DD-12` es dueña de este turno, cuando se puede resolver
    #: sin ambigüedad. Vacío si la sesión no está en ninguna clase o está en
    #: más de una — ver `dominio/modelo/turno.py::ContextoTurno.clase`.
    clase: str = ""
    #: `PM-B10`/`PM-B15` · la clave del perfil versionado (`PM-B11`), resuelta
    #: por el servidor con la misma preferencia que ya aplica `aplicacion.py`
    #: en la supresión de `RP-19`: `identificador_estable` si la sesión se
    #: autenticó con Google, si no `identificador_sesion`. Vacío si ninguno de
    #: los dos existe — no debería pasar en producción, pero el adaptador no
    #: asume que siempre llega.
    identificador_sujeto: str = ""
    #: Fase 4 · el estado pedagógico **de esta conversación**: afectivo
    #: temporal, problema abierto con sus contadores y episodios, y
    #: preferencias. Lo pone el servidor desde la sesión, igual que `señales`.
    #: Es el que decide (política F.6); el perfil versionado se sigue cargando
    #: para auditar y ya no interviene.
    estado_conversacion: EstadoDeConversacion | None = None
    #: Fase 4 · política F.11 · si esta sesión puede dejar rastro en el perfil
    #: **longitudinal**. Lo resuelve `aviso_legal.permite_escritura_longitudinal()`
    #: en el borde y viaja explícito hasta la escritura: hasta ahora la
    #: protección se sostenía de rebote, porque `identificador_sujeto` llegaba
    #: vacío. Una protección que vive en el valor de una variable no se puede
    #: probar; ésta sí.
    escritura_longitudinal_permitida: bool = True
    #: `DD-27`, 2026-08-18 · la clave de **supresión** (`RD-22`), que NO es la
    #: misma que la de arriba aunque hoy salgan las dos de `sujeto_de(datos)`:
    #: `RL-09` gatea la **inferencia conductual**, no el derecho de supresión.
    #:
    #: Están separadas porque fundirlas tiene una consecuencia concreta y
    #: silenciosa. `identificador_sujeto` queda vacío cuando
    #: `modulo_conductual_habilitado()` es falso (`rutas/turno.py`), y eso hoy
    #: no ocurre en producción solo porque `DD-26` §4 pone la edad por defecto
    #: en 18 dentro del modo piloto y `AGENTE_PILOTO_TESIS` viene encendida en
    #: `compose.produccion.yaml`. **El día que ese interruptor se apague** —que
    #: es lo que `DD-26` §4 planea— un estudiante autenticado archivaría sus
    #: turnos bajo su sesión y no bajo su identidad estable, y una supresión
    #: por sujeto no los alcanzaría. Un interruptor cuyo apagado rompe `RD-22`
    #: sin decirlo es peor que uno decorativo.
    #:
    #: Nunca se gatea. Lo que `RL-09` impide es persistir perfil; lo que no se
    #: persiste sigue sin persistirse, y el turno se registra igual porque
    #: `RF-REG-01` pide registrar **la totalidad** de los turnos.
    identificador_titular: str = ""
    #: `EQ-016`, hito B3 · el evento de consentimiento bajo el que se recoge este
    #: turno. Lo resuelve `rutas/turno.py` con el estado vigente que ya consultó
    #: para autorizar el acceso: preguntarlo dos veces daría dos respuestas si el
    #: consentimiento cambiara entre medias.
    consentimiento_evento: int | None = None
    #: `EQ-031` · para qué se usó el tutor en este turno.
    #:
    #: Como `señales` y `clase`, **lo pone el servidor**: lo deriva
    #: `rutas/turno.py` del rol real de la sesión autenticada. Si el cliente
    #: pudiera declararlo, un estudiante se sacaría del diagnóstico y un
    #: profesional metería sus consultas en los agregados de una clase.
    #:
    #: Viaja hasta el filtro 12, que lo persiste con el turno y con sus dos
    #: voces. Ver `dominio/modelo/contexto_de_uso.py`.
    contexto_de_uso: str = ContextoDeUso.APRENDIZAJE_ESTUDIANTE
    #: `PM-B08` · lo que el estudiante contestó a un ítem de dos niveles, si
    #: este turno responde a uno. `None` en todos los de hoy: **el sistema no
    #: plantea ítems todavía**, y decidir si el flujo conversacional los tendrá
    #: es de producto, no de este adaptador.
    #:
    #: A diferencia de `señales`, esto **sí** viene del cliente — es lo que la
    #: persona eligió—, pero llega en crudo: el identificador de la opción, no
    #: si era correcta ni qué delata. Eso lo resuelve el filtro 6.75 contra el
    #: banco del servidor, de modo que un cliente no pueda diagnosticarse a sí
    #: mismo. Ver `RespuestaAlItem`.
    respuesta_al_item: RespuestaAlItem | None = None
    #: `PM-B28` · lo que la sesión recuerda de los ítems ya planteados. Como
    #: `señales`, **lo pone el servidor**: si el cliente pudiera decir «hace
    #: mucho que no me preguntas», podría pedirse ítems a voluntad y el tope de
    #: frecuencia dejaría de ser del dominio.
    estado_de_sondeo: EstadoDeSondeo | None = None
    #: `PM-B31` · la última expresión que el estudiante escribió en la sesión.
    #: Como `señales`, la pone el servidor: es contexto de conversación, no del
    #: turno, y el turno no puede deducirlo de su propio texto.
    expresion_previa: str = ""
    #: Enunciado matemático explícito recordado por el servidor para verificar
    #: respuestas posteriores sin confundirlas con un ejercicio nuevo.
    ejercicio_activo: dict[str, str] | None = None
    #: `PM-B32` · `D-21` · la notación en la que el estudiante quiere leer lo
    #: que el sistema le escribe. **Ésta SÍ viene del cliente**, como
    #: `respuesta_al_item` y a diferencia de `señales`: es una preferencia de
    #: presentación, no una señal del arbitraje, y un estudiante que la
    #: manipulara solo conseguiría leer su propio desarrollo en otra notación.
    #: Vacía cuando no eligió.
    notacion: str = ""
    #: Los turnos recientes de la sesión para mantener el hilo de la conversación.
    historial_reciente: tuple[dict, ...] = ()
    contexto_conversacional: dict = field(default_factory=dict)
    continuidad: dict | None = None


# ── Lo que sale ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FaseEmitida:
    """§4.1. `fase` es del catálogo cerrado; `texto` lo compone el servidor."""

    fase: str
    texto: str


@dataclass(frozen=True)
class Bloque:
    """§5. El sello tiene exactamente dos valores; no hay un tercero."""

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
    """§6.bis. Del banco de `DD-13`."""

    id: str
    nombre: str


@dataclass(frozen=True)
class ContenidoDelCurso:
    """Lo que el turno lee de `contenido/`, en un solo objeto.

    Dos piezas —el banco de conceptos de `D-28` y el catálogo de fuentes de la
    Fase 5— que se resuelven del árbol al arrancar, no dependen de `AGENTE_BD`
    ni del proveedor, y **faltan juntas**: si no hay `contenido/`, no hay
    ninguna de las dos y el tutor conversa igual.

    Viajan agrupadas y no como dos argumentos sueltos porque el constructor de
    `AdaptadorTurno` ya estaba en el límite de argumentos que `PM-B22` fijó
    para todo el proyecto, y añadir el segundo lo habría pasado. Agrupar dos
    cosas que ya iban juntas es la respuesta a esa métrica; una exclusión por
    archivo sería deuda, no permiso.
    """

    banco: object | None = None
    catalogo: object | None = None


@dataclass(frozen=True)
class MaterialDelTurno:
    """§7.bis · Fase 5 · un fragmento recuperado, tal como se le ofrece al cliente.

    Lleva **título humano** y no sólo el identificador, porque la pantalla lo
    presenta y el encargo pide que `F-*` quede como dato secundario de
    trazabilidad. El título se compone de la obra y la página —que es como se
    cita un pasaje— y no se inventa: los archivos del corpus no declaran título.

    ⚠️ `relacion` es `recuperado` y hoy no puede ser otra cosa. Ver
    `dominio/puertos/registro.py::RELACIONES_DEL_MATERIAL`. La interfaz la usa
    para escribir «Material consultado» y **nunca** «fuente que demuestra esta
    frase».
    """

    id: str
    obra: str
    titulo: str
    relacion: str = "recuperado"


@dataclass(frozen=True)
class Procedencia:
    """§7. `origen` es `corpus` o `sin-fuente`; nunca se improvisa un tercero."""

    origen: str
    referencia: str = ""
    #: Fase 5 · lo mismo que `referencia` resume, en piezas navegables.
    #:
    #: **Convive con la cadena y no la sustituye.** `referencia` es contrato
    #: publicado de `08-Contrato-del-Turno.md` §7 y hay clientes e historial
    #: escritos con ella; quitarla rompería lo que ya funciona. Un cliente que
    #: no conozca `material` sigue mostrando la cadena, exactamente como hoy.
    material: tuple[MaterialDelTurno, ...] = ()


@dataclass(frozen=True)
class RazonOfrecida:
    """§6.quater. Una de las cuatro razones, **con lo que el estudiante ve y
    nada más**.

    No lleva `es_correcta` ni la concepción que delata, y ésa es toda la razón
    de que este tipo exista en vez de emitir `OpcionRazon` tal cual: mandarlos
    resolvería el ítem antes de plantearlo. Es la regla 2 del módulo —la
    separación por rol de `RP-17`— aplicada a un dato nuevo.
    """

    id: str
    texto: str


@dataclass(frozen=True)
class ItemOfrecido:
    """§6.quater. El ítem de dos niveles que este turno plantea (`PM-B28`).

    Va **junto** a la respuesta y no en su lugar: el tutor contesta lo que el
    estudiante escribió y además le ofrece el ítem. Sustituir la respuesta por
    el ítem convertiría el turno en una pregunta de examen, que es lo que
    `RF-GEN-03` prohíbe — y dejaría sin contestar a alguien que preguntó.
    """

    nodo: str
    enunciado: str
    razones: tuple[RazonOfrecida, ...]


@dataclass(frozen=True)
class CuerpoTurno:
    """§4.2."""

    turno: str
    bloques: tuple[Bloque, ...]
    nivel: str
    procedencia: Procedencia
    conceptos: tuple[Concepto, ...] = ()
    #: `PM-B28` · el ítem de dos niveles, cuando este turno plantea uno.
    #: `None` casi siempre: ver `dominio/pedagogia/sondeo.py`, que es donde
    #: está la regla y por qué es así de estrecha.
    sondeo: ItemOfrecido | None = None


@dataclass(frozen=True)
class Degradado:
    """§8.3. Nunca llega contenido matemático sin sello — por eso no lleva
    bloques: si el fallo impidió verificar, el resultado no viaja."""

    ultima_fase: str = ""
    explicacion: str = ""
    # La degradación también pertenece a un turno concreto. Sin esta clave una
    # corrección docente posterior no puede conservar su posición en el hilo.
    turno: str = ""


@dataclass(frozen=True)
class RespuestaTurno:
    """La emisión en dos tiempos. `cuerpo` y `degradado` son excluyentes: uno
    de los dos es `None`, nunca los dos a la vez y nunca ninguno."""

    fases: tuple[FaseEmitida, ...] = ()
    cuerpo: CuerpoTurno | None = None
    degradado: Degradado | None = None
    #: Fase 4 · el estado pedagógico **tras** este turno, listo para que el
    #: borde lo guarde en la sesión. Lo cierra el adaptador y no la ruta porque
    #: tres de los cinco hechos del episodio —el veredicto del motor, la
    #: estrategia aplicada y la intención resuelta— sólo existen aquí dentro.
    #:
    #: `None` cuando el turno degradó antes de resolver la intención: entonces
    #: no hay nada que observar y el estado se queda como estaba, que es lo
    #: correcto — un turno que falló no es un intento del estudiante.
    estado_conversacion: EstadoDeConversacion | None = None
    #: `R2-B` · qué hizo el servidor con la respuesta al ítem, para que el borde
    #: HTTP sepa si puede cerrarlo. Lo produce el filtro 6.75 dentro de la
    #: cadena y esto sólo lo transporta: es el mismo camino y el mismo motivo
    #: que `estado_conversacion`.
    #:
    #: 🔴 El borde **no** puede deducirlo de `entrante.respuesta_al_item`. Ese
    #: campo es lo que el cliente mandó; que llegara no dice que se admitiera.
    desenlace_del_sondeo: DesenlaceDelSondeo = field(default_factory=DesenlaceDelSondeo)
    #: Fase 8 · el nombre del modelo que **respondió de verdad**, tal como lo
    #: devolvió el proveedor. Sale de `ctx.generacion.modelo`, que el filtro de
    #: generación rellena desde la respuesta y no desde la configuración: son
    #: distintos en cuanto el proveedor sirve un alias o sustituye el modelo, y
    #: el encargo pide precisamente «la versión de modelo realmente respondida».
    #:
    #: Viaja aquí y no en las fases porque `FaseEmitida` sólo lleva `fase` y
    #: `texto` —es lo que ve el estudiante— y ensancharla habría metido un dato
    #: de operación en el contrato del turno. Este campo **no se serializa** en
    #: la respuesta HTTP: lo consume la instrumentación del backend.
    version_modelo: str = ""
    # Solo para el borde del servidor; nunca se serializa en el cuerpo HTTP.
    trazas_contexto: tuple[dict, ...] = ()
    continuidad: dict | None = None


# ── El adaptador ───────────────────────────────────────────────────────────


class AdaptadorTurno:
    """Implementa la ruta del turno contra una cadena ya construida.

    Recibe el `Orquestador` por inyección — igual que cada filtro recibe su
    puerto —: este adaptador no arma la cadena ni sabe qué proveedor hay
    detrás de cada uno. Eso es del compositor del sistema, que todavía no
    existe porque `adaptadores/entrantes/` no tenía nada que componer antes
    de esta sesión.
    """

    def __init__(  # noqa: PLR0913 — dependencias explícitas y opción de contexto del servidor
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
        # Inyectable para que las pruebas no dependan de un UUID al azar.
        self._generador_de_id = generador_de_id or (lambda: uuid.uuid4().hex)
        #: `RF-REG-01`, 2026-08-18 · quién sella la marca temporal del turno.
        #: Inyectable por el mismo motivo que el generador de identificadores:
        #: una prueba no puede depender del reloj de pared.
        #:
        #: **UTC y con zona explícita.** `EntradaDeTurno.validar()` rechaza una
        #: marca sin zona, y con razón: de ella cuelgan el orden del historial
        #: y el plazo de retención de `C-01`, y una hora sin zona es una hora
        #: que alguien tendrá que adivinar.
        self._reloj = reloj or (
            lambda: datetime.now(UTC).isoformat(timespec="milliseconds")
        )
        # `PM-B10`/`PM-B11`, enganchados el 2026-08-12. `None` sin `AGENTE_BD`
        # — ver la cabecera del módulo.
        self._adaptador_perfil = adaptador_perfil
        # `PM-B28`. `None` sin `contenido/`: entonces no hay ítems que plantear
        # y el tutor conversa en texto libre, exactamente como antes.
        self._plantillas = plantillas
        #: Lo que se lee de `contenido/`: el banco de conceptos de `D-28` y el
        #: catálogo de fuentes de la Fase 5. `None` es un estado normal —sin
        #: `contenido/` el tutor conversa y el panel va vacío, igual que pasa
        #: con `plantillas`— y por eso los dos viajan juntos: se resuelven a la
        #: vez, faltan a la vez y se prueban a la vez.
        self._contenido = contenido or ContenidoDelCurso()
        self.contexto_reforzado = contexto_reforzado

    def manejar_con_progreso(self, entrante: TurnoEntrante, al_iniciar) -> RespuestaTurno:
        return self.manejar(entrante, al_iniciar=al_iniciar)

    def manejar(self, entrante: TurnoEntrante, *, al_iniciar=None) -> RespuestaTurno:
        # `PM-V15` · el identificador se genera ANTES de la cadena y no después.
        # Hasta el 2026-08-14 se generaba en `_cuerpo()`, ya con el turno
        # resuelto, así que el dominio nunca lo veía y el filtro 12 registraba
        # por sesión — pisándose a sí mismo. Generarlo aquí hace además que el
        # `turno` que el estudiante recibe y el del registro sean **el mismo**,
        # sin lo cual un turno reportado no se puede encontrar.
        turno_id = self._generador_de_id()
        ctx = ContextoTurno(
            texto_estudiante=entrante.mensaje,
            identificador_sesion=entrante.sesion,
            identificador_turno=turno_id,
            # `DD-27`, 2026-08-18 · deja de viajar SOLO por fuera del contexto.
            # Hasta hoy el sujeto se pasaba aparte a `_registrar_en_frio(...)`
            # y el filtro 12 —que solo recibe `ctx`— no podía verlo, así que el
            # registro no se podía clavar al identificador que sobrevive a
            # cerrar el navegador.
            #
            # Sale de `identificador_titular` y **no** de `identificador_
            # sujeto`: el segundo lo gatea `RL-09` y quedaría vacío con el
            # módulo conductual apagado. Ver el campo en `TurnoEntrante`.
            identificador_sujeto=entrante.identificador_titular,
            # `EQ-016`, hito B3 · viaja hasta el filtro 12, que lo copia a las
            # dos voces del turno.
            consentimiento_evento=entrante.consentimiento_evento,
            # `RF-REG-01` · la marca la sella el SERVIDOR. `entrante.momento`
            # viene del cuerpo de la petición y NO se usa: ver el campo en
            # `ContextoTurno`.
            momento=self._reloj(),
            señales=entrante.señales,
            clase=entrante.clase,
            # `EQ-031` · viaja hasta el filtro 12, igual que
            # `consentimiento_evento`. El dominio no lo deriva ni lo corrige.
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
            # Se sigue cargando, y ya **no decide**: la política F.6 lo deja
            # disponible para auditoría. Ver `dominio/filtros/deteccion.py`.
            perfil_previo=self._cargar_perfil(entrante.identificador_sujeto),
            respuesta_al_item=entrante.respuesta_al_item,
            # `RC-PED-06` · qué ítems planteó ESTA sesión. El filtro 6.75 lo
            # necesita para no clasificar una respuesta a un ítem que nunca se
            # ofreció; el 6.8, para respetar el tope de frecuencia.
            sondeos_ofrecidos=(
                entrante.estado_de_sondeo.ofrecidos if entrante.estado_de_sondeo else ()
            ),
            # Paquete H · y cuáles ya contestó, para no diagnosticar dos veces
            # el mismo ítem ni admitir el de una pestaña obsoleta.
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
            # `08-Contrato-del-Turno.md` §8.3: degradación segura y explícita,
            # con la última fase alcanzada cuando la hay. `exc.ctx_parcial` es
            # el turno tal como quedó justo antes del filtro que lanzó —lo
            # que `Orquestador.ejecutar` conserva desde el 2026-08-08—, así
            # que sus trazas sí existen y de ahí sale `ultima_fase`.
            # `T-04`, 2026-08-18 · UNA definición de la explicación, usada
            # dos veces: la que el estudiante ve y la que entra al historial.
            # Antes se construía solo aquí abajo, DESPUÉS de registrar en
            # frío, así que el filtro 12 no podía saber que el turno se había
            # degradado.
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
        # `PM-B28` · el ítem se decide DESPUÉS de que la respuesta esté hecha,
        # y es lo que lo mantiene siendo un añadido y no una alternativa: nada
        # de lo que el tutor contestó depende de si además se plantea uno.
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
        # `PM-B20`: después de construir la respuesta, nunca antes — es lo
        # que hace que el filtro 12 sea de verdad ruta fría y no solo lo
        # declare `Filtro.ruta`.
        #
        # `PM-B25`: y con el cuerpo YA construido dentro del contexto, para que
        # el historial guarde lo que el estudiante vio y no solo lo que se
        # narró. El orden importa: `_cuerpo()` tiene que haber corrido.
        self._registrar_en_frio(
            entrante.identificador_sujeto,
            _como_registro(salida, cuerpo),
            entrante.escritura_longitudinal_permitida,
        )
        return respuesta

    def _cargar_perfil(self, identificador_sujeto: str):
        """`ctx.perfil_previo` de verdad, o `None` si no hay con qué cargarlo.

        Sin `adaptador_perfil` (sin `AGENTE_BD`) o sin sujeto —lo que hoy
        significa que `RL-09` deshabilitó el módulo conductual, no que la sesión
        sea anónima: `EQ-020` retiró el anonimato en el hito B1—, el filtro 3
        sigue corriendo: solo que parte del estado en blanco que ya tenía por
        defecto, la misma degradación explícita que el resto de la composición
        aplica.
        """
        if self._adaptador_perfil is None or not identificador_sujeto:
            return None
        try:
            return self._adaptador_perfil.reconstruir_perfil(identificador_sujeto)
        except Exception:  # noqa: BLE001 — cargar perfil no puede tumbar el turno
            return None

    def _registrar_en_frio(
        self, identificador_sujeto: str, ctx: ContextoTurno, permitida: bool = True
    ) -> None:
        """Guarda las entradas de auditoría del filtro 3 y corre la ruta fría.

        Las dos cosas comparten sitio porque comparten regla: ninguna puede
        tumbar una respuesta que ya se construyó (o que ya se degradó de
        forma explícita). `Orquestador.ejecutar_fria` ya envuelve el fallo de
        cada filtro frío en `ErrorDeOrquestacion`; aquí se atrapa también eso,
        porque para cuando se llega aquí el turno del estudiante ya está
        decidido — es lo que el propio `dominio/filtros/registro.py` deja
        escrito que le corresponde a quien compone el sistema decidir.

        `A4`, 2026-08-18 · no tumbar el turno NO es lo mismo que no contarlo
        ------------------------------------------------------------------------
        Hasta hoy las dos operaciones iban dentro de `contextlib.suppress
        (Exception)`, así que un rechazo de la base **no lo decía nadie**: ni
        el estudiante, ni el log, ni `GET /api/salud`. Eso choca con
        `CONTEXTO-MAESTRO.md` §5.1, *cero modo mock silencioso*.

        Lo que se conserva es que el turno no se caiga; lo que se corrige es
        que el fallo sea invisible. `logging.exception` deja el rastro completo
        **con el identificador del turno**, para que sea rastreable hasta el
        turno concreto y no solo hasta «algo falló alguna vez».

        La regla, para lo que venga: **la ruta fría puede fallar en silencio
        para el estudiante, nunca para quien opera el sistema.**

        ⚠️ Lo que esto NO cubre, y `A4.bis` sí: una base que acepta la conexión
        y no responde. Ahí no hay excepción que registrar — hay una espera. Ver
        `PM-B38`.
        """
        if self._adaptador_perfil is not None and identificador_sujeto and permitida:
            try:
                self._guardar_perfil(identificador_sujeto, ctx)
            except Exception:  # noqa: BLE001 — la respuesta ya se emitió
                _registro.exception(
                    "no se pudo guardar el perfil del turno %s (sesión %s)",
                    ctx.identificador_turno or "sin identificador",
                    ctx.identificador_sesion or "sin sesión",
                )
        try:
            self._orquestador.ejecutar_fria(ctx)
        except Exception:  # noqa: BLE001 — la respuesta ya se emitió
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


# ── Traducción · fases ─────────────────────────────────────────────────────


def _trazas_para_contexto(ctx: ContextoTurno) -> tuple[dict, ...]:
    nombres = {"clasificación de intención", "verificación del intento del estudiante",
               "verificación simbólica"}
    return tuple(asdict(t) for t in ctx.trazas if t.filtro in nombres)


def _modelo_que_respondio(ctx: ContextoTurno) -> str:
    """El modelo que el proveedor dice haber usado, o cadena vacía.

    Cadena vacía y no un valor por defecto: si el turno degradó antes de
    llamar al proveedor, no respondió ningún modelo, y escribir aquí el que la
    configuración pide afirmaría algo que no ocurrió. El catálogo KPI trata la
    cadena vacía como «no consta», que es exactamente lo que pasó.
    """
    return getattr(ctx.generacion, "modelo", "") or ""


def _fases_desde_trazas(trazas: Sequence[TrazaFiltro]) -> tuple[FaseEmitida, ...]:
    fases: list[FaseEmitida] = []
    for t in trazas:
        if t.metadatos.get("omitido"):
            continue          # la compuerta del filtro 4 lo saltó; no hubo fase
        fase_id = _FASE_POR_FILTRO.get(t.filtro)
        if fase_id is None:
            continue          # trabajo interno sin fase propia (§4.1)
        fases.append(FaseEmitida(fase=fase_id, texto=_TEXTO_DE_FASE[fase_id]))
    return tuple(fases)


# ── Traducción · cuerpo y bloques ───────────────────────────────────────────


def _como_registro(ctx: ContextoTurno, cuerpo: CuerpoTurno) -> ContextoTurno:
    """El cuerpo emitido, traducido a tipos del puerto y puesto en el contexto.

    `PM-B25`, 2026-08-18. El historial guardaba `ctx.respuesta` —la narración
    cruda, con sus marcas `{{c1}}` sin resolver y sin decir qué bloque se había
    verificado—. Esto es lo que el estudiante vio de verdad.

    **Traduce, no recalcula.** Los bloques y su sello los decidió `_cuerpo()`
    tres líneas más arriba; volver a derivarlos en el dominio daría dos
    implementaciones de la misma cuenta, que es como este proyecto acabó con
    dos recuentos de archivos del frontend que no coincidían.

    Va aquí y no en el filtro 12 porque separar la narración es del borde
    —`08-Contrato-del-Turno.md` §5— y el dominio no debe conocer `Bloque`.
    """
    return dataclasses_replace(
        ctx,
        # El verificador puede sustituir la estructura por una corrección
        # comprobada. Sus bloques y citas pertenecen a esa narración final;
        # conservar el texto anterior deja marcas huérfanas y pierde el turno.
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
            # `ExpresionCitada` lo llama `identificador`; aquí es `marca`,
            # que es como aparece dentro del texto. Un solo sitio traduce el
            # nombre, para que la discrepancia no se propague.
            *(
                CitaRegistrada(marca=c.identificador, expresion=c.expresion)
                for c in (
                    ctx.respuesta_generada.citadas
                    if ctx.respuesta_generada is not None
                    else ()
                )
            ),
            # 🔴 **Y las AFIRMACIONES, que faltaban.** `PM-B25` añadió los
            # bloques y las citadas para que `validar()` no rechazara una
            # narración con marcas, pero la narración cita las dos clases:
            # `{{c1}}` para lo que nombra y `{{a1}}` para lo que afirma. Con
            # sólo las primeras, **cualquier turno de nivel 2 o 3 no se
            # registraba**: `_fallos_de_las_marcas()` veía `a1` sin cita y la
            # entrada se rechazaba entera.
            #
            # No se notaba porque hasta la fase 4 el sistema operaba siempre en
            # nivel 1 —lo declaraba `composicion.py`—, así que ninguna
            # narración llevaba afirmaciones. Con la escala de `RF-GEN-05`
            # funcionando y `DEC-R3` abriendo el nivel 2 a las peticiones de
            # teoría, es el caso normal.
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

    # ⚠️ LO QUE DECIDE ESTO NO ES SI SE SEPARA, ES SI SE PUEDE SELLAR COMO
    # VERIFICADO. La narración SIEMPRE se separa por sus referencias, también en
    # el piso seguro. Hasta el 2026-08-11 el piso emitía `ctx.respuesta` tal
    # cual, y como su condición es `nivel_divulgacion == 1` —el caso normal
    # mientras el arbitraje no suba— el estudiante veía en pantalla la marca
    # cruda: «Fíjate en {{c1}}: tienes una función compuesta». Es `PM-B25`, y se
    # vio en la primera pantalla real, no en una prueba.
    #
    # Separar en el piso es seguro **porque en el piso no hay afirmaciones**:
    # `C4` rechaza el nivel 1 con afirmaciones y `podada()` las retira al
    # descender, así que lo único que queda por resolver son expresiones
    # citadas, cuyo sello es `generado` (§5.4: una expresión suelta no puede ser
    # verdadera ni falsa). El nivel sondeo sigue sin llevar un solo bloque
    # `verificado`, que es lo que §6 exige.
    verificable = ctx.nivel_divulgacion > 1 and aprobada

    if ctx.respuesta_generada is None:
        # Sin estructura no hay nada que separar: es el turno cuyo generador
        # ignoró el formato (`R-21`) y aquí no se inventa la que no vino.
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
    """El estado pedagógico tras el turno, o `None` si no hay nada que observar.

    Se llama **después** de la cadena, y esa posición es la decisión: tres de
    los cinco hechos del episodio —el veredicto del motor, la estrategia
    aplicada y la intención resuelta— no existen antes. La consecuencia, dicha:
    el `ciclo_negativo` que el turno *N* usa para decidir es el de los episodios
    *1..N-1*. Un ciclo es, por definición, algo que ya venía pasando.

    `None` cuando el turno degradó antes de que el filtro 2 resolviera la
    intención: sin ella no se puede decir si el estudiante propuso, pidió o
    saludó, y **contar a ciegas es peor que no contar**. El estado se queda como
    estaba, que es lo correcto: un turno que falló no es un intento suyo.
    """
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
            # Paquete E · el modelo del problema tiene que distinguir lo que el
            # estudiante escribió de lo que el filtro 1 heredó (`PM-B31`).
            expresiones_heredadas=ctx.expresiones_heredadas,
            nodo=ctx.nodo_activo,
            # 🐛 `R2-B` · aquí se leía `ctx.respuesta_al_item.nodo` **en crudo**,
            # así que un `dos_niveles` que el servidor había RECHAZADO pasaba a
            # ser la identidad del problema activo: `unidad_de()` da precedencia
            # al ítem, la identidad cambiaba y los contadores se reiniciaban.
            # Reproducido: dos intentos legítimos sobre `cos(x)^3` y un payload
            # forjado para `N08` dejaban el problema en `item:N08` con
            # `intentos=0`. Eso es apagar la escala de `RF-GEN-05` desde el
            # cliente. Ahora manda el desenlace, que es lo que el servidor
            # decidió; ver `DesenlaceDelSondeo.admitida`.
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
        # El afectivo lo actualizó el filtro 3 dentro de la cadena.
        afectivo=(ctx.estado_conversacion or estado).afectivo,
        problema=problema,
        # La preferencia **no se apaga ni se enciende sola**: las dos son actos
        # del estudiante. Paquete F · antes esto era un `or`, así que una vez
        # puesta no había forma de retirarla; la orden explícita de volver a
        # adaptar es la que la apaga, y ninguna otra cosa.
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
    """Separa la narración en prosa y notación por cada `{{id}}` citado.

    `ADR-014` C2 ya garantiza —lo comprobó el filtro 9— que toda referencia
    corresponde a una afirmación declarada, así que aquí no hace falta volver
    a defenderse de una referencia huérfana.

    `verificable` dice si esta respuesta ganó el derecho a sellar `verificado`:
    hace falta que el motor la aprobara **y** que el arbitraje pasara del
    sondeo. Cuando es falso, una afirmación no se calla —callarla dejaría la
    frase sin aquello de lo que habla— pero **sale con el sello que le
    corresponde**, `generado`, que es exactamente lo que `RP-01` pide que se
    marque por bloque. No es una vía para emitir sin verificar: es la marca
    diciendo que no se verificó.
    """
    por_id = {a.identificador: a for a in respuesta.afirmaciones}
    citadas = {c.identificador: c for c in respuesta.citadas}
    partes = _PATRON_REFERENCIA.split(respuesta.narracion)

    bloques: list[Bloque] = []
    for i, parte in enumerate(partes):
        if i % 2 == 0:
            # ⚠️ SE CONSERVAN LOS ESPACIOS DE ALREDEDOR, y no es descuido de
            # limpieza. La narración dice «Fíjate en {{c1}}: es una
            # composición», así que el espacio va ANTES de la expresión y el
            # dos puntos va pegado DESPUÉS. Recortando cada trozo, la interfaz
            # los junta con su propio criterio y sale «sen(x^2) : es una» —
            # espacio antes del signo, que en español está mal. La puntuación
            # es del texto, no del que lo pinta. El recorte de los extremos se
            # hace una vez al final, sobre el conjunto.
            if parte.strip():
                bloques.append(Bloque(tipo="prosa", contenido=parte, sello="generado"))
            continue

        # `ADR-014` §5.4 · una expresión que solo se menciona se renderiza y
        # **no se verifica**, porque una expresión suelta no puede ser
        # verdadera ni falsa. Su sello es `generado`, que es lo honesto: el
        # sistema no ha comprobado nada sobre ella porque no había nada que
        # comprobar. Es el tipo que `08-Contrato-del-Turno.md` §5 declara y que
        # hasta hoy nadie emitía.
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
    """Recorta el primer y el último bloque de prosa, y solo ésos.

    Lo de en medio se conserva tal cual porque ahí el espacio significa algo
    —separa la frase de la expresión que nombra—. En los extremos no separa de
    nada y solo desplaza el texto.
    """
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
    """El mismo cuerpo, con el ítem de dos niveles si en este turno toca.

    🔴 **Fase 4 · aquí ya no se decide, se traduce.** La decisión vive en el
    filtro 6.8 (`dominio/filtros/sondeo.py`) porque el prompt necesita saberla:
    si el turno plantea un ítem, la respuesta del tutor no debe además
    preguntar. Lo que queda aquí es lo que siempre fue traducción de borde:
    quitar del ítem lo que no puede cruzar al estudiante. Ver `RazonOfrecida`.
    """
    item = ctx.item_ofrecido
    if item is None:
        return cuerpo

    return dataclasses_replace(
        cuerpo,
        sondeo=ItemOfrecido(
            nodo=item.nodo,
            enunciado=item.enunciado,
            # Solo identificador y texto. `es_correcta` y `concepcion` se
            # quedan en el servidor — ver `RazonOfrecida`.
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
    """Lee una función con cualquier letra, o y=…, sin la prosa posterior."""
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
    """Conserva el nombre explícito de la curva, incluida una petición posterior."""
    from dominio.modelo.notacion_entrada import normalizar_escritura_matematica
    textos = [ctx.texto_estudiante, *(str(t.get("estudiante", "")) for t in reversed(ctx.historial_reciente))]
    for texto in textos:
        normalizado = normalizar_escritura_matematica(texto)
        for letra in re.findall(r"\b([a-zA-Z])\s*(?:\\left\s*)?\(\s*x\s*(?:\\right\s*)?\)\s*=", normalizado):
            if _funcion_declarada(texto, letra) == fuente:
                return letra
    return "f"


def _formula_para_grafica(texto: str) -> str:
    """Una fórmula explícita del mensaje, sin convertir x=1 en una curva."""
    from dominio.filtros.normalizacion import segmentar
    from dominio.modelo.notacion_entrada import normalizar_escritura_matematica

    for expresion in segmentar(normalizar_escritura_matematica(texto))[0]:
        formula = expresion.strip().rstrip(".,; ")
        if "x" in formula.lower() and not re.fullmatch(r"x\s*=\s*[-+]?\d+(?:[.,]\d+)?", formula, re.I):
            return formula
    return ""


def _principal_del_historial(ctx: ContextoTurno) -> str:
    """Conserva la curva f de la conversación al añadir una g temporal."""
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
    """El bloque `grafica` de `PM-B26`, si este turno tiene algo que dibujar.

    `08-Contrato-del-Turno.md` §12: el servidor lo emite siempre que aplica;
    el cliente decide si lo pinta (`DD-14`). «Siempre que aplica» es: hay un
    precómputo válido y el adaptador simbólico consiguió describir la función
    original en JavaScript. Un límite dibuja esa función, no «la curva del
    límite»; el destino se añade como referencia, sin afirmar f(a)=límite.

    El contenido de la función original va siempre que exista: no afirma
    nada sobre la derivada, es igual que una `expresion-citada` (§5.4), así
    que no hay nada que el nivel `sondeo` tenga que ocultar. La derivada
    **sí** es la respuesta, así que solo viaja cuando `verificable` —el
    mismo criterio que ya decide si una `notacion` sella `verificado`— es
    verdadero; si no, el bloque igual se emite, con la función y sin ella.
    """
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
    # «Los tres» después de comparar x/x, x²/x y x/x² requiere tres curvas,
    # aunque el último mensaje no vuelva a escribir ninguna de ellas.
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
        # g no significa por sí sola «añadir otra curva». Una petición directa
        # debe dibujar su propia función, aunque antes se estuviera estudiando f.
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
        # «Muéstrame esa», «solo gráfica» y «vuelve a dibujarla» usan la
        # función activa o la última principal sin pedir que la reescriban.
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
    # Conservar un ejercicio entre turnos permite verificar «me da ...», pero
    # no significa adjuntar su gráfica en cada respuesta o rango de tabla.
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
        # Hay funciones graficables cuyo desarrollo simbólico de la derivada
        # no es útil o no está soportado (por ejemplo, Piecewise). La petición
        # de representación sigue pudiendo satisfacerse con la función
        # original, sin presentar una derivada ni una solución inventada.
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

    # El rótulo procede del mismo insumo que produjo ambas cadenas ejecutables.
    # Reconstruirlo desde `ctx.expresiones` podía mentir cuando el precómputo
    # había usado `expresion_previa` o el contexto ya contenía otra extracción.
    expresion = precomputo.expresion_fuente or (
        ctx.expresiones[0] if ctx.expresiones else "la función de este turno"
    )
    if not ctx.es_limite and "x" not in expresion:
        return None
    contenido: dict[str, str] = {
        "funcion_js": precomputo.funcion_js,
        # Texto matemático para presentación. `funcion_js` sigue siendo la
        # única entrada ejecutable del trazador; esta copia evita reconstruir
        # notación humana a partir de JavaScript en el navegador.
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
    """§7 · de dónde salió el material de este turno.

    Fase 5 añade `material`: las mismas piezas que la cadena resume, cada una
    con su obra y un título legible. El título lo compone el catálogo cuando
    está disponible; **sin catálogo el turno no falla** —igual que sin banco de
    conceptos— y las piezas viajan con el identificador por título, que es peor
    de leer pero cierto.
    """
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
    """Un rótulo legible para un fragmento recuperado.

    Se pide al catálogo, que es quien conoce la ficha de la obra. Si no está
    compuesto —o si la obra salió del catálogo desde que se escribió el
    fragmento— se cae al identificador. **No se inventa un título**: los
    archivos del corpus no declaran ninguno.
    """
    if catalogo is None:
        return fragmento.identificador
    try:
        return catalogo.titulo_de_fragmento(fragmento.identificador)
    except Exception:  # noqa: BLE001 — el turno no se rompe por un rótulo
        return fragmento.identificador


def _conceptos_invocados(recuperacion, banco) -> tuple[Concepto, ...]:
    """§6.bis · las páginas del banco ancladas en el material que ESTE turno
    citó · `D-28`.

    Del NODO del material, nunca del diagnóstico: `D-28` descarta por escrito
    alimentar esto con `ctx.diagnostico.concepcion`, y el motivo no es de
    contenido sino de puerta — este panel lo abre el sistema y además acumula
    toda la conversación, así que una concepción diagnosticada quedaría a la
    vista del estudiante turno tras turno. `RP-18` lo prohíbe.

    Sin corpus utilizable va vacío, por el mismo criterio con que
    `_procedencia()` declara `sin-fuente`: un turno sin material no invocó nada.

    ⛔ SIN TOPE Y SIN ORDENAR POR RELEVANCIA. `D-28` §2: recortar sería decidir
    qué concepto importa, y §6.bis se lo prohíbe al servidor con las mismas
    palabras que al cliente. El orden es el de aparición del material.

    Es la pareja de `_procedencia()` —las dos leen `ctx.recuperacion` y las dos
    son traducción de borde— y por eso vive pegada a ella.
    """
    # `banco=None` tiene que funcionar, igual que `plantillas`: sin `contenido/`
    # el tutor conversa y no hay panel, exactamente como hasta hoy.
    if banco is None or recuperacion is None or not recuperacion.utilizable:
        return ()

    # Los nodos del material citado, en orden de aparición y sin repetir. Un
    # fragmento sin nodo no aporta ninguno; no es un fallo.
    nodos: list[str] = []
    for fragmento in recuperacion.fragmentos:
        nodo = getattr(fragmento, "nodo_grafo", None)
        if nodo and nodo not in nodos:
            nodos.append(nodo)

    invocados: dict[str, Concepto] = {}
    for nodo in nodos:
        for pagina in banco.por_nodo(nodo):
            # Dedup por identificador conservando el primero: una página anclada
            # en dos nodos citados aparece una vez, donde apareció antes.
            invocados.setdefault(pagina.identificador, Concepto(
                id=pagina.identificador,
                nombre=pagina.nombre,
            ))
    return tuple(invocados.values())
