"""
sondeo.py — Cuándo el tutor plantea un ítem de dos niveles (`PM-B28` · `D-19`)
==============================================================================

`RC-PED-06` y `RF-DGC-01` piden que el tutor **pregunte** de vez en cuando con
un ítem de dos turnos —resultado primero, razón después— en vez de conversar
solo en texto libre. `D-19` cerró que se construye; lo que dejó abierto a
propósito son las tres preguntas que este módulo responde, **y las tres son
decisiones de esta sesión, no del documento**:

1. cuándo se ofrece,
2. cada cuánto como máximo,
3. qué pasa si el estudiante lo ignora.

Vive aparte de `andamiaje.py` porque son dos reglas distintas —aquélla decide
**qué preguntas se le sugieren al generador**, ésta decide **si además se le
plantea un ítem estructurado**— y aparte del adaptador porque es pedagogía:
quien quiera revisar el criterio lee esta tabla y ningún archivo más.

1 · Cuándo se ofrece
-----------------------
| Condición | Por qué |
|---|---|
| Hay ítem **ofrecible** para el nodo del turno | Sin las cuatro razones escritas no hay ítem que plantear. El banco actual escribe `N08`, `N14` y `N05`; los tres siguen pendientes de revisión docente. |
| El turno **trae una expresión** y la intención **no es emocional** | `p-two-tier.md` §Cuándo se activa: *«preferentemente en ítems de nivel de aplicación»*, que es donde `RF-DGC-02` sitúa la evidencia sólida — *«en ítems de comprensión el efecto medido no es significativo»*. Un turno con matemática segmentada dentro **es** ese nivel |
| Hay **al menos dos intentos** en el problema activo (`DEC-R2`) | La duda tiene que estar sostenida. Se reutiliza el umbral que `RF-GEN-05` ya usa para decir «esto dejó de ser un tropiezo» en vez de inventar uno nuevo |

⚠️ **Por qué la segunda fila mira la expresión y no «intención procedimental»,
y lo corrigió una medición.** La primera versión de esta regla, escrita el
mismo día, exigía `intencion == "procedimental"`. Al correrla contra el sistema
real **no se ofreció ni un ítem**: el filtro 2 clasifica `ambigua` con mucha
frecuencia, también en turnos que sí están resolviendo un ejercicio. Y el
proyecto ya tiene decidido qué hacer con eso — `ADR-007` I3: ante `ambigua`
**se actúa**, que es lo que hace la compuerta del filtro 4 con la recuperación.
Exigir `procedimental` era inventar una postura propia para un caso que ya
estaba resuelto en otro sitio. Lo que se descarta es `emocional`, que es la
única clase en la que preguntar por una derivada sería impertinente.

⚠️ **Y por qué NO basta con el contador de intentos.** `PM-V15` midió el
2026-08-14 que `contabilizar()` cuenta de más: tres mensajes cualesquiera
—«hola», «gracias», «vale, entendido»— llevan el arbitraje a nivel 3. Si esta
regla mirara solo el contador, el tutor plantearía un ítem de cálculo
diferencial después de dos saludos. Lo impide **exigir expresión**, y por eso
esa condición va antes que el contador y no después: ninguno de esos tres
mensajes trae una. Arreglar `contabilizar()` es otra tarea y otra decisión;
esta regla no depende de que se arregle.

2 · Cada cuánto como máximo · la regla que gobierna todo esto
-------------------------------------------------------------------
**Es un tutor, no un examen.** `p-two-tier.md` §Cuándo se activa lo dice con
todas las letras: *«no se activa dos veces seguidas. Un formato de opción
múltiple repetido deja de medir razones y empieza a medir paciencia»*, y
`RF-GEN-03` prohíbe que la conversación se convierta en evaluación.

Dos topes, y son distintos:

- **`_TURNOS_ENTRE_SONDEOS = 3`.** El contenido pide «no dos veces seguidas»,
  que sería 2. Se pone 3 porque con 2 el estudiante vería un ítem cada dos
  turnos —un tercio de la conversación— y eso ya se parece a un cuestionario.
  Con 3, el ítem es un episodio dentro de una conversación y no su ritmo.
- **Un nodo, una vez por sesión.** Repetir el mismo ítem no mide nada nuevo:
  las cuatro razones ya no son cuatro, son las mismas de antes con la respuesta
  sabida. Es el mismo motivo por el que `DD-25` congela un banco antes de medir.

3 · Qué pasa si el estudiante lo ignora · **nada, y es deliberado**
--------------------------------------------------------------------------
Sigue escribiendo texto libre y la conversación continúa igual. **No se
reintenta, no se insiste y no se queda nada esperando.** Un tutor que repite la
pregunta hasta que le contesten deja de ser un tutor, y `RF-GEN-04` ya fija esa
postura para la dirección contraria —insistir no consigue nada—; sería
incoherente que el sistema sí pudiera insistir.

El tope de frecuencia hace el resto solo: como el contador de turnos corre
igual se le haya contestado o no, ignorar un ítem **aleja** el siguiente en vez
de acercarlo. No hace falta un mecanismo de reintento porque no hay reintento.

Y por eso el estado que esta regla necesita es **de la sesión y no del ítem**:
no se guarda «hay un ítem pendiente» —que obligaría a resolver qué hacer con lo
pendiente— sino «cuándo fue el último y de qué nodos». Un ítem contestado tres
turnos después se clasifica igual: el servidor lo valida contra el banco, no
contra una expectativa.


"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from dominio.puertos.plantillas import ItemDosNiveles

#: Cuántos turnos tienen que pasar entre dos ítems. Ver §2 de la cabecera.
_TURNOS_ENTRE_SONDEOS = 3

#: Cuántos intentos hacen falta para que la duda cuente como sostenida. Es el
#: mismo umbral con el que `RF-GEN-05` escala a nivel 2, y se reutiliza a
#: propósito: dos criterios de «esto ya no es un tropiezo» que pudieran
#: discrepar serían dos ideas distintas del mismo estudiante.
_INTENTOS_MINIMOS = 2


@dataclass(frozen=True)
class ItemOfrecido:
    """Un ítem que **esta sesión** llegó a plantear, y con qué opciones.

    🔴 **Fase 4.** Hasta aquí la sesión recordaba sólo el nodo, y con eso se
    respetaba el tope de frecuencia pero **no se podía validar la respuesta**:
    el servidor clasificaba cualquier `(nodo, resultado, razón)` que llegara,
    aunque el ítem no se hubiera planteado nunca en esa conversación. Un
    cliente podía provocar un diagnóstico sobre un nodo que jamás vio.

    Se guardan los identificadores de las razones **tal como se emitieron**,
    para poder comprobar que la que vuelve es una de ellas y no una inventada
    ni una de otro ítem. El texto no hace falta: lo que se valida es la
    correspondencia, no el contenido.
    """

    nodo: str
    razones: tuple[str, ...] = ()


@dataclass(frozen=True)
class Veredicto:
    """Si una respuesta a un ítem se admite, y por qué no cuando no.

    El motivo va siempre. Un rechazo sin motivo no permite distinguir un
    cliente manipulado de un ítem que se retiró del contenido, y las dos cosas
    se atienden distinto.
    """

    admitida: bool
    motivo: str = ""


def validar_respuesta(
    respuesta,
    item,
    ofrecidos: tuple[ItemOfrecido, ...],
    contestados: tuple[str, ...] = (),
) -> Veredicto:
    """Si el servidor puede clasificar esta respuesta. Seis comprobaciones.

    Ninguna mira si acertó: eso es el diagnóstico y va después. Aquí sólo se
    decide si **hay ítem que corregir**, y el orden va de lo más barato a lo
    más caro.

    | Comprobación | Qué impide |
    |---|---|
    | el ítem existe y es utilizable | clasificar contra un ítem que el contenido no trae |
    | **se ofreció en esta sesión** | provocar un diagnóstico sobre un nodo que el estudiante nunca vio |
    | **es el ítem vigente** | que un cliente obsoleto conteste el de hace cinco turnos |
    | **no se contestó ya** | un segundo diagnóstico sobre las mismas razones, ya sabidas |
    | la razón es de las que se emitieron | responder con la razón de otro ítem, o con una inventada |
    | el resultado no viene vacío | corregir una cadena vacía como si fuera una propuesta |

    🔴 **Las dos del medio son del paquete H.** «Se ofreció en esta sesión» no
    bastaba cuando la sesión había ofrecido más de uno: una pestaña vieja o un
    reintento que se quedó con el ítem anterior podían provocar un diagnóstico
    sobre un ejercicio que ya no estaba en pantalla.

    **Contestarlo tarde sigue valiendo**, y eso no cambia: `§3` de la cabecera
    decidió que ignorar un ítem aleja el siguiente en vez de cancelarlo, así
    que mientras no llegue otro, el suyo sigue vigente.
    """
    if item is None or not item.utilizable:
        return Veredicto(False, f"no hay ítem de dos niveles utilizable para «{respuesta.nodo}»")

    ofrecido = next((o for o in ofrecidos if o.nodo == item.nodo), None)
    if ofrecido is None:
        return Veredicto(
            False,
            f"el ítem de «{item.nodo}» no se planteó en esta sesión: no se clasifica",
        )
    if ofrecidos[-1].nodo != item.nodo:
        return Veredicto(
            False,
            f"el ítem de «{item.nodo}» ya no es el vigente: la sesión ofreció "
            f"después el de «{ofrecidos[-1].nodo}»",
        )
    if item.nodo in contestados:
        return Veredicto(False, f"el ítem de «{item.nodo}» ya se contestó en esta sesión")

    razon = respuesta.razon.strip().lower()
    if ofrecido.razones and razon not in ofrecido.razones:
        return Veredicto(
            False, f"«{respuesta.razon}» no es una de las razones que se ofrecieron"
        )
    if item.opcion(respuesta.razon) is None:
        return Veredicto(False, f"«{respuesta.razon}» no es una razón de este ítem")
    if not respuesta.resultado.strip():
        return Veredicto(False, "la respuesta no trae resultado del turno 1")

    return Veredicto(True)


class Desenlace(str, Enum):
    """En qué acabó la respuesta al ítem que este turno traía. `R2-B`.

    Cuatro estados y no un booleano, porque los tres que **no** cierran el ítem
    se atienden igual pero no significan lo mismo, y la traza tiene que poder
    distinguirlos:

    | Estado | Qué pasó |
    |---|---|
    | `SIN_RESPUESTA` | el turno no traía `dos_niveles`. Es el caso normal de hoy |
    | `RECHAZADA` | el servidor **no admitió** la respuesta: ver `validar_respuesta()` |
    | `NO_CLASIFICABLE` | admitida, pero el servidor no pudo diagnosticarla |
    | `PROCESADA` | admitida **y** clasificada: hay `Diagnostico` |
    """

    SIN_RESPUESTA = "sin_respuesta"
    RECHAZADA = "rechazada"
    NO_CLASIFICABLE = "no_clasificable"
    PROCESADA = "procesada"


@dataclass(frozen=True)
class DesenlaceDelSondeo:
    """La **fuente única** de «qué hizo el servidor con esta respuesta». `R2-B`.

    Por qué existe · el defecto que cierra
    -----------------------------------------
    🐛 Hasta la revisión R2 el borde HTTP no tenía forma de saberlo. Anotaba el
    ítem como contestado **después de procesar el turno**, mirando sólo si el
    cliente había mandado el campo, y el estado del problema hacía lo mismo por
    su cuenta. Las dos mutaciones inferían el desenlace de «no saltó ninguna
    excepción», que es lo único que un `try` demuestra.

    Lo que la revisión independiente reprodujo con eso:

    1. mandar una respuesta a `N08` **antes** de que el servidor lo ofreciera;
    2. el filtro la rechaza, y `N08` aparece igualmente en `sondeos_contestados`
       —y el problema activo pasa a ser `item:N08`, con los contadores a cero—;
    3. la conversación llega de verdad a `N08` y el servidor lo ofrece;
    4. la respuesta legítima ya no se puede diagnosticar: el ítem está cerrado.

    El frontend normal no produce el primer payload. Da igual: **el servidor es
    la frontera de autoridad** y tiene que resistir clientes manipulados,
    pestañas viejas y reintentos obsoletos.

    Las dos lecturas, y por qué no son la misma
    -----------------------------------------------
    `cierra_el_item` es **sólo** `PROCESADA`. Una respuesta que no se pudo
    clasificar no cierra nada: el estudiante no recibió diagnóstico, así que
    cerrarle el ítem le quitaría su única oportunidad sobre esas cuatro razones
    a cambio de nada.

    `admitida` incluye además `NO_CLASIFICABLE`, y gobierna otra cosa: si esta
    respuesta **identifica el problema activo**. Contestar el ítem que el
    servidor acaba de ofrecer es hablar de ese ítem aunque el motor simbólico no
    haya podido corregir el turno 1; lo que no puede es que lo decida un payload
    que el servidor rechazó, porque entonces cualquiera reinicia los contadores
    de `RF-GEN-05` mandando un `dos_niveles` inventado.
    """

    estado: Desenlace = Desenlace.SIN_RESPUESTA
    #: El nodo del ítem, para no volver a leerlo del payload al mutar la sesión.
    nodo: str = ""
    #: Va siempre, también cuando se procesó. Un rechazo sin motivo no permite
    #: distinguir un cliente manipulado de un ítem retirado del contenido.
    motivo: str = ""

    @property
    def cierra_el_item(self) -> bool:
        """Si esta respuesta deja el ítem contestado. Sólo un diagnóstico."""
        return self.estado is Desenlace.PROCESADA

    @property
    def admitida(self) -> bool:
        """Si el servidor la aceptó como respuesta al ítem vigente."""
        return self.estado in (Desenlace.PROCESADA, Desenlace.NO_CLASIFICABLE)


@dataclass(frozen=True)
class EstadoDeSondeo:
    """Lo que la sesión recuerda de los ítems ya planteados.

    Viene **de fuera de la cadena**, igual que `Señales`: cuántos turnos van
    desde el último ítem no es algo que este turno pueda deducir de su propio
    texto. Lo mantiene el borde, que es quien conoce la sesión.
    """

    #: Turnos transcurridos desde el último ítem. El valor por defecto es alto
    #: a propósito: **nunca haber ofrecido no puede parecer «acabo de
    #: ofrecer»**, o el primer ítem no llegaría nunca.
    turnos_desde_el_ultimo: int = _TURNOS_ENTRE_SONDEOS
    #: Los ítems que esta sesión llegó a plantear, con sus razones. El tope de
    #: «un nodo, una vez por sesión» se lee de aquí, y la validación de una
    #: respuesta también: son la misma información y tenerla dos veces la
    #: dejaría desincronizarse.
    ofrecidos: tuple[ItemOfrecido, ...] = field(default_factory=tuple)
    #: Paquete H · los que ya se contestaron. Un ítem contestado está cerrado:
    #: volver a contestarlo produciría un segundo diagnóstico sobre las mismas
    #: cuatro razones, ya sabidas.
    contestados: tuple[str, ...] = field(default_factory=tuple)

    @property
    def nodos_ya_ofrecidos(self) -> tuple[str, ...]:
        return tuple(o.nodo for o in self.ofrecidos)


@dataclass(frozen=True)
class Ofrecimiento:
    """Si en este turno se plantea un ítem, y por qué sí o por qué no.

    El motivo va siempre, también cuando no se ofrece: `RF-REG-06` pide poder
    reconstruir la decisión pedagógica, y «no se ofreció» sin más no permite
    distinguir «no tocaba» de «no había ítem escrito».
    """

    item: ItemDosNiveles | None = None
    motivo: str = ""

    @property
    def procede(self) -> bool:
        return self.item is not None


def decidir(
    item: ItemDosNiveles | None,
    *,
    intencion: str = "",
    trae_expresion: bool = False,
    intentos_en_el_problema: int = 0,
    estado: EstadoDeSondeo | None = None,
    habilitado: bool = True,
    umbral_intentos: int = _INTENTOS_MINIMOS,
) -> Ofrecimiento:
    """Si este turno lleva ítem. Ver la tabla de la cabecera del módulo.

    `item` es `None` cuando el nodo del turno no tiene ninguno escrito; el
    banco actual trae `N08`, `N14` y `N05`. Nunca lanza, y con
    cero ítems el sistema conversa en texto libre exactamente como antes — la
    misma propiedad que `PM-B06` exigió a las plantillas.
    """
    estado = estado or EstadoDeSondeo()

    if not habilitado:
        return Ofrecimiento(motivo="el sondeo de este nodo está congelado por decisión curricular")
    if item is None:
        return Ofrecimiento(motivo="no hay ítem escrito para el nodo de este turno")
    if not item.ofrecible:
        return Ofrecimiento(motivo=f"el ítem de {item.nodo} está incompleto para plantearlo")
    if item.nodo in estado.nodos_ya_ofrecidos:
        return Ofrecimiento(motivo=f"el ítem de {item.nodo} ya se planteó en esta sesión")
    if estado.turnos_desde_el_ultimo < _TURNOS_ENTRE_SONDEOS:
        return Ofrecimiento(
            motivo=f"solo han pasado {estado.turnos_desde_el_ultimo} turnos desde el último"
        )
    if not trae_expresion or intencion == "emocional":
        return Ofrecimiento(motivo="el turno no está resolviendo un ejercicio")
    if intentos_en_el_problema < umbral_intentos:
        return Ofrecimiento(motivo="la duda todavía no está sostenida")

    return Ofrecimiento(
        item=item,
        motivo=f"{intentos_en_el_problema} intentos en un ejercicio de {item.nodo}",
    )
