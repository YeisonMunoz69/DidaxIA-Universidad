"""
problema.py — La unidad de problema y sus intentos
========================================================

Hasta la fase 4 los contadores del arbitraje eran **de la sesión**, y su propio
código lo declaraba: *«sigue sin ser “en el mismo paso”… se cuenta por sesión, y
por eso la escala no baja nunca dentro de una conversación aunque el estudiante
cambie de ejercicio»*. Con la escala de `RF-GEN-05` colgando de esos contadores,
la consecuencia era concreta: **tres intentos repartidos entre tres ejercicios
distintos abrían el desarrollo del cuarto**.

Este módulo es la corrección, y su núcleo son cuatro definiciones que la
política D de la fase 4 fija:

| Qué | Definición operativa |
|---|---|
| **problema** | la unidad matemática activa, identificada por nodo del grafo, expresión normalizada e ítem — información observable, nunca una etiqueta que alguien anota aparte |
| **intento** | una propuesta que aporta razonamiento, transformación, resultado parcial o decisión de procedimiento. Una cortesía no lo es; **una repetición idéntica tampoco** |
| **insistencia** | repetición de la petición de solución. No escala nada (`RF-GEN-04`) |

`DEC-R2` · la unidad de conteo v1 es **el problema activo**
--------------------------------------------------------------
Hasta la revisión R1 este módulo declaraba además un **paso** —«un subobjetivo
explícito»— y exportaba `Paso` y `abrir_paso()`. **No los llamaba ningún
productor real**: sólo sus propias pruebas. Un contador que nadie incrementa no
mide un paso, y tener dos conceptos para el mismo dato invitaba a que la
próxima lectura eligiera el equivocado.

`DEC-R2` lo cierra: la unidad es el problema activo y se llama así de extremo a
extremo. `intentos_en_el_paso` pasó a `intentos_en_el_problema` en dominio,
serialización, trazas, instantánea, documentación y pruebas, **sin alias**: un
alias permanente habría dejado las dos palabras vivas, que es el estado del que
se venía.

Por qué la identidad es observable y no declarada
----------------------------------------------------
Porque una etiqueta declarada envejece: alguien tendría que anotar «ahora
estamos en otro ejercicio», y quien no lo anotara arrastraría los contadores.
La identidad sale de lo que el turno **ya trae** —el nodo que el filtro 4 fijó y
la expresión que el filtro 1 segmentó—, así que cambiar de ejercicio cambia la
identidad sin que nadie tenga que decirlo.

⚠️ Y cuando no hay evidencia suficiente, **se conserva el problema actual**. La
política D lo pide con esas palabras: *«si no hay evidencia suficiente para
afirmar que cambió el problema, conserva el actual o pregunta; no lo adivines»*.
Un turno sin expresión y sin nodo —«sigo sin verlo»— sigue hablando del mismo
ejercicio, que es el caso típico.

Volver a un problema anterior · el contrato, escrito
--------------------------------------------------------
Los contadores son **del problema**, así que volver a uno recupera **los
suyos** y nunca los de otro. La conversación archiva el estado de los
problemas que ya vio —`_MAXIMO_ARCHIVADOS`, los más recientes— y al reconocer
otra vez esa identidad lo restaura entero: intentos, insistencias,
confirmación, expresiones vistas y episodios.

Las dos alternativas se descartan por lo que cada una rompe:

- **arrastrar los contadores** —lo que hacía la fase 3— suma intentos de
  ejercicios distintos, que es justo lo que `RF-GEN-05` no puede permitirse:
  tres intentos repartidos entre tres ejercicios abrían el desarrollo del
  cuarto;
- **reiniciar siempre al volver** tira evidencia real. El estudiante que
  intentó dos veces `cos(x)^3`, se fue a otra cosa y volvió, ya lo intentó dos
  veces; hacerle empezar de cero es medir la conversación, no su trabajo.

El archivo es de la conversación y muere con ella, como el resto de este
estado (política F.6). No es un perfil ni viaja entre conversaciones.

Los episodios, y qué los hace observables
--------------------------------------------
`DD-06` mide la ventana estratégica en **episodios**, no en turnos, y hasta la
fase 4 `EstadoEstrategico.registrar()` **no lo llamaba nadie**: `ciclo_negativo`
era siempre falso y el nivel 2 de `T6` era inalcanzable. Aquí cada episodio se
construye con cinco hechos que se pueden señalar en el turno que los produjo:

| Campo de `Episodio` | Productor observable |
|---|---|
| `retroalimentacion_correctiva` | el turno anterior sobre ESTE problema aplicó una estrategia que **corrige** —`KQ`, conflicto conceptual, desarrollo— **y** había algo escrito por el estudiante que corregir |
| `reincide_en_la_estrategia` | la expresión que escribe ya se vio en este problema |
| `confusion` | **declaró** bloqueo, o el motor **comprobó** que su propuesta no cuadra |
| `afecto_negativo` | escribió una manifestación emocional directa |
| `evitacion_o_bajo_esfuerzo` | pidió la respuesta con el problema abierto |

🔴 **Tres de los cinco no eran observables, y juntos fabricaban ciclos.**
La revisión R1 los corrigió, y el ciclo negativo importa porque gobierna el
nivel 2 de `T6`: fabricarlo cambia lo que el estudiante recibe.

- **`confusion` salía también de la intención `ambigua`.** Que el catálogo v1
  no resuelva la intención es una propiedad *del clasificador* —su propia rama
  ambigua significa «no hay evidencia suficiente»—, y convertir la falta de
  evidencia en evidencia de confusión es lo contrario de lo que declara.
- **`evitacion_o_bajo_esfuerzo` salía también de una cortesía.** «hola» y
  «gracias» son educación, no bajo esfuerzo. Con la regla vieja, tres
  cortesías llenaban la ventana de `DD-06`.
- **`retroalimentacion_correctiva` salía de cualquier estrategia que
  «orientara»**, incluidas `practica_guiada`, `dialogo_socratico_apos` y
  `primer_paso_ante_bloqueo`. Acompañar un paso no es corregir, y sin nada
  escrito del estudiante no hay nada suyo que corregir.

Cuándo se cierra un episodio, y desde cuándo cuenta
------------------------------------------------------
Se cierra **al cerrar el turno que lo produjo**, y sólo si ese turno trabajó
sobre el problema activo: propuso algo, repitió una propuesta o pidió la
respuesta. Un saludo no abre ninguno, tenga o no problema abierto.

Y **afecta desde el turno siguiente, nunca el suyo**: las `Señales` del
arbitraje se derivan al entrar el turno, con el estado tal como quedó al
cerrar el anterior. Es la misma disciplina que los contadores de intentos, y
la que hace que la decisión de un turno se pueda reconstruir con lo que se
sabía al tomarla.

Los episodios son **del problema**: cambiar de ejercicio los deja archivados
con él y el nuevo empieza sin ninguno, así que un atasco no viaja de un
ejercicio a otro. Y son de la conversación, no del estudiante: no cruzan entre
sesiones ni entre usuarios (política F.6).


"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, replace

from dominio.modelo.estudiante import Episodio, EstadoEstrategico
from dominio.pedagogia import estrategias as E
from dominio.pedagogia.intenciones import (
    BLOQUEO_EXPLICITO,
    PETICION_SOLUCION,
    Intencion,
)

#: Las estrategias que **corrigen**, que no son las que acompañan · paquete D.
#:
#: 🔴 Aquí estaban además `dialogo_socratico_apos`, `practica_guiada` y
#: `primer_paso_ante_bloqueo`, bajo el nombre `_ORIENTAN`. Orientar no es
#: corregir: acompañar un paso, dar un primer movimiento o sostener una
#: transición de nivel **no señalan ningún error del estudiante**, así que
#: escribir lo mismo después no es «reincidir sobre algo ya señalado».
#:
#: Las tres que quedan sí operan sobre lo que el estudiante produjo: `KQ`
#: señala un trozo suyo, el conflicto conceptual pone su regla frente a un
#: contraejemplo y el desarrollo le muestra el procedimiento entero.
_CORRIGEN = frozenset(
    {
        E.SCAFFOLDING_KQ,
        E.CONFLICTO_CONCEPTUAL,
        E.DESARROLLO_GUIADO,
    }
)

_ESPACIOS = re.compile(r"\s+")

#: Cuántos problemas cerrados recuerda una conversación. Paquete E: volver a
#: uno recupera sus contadores, y sin tope el estado de sesión crecería con
#: cada cambio de ejercicio. Ocho cubre una sesión de trabajo larga sin
#: convertir la sesión en un historial —para eso está el perfil versionado—.
_MAXIMO_ARCHIVADOS = 8


def normalizar_expresion(expresion: str) -> str:
    """La forma con la que se compara si dos expresiones son la misma.

    Sin espacios, sin tildes, en minúsculas y sin la puntuación de final de
    frase que el segmentador arrastra —`3*cos(x)^2.` y `3*cos(x)^2` son lo
    mismo escrito dos veces, y contarlas como dos intentos distintos es
    exactamente lo que la política D prohíbe—.

    **No pasa por el motor simbólico**, y es deliberado: aquí se compara lo que
    el estudiante ESCRIBIÓ, no lo que significa. Dos formas equivalentes pero
    distintas —`cos(x)^2-sen(x)^2` y `cos(2x)`— son dos intentos, porque son dos
    cosas que el estudiante pensó.
    """
    plano = unicodedata.normalize("NFD", expresion.strip().lower())
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
    return _ESPACIOS.sub("", plano).rstrip(".,;:")


@dataclass(frozen=True)
class UnidadDeProblema:
    """Qué ejercicio está activo, en información observable.

    Los tres campos pueden estar vacíos: una conversación puede no tener
    ningún problema abierto —alguien que sólo pregunta teoría—, y eso no es un
    hueco sino un estado.
    """

    nodo: str = ""
    expresion: str = ""
    item: str = ""

    @property
    def identidad(self) -> str:
        """La clave con la que se compara si dos turnos hablan del mismo.

        El ítem manda cuando lo hay: responder al ítem de `N08` es hablar de
        `N08` aunque el mensaje no traiga ninguna expresión.
        """
        if self.item:
            return f"item:{self.item}"
        if self.expresion:
            return f"expr:{normalizar_expresion(self.expresion)}"
        if self.nodo:
            return f"nodo:{self.nodo}"
        return ""

    @property
    def abierto(self) -> bool:
        return bool(self.identidad)


@dataclass(frozen=True)
class EstadoDelProblema:
    """Lo que la conversación sabe del ejercicio activo.

    `intentos` es lo que la escala de `RF-GEN-05` mide, y ahora sí es «en el
    mismo problema»: cambiar de ejercicio crea un estado nuevo.
    """

    unidad: UnidadDeProblema = field(default_factory=UnidadDeProblema)
    intentos: int = 0
    insistencias: int = 0
    peticion_confirmada: bool = False
    #: Las expresiones ya escritas en este problema, normalizadas. Sirven para
    #: la regla de la repetición y para el campo `reincide_en_la_estrategia`.
    expresiones_vistas: tuple[str, ...] = ()
    episodios: EstadoEstrategico = field(default_factory=EstadoEstrategico)
    #: La estrategia que el tutor aplicó en el turno anterior **de este
    #: problema**. Es lo que hace observable `retroalimentacion_correctiva`.
    estrategia_anterior: str = ""
    correccion_comprobada_anterior: bool = False
    #: Paquete E · los problemas que esta conversación ya vio, por identidad.
    #: Volver a uno restaura **sus** contadores; ver la cabecera sobre por qué
    #: ni se arrastran ni se reinician. Se guarda como tupla de pares para que
    #: el orden —y con él el tope de `_MAXIMO_ARCHIVADOS`— sea reproducible.
    archivados: tuple[tuple[str, EstadoDelProblema], ...] = ()

    @property
    def ciclo_negativo(self) -> bool:
        return self.episodios.ciclo_negativo

    @property
    def sesgo_de_confirmacion(self) -> bool:
        return self.episodios.sesgo_de_confirmacion

    def como_dict(self) -> dict:
        return {
            "unidad": {
                "nodo": self.unidad.nodo,
                "expresion": self.unidad.expresion,
                "item": self.unidad.item,
            },
            "intentos": self.intentos,
            "insistencias": self.insistencias,
            "peticion_confirmada": self.peticion_confirmada,
            "expresiones_vistas": list(self.expresiones_vistas),
            "episodios": [
                {
                    "retroalimentacion_correctiva": e.retroalimentacion_correctiva,
                    "reincide_en_la_estrategia": e.reincide_en_la_estrategia,
                    "confusion": e.confusion,
                    "afecto_negativo": e.afecto_negativo,
                    "evitacion_o_bajo_esfuerzo": e.evitacion_o_bajo_esfuerzo,
                }
                for e in self.episodios.episodios
            ],
            "estrategia_anterior": self.estrategia_anterior,
            "correccion_comprobada_anterior": self.correccion_comprobada_anterior,
            # El archivo se serializa **sin su propio archivo**: es un mapa de
            # problemas cerrados, y anidarlos produciría una cadena que crece
            # con cada cambio de ejercicio.
            "archivados": [
                [identidad, estado.como_dict()] for identidad, estado in self.archivados
            ],
        }

    @classmethod
    def desde_dict(cls, crudo: dict) -> EstadoDelProblema:
        unidad = crudo.get("unidad") or {}
        return cls(
            unidad=UnidadDeProblema(
                nodo=str(unidad.get("nodo", "")),
                expresion=str(unidad.get("expresion", "")),
                item=str(unidad.get("item", "")),
            ),
            intentos=int(crudo.get("intentos", 0)),
            insistencias=int(crudo.get("insistencias", 0)),
            peticion_confirmada=bool(crudo.get("peticion_confirmada", False)),
            expresiones_vistas=tuple(crudo.get("expresiones_vistas", ())),
            episodios=EstadoEstrategico(
                episodios=tuple(Episodio(**e) for e in crudo.get("episodios", ()))
            ),
            estrategia_anterior=str(crudo.get("estrategia_anterior", "")),
            correccion_comprobada_anterior=bool(crudo.get("correccion_comprobada_anterior", False)),
            archivados=tuple(
                (str(identidad), cls.desde_dict(guardado))
                for identidad, guardado in crudo.get("archivados", ())
            ),
        )


@dataclass(frozen=True)
class Observacion:
    """Lo observable de un turno que el modelo de problema necesita.

    Es un tipo cerrado y no el `ContextoTurno` entero, por la misma razón que
    `Situacion` lo es para la política: si mañana hace falta algo nuevo, tiene
    que producirlo un filtro y declararse aquí, no leerse por debajo.
    """

    intencion: Intencion
    #: Las expresiones que el filtro 1 segmentó de ESTE mensaje.
    expresiones: tuple[str, ...] = ()
    #: Si esas expresiones **no** se escribieron en este mensaje sino que el
    #: filtro 1 las heredó de la sesión (`PM-B31`). Paquete E: una expresión
    #: heredada es del turno anterior por definición, así que no puede ser
    #: evidencia de que el problema cambió — leerla como tal hacía que el
    #: ejercicio activo pasara a ser **la respuesta del propio estudiante**.
    expresiones_heredadas: bool = False
    #: El nodo que el filtro 4 fijó, si lo fijó.
    nodo: str = ""
    #: El nodo del ítem de dos niveles al que responde, si responde a uno.
    item: str = ""
    #: Lo que el filtro 6.6 concluyó de su propuesta.
    veredicto: str = ""
    #: La estrategia que el turno terminó aplicando. La aporta el borde después
    #: de la cadena: el episodio de un turno se cierra cuando el turno termina.
    estrategia: str = ""
    #: Base y propuesta explícitas del verificador; nunca una expresión heredada.
    base: str = ""
    propuesta: str = ""
    correccion_comprobada: bool = False


@dataclass(frozen=True)
class EventoDeConteo:
    """Qué cambió este turno y por qué. `RF-REG-06` para los contadores.

    Sin esto, «intentos: 2» no permite distinguir dos intentos reales de un
    intento contado dos veces por una repetición que nadie filtró.
    """

    problema_cambio: bool = False
    identidad: str = ""
    identidad_anterior: str = ""
    conto_intento: bool = False
    conto_insistencia: bool = False
    repeticion_ignorada: bool = False
    episodio_registrado: bool = False
    motivo: str = ""

    def como_dict(self) -> dict:
        return {
            "problema_cambio": self.problema_cambio,
            "identidad": self.identidad,
            "identidad_anterior": self.identidad_anterior,
            "conto_intento": self.conto_intento,
            "conto_insistencia": self.conto_insistencia,
            "repeticion_ignorada": self.repeticion_ignorada,
            "episodio_registrado": self.episodio_registrado,
            "motivo": self.motivo,
        }


def unidad_de(observacion: Observacion, actual: UnidadDeProblema) -> UnidadDeProblema:
    """Qué problema está activo tras este turno.

    **Conserva el actual cuando no hay evidencia de cambio.** Un turno sin
    expresión, sin nodo y sin ítem —«sigo sin verlo»— no dice que se haya
    cambiado de ejercicio; dice que se sigue en el mismo.

    🐛 **Y una propuesta con UNA sola expresión no es un ejercicio nuevo.**
    Cuando el turno propone —*«ahora me da x*cos(x) - sen(x)»*— esa expresión es
    **su respuesta**, no el enunciado. Leerla como problema nuevo reiniciaba los
    contadores en cada intento, así que una conversación de tres intentos se
    quedaba en uno y **nunca llegaba al nivel 3**: el estudiante que sí se había
    ganado el desarrollo no lo recibía. Se vio en la instantánea del banco, no
    razonándolo.

    La base sólo se lee cuando el turno la trae: dos expresiones —enunciado y
    propuesta, en ese orden, el mismo criterio que usa el filtro 6.6— o una sola
    en un turno que no está proponiendo nada.
    """
    if observacion.item:
        return UnidadDeProblema(nodo=observacion.nodo or actual.nodo, item=observacion.item)
    if observacion.base:
        return UnidadDeProblema(nodo=observacion.nodo or actual.nodo, expresion=observacion.base)
    if observacion.expresiones_heredadas and observacion.expresiones:
        # Paquete E · la herencia de `PM-B31` sirve para que el precómputo y la
        # verificación tengan sobre qué trabajar cuando el mensaje habla de «lo
        # de adentro». Como identidad del problema no vale nada: viene del
        # turno anterior, así que decir que el problema cambió por ella sería
        # cambiarlo por lo que ya había. Se conserva el actual, que es lo que
        # la política D pide sin evidencia de cambio.
        return actual if actual.abierto else UnidadDeProblema(
            nodo=observacion.nodo or actual.nodo, expresion=observacion.expresiones[0]
        )
    if observacion.expresiones:
        propone = observacion.intencion.propone_solucion
        if not propone or len(observacion.expresiones) >= 2:
            return UnidadDeProblema(
                nodo=observacion.nodo or actual.nodo, expresion=observacion.expresiones[0]
            )
        # Propone y sólo trae una expresión: es su respuesta. Se sigue en el
        # mismo ejercicio, y si no había ninguno abierto, ése pasa a serlo —
        # no hay otra lectura posible y perderla dejaría el problema sin abrir.
        if actual.abierto:
            return actual
        return UnidadDeProblema(
            nodo=observacion.nodo or actual.nodo, expresion=observacion.expresiones[0]
        )
    if observacion.nodo and observacion.nodo != actual.nodo:
        return UnidadDeProblema(nodo=observacion.nodo)
    return actual


def _episodio(estado: EstadoDelProblema, observacion: Observacion, repetida: bool) -> Episodio:
    """Los cinco hechos del episodio, cada uno señalable en el turno.

    Paquete D · **cada campo se puede apuntar con el dedo en la conversación**.
    Tres de ellos no podían, y su corrección es lo que impide que el sistema
    fabrique un ciclo negativo — que es la señal que gobierna el nivel 2 de
    `T6`, así que fabricarla cambia lo que el estudiante recibe.
    """
    intencion = observacion.intencion
    return Episodio(
        # El tutor **corrigió** en el turno anterior de este problema, y había
        # algo escrito por el estudiante que corregir. Las dos mitades hacen
        # falta: una estrategia correctiva sobre alguien que no ha escrito nada
        # no corrigió nada suyo, se llame como se llame.
        retroalimentacion_correctiva=(
            (estado.estrategia_anterior in _CORRIGEN or estado.correccion_comprobada_anterior)
            and bool(estado.expresiones_vistas)
        ),
        reincide_en_la_estrategia=repetida,
        # 🔴 `AMBIGUA` ya NO produce confusión. Que el catálogo v1 no resuelva
        # la intención es una propiedad **del clasificador**, no del estudiante:
        # el propio catálogo declara que su rama ambigua significa «no hay
        # evidencia suficiente», y convertir la falta de evidencia en evidencia
        # de confusión es exactamente lo contrario de lo que dice.
        #
        # Quedan los dos hechos que sí se pueden señalar: que el estudiante
        # **declaró** que no sabe seguir, y que el motor **comprobó** que su
        # propuesta no cuadra.
        confusion=(
            intencion.clase == BLOQUEO_EXPLICITO or observacion.veredicto == "invalida"
        ),
        afecto_negativo=intencion.carga_emocional_expresada,
        # 🔴 Una **cortesía** ya NO es evitación ni esfuerzo bajo. «hola» y
        # «gracias» son educación, y contarlos como bajo esfuerzo convertía una
        # conversación amable en un atasco. Queda pedir la respuesta con el
        # problema abierto, que sí es observable: el estudiante pide el
        # resultado en vez de trabajarlo.
        evitacion_o_bajo_esfuerzo=intencion.clase == PETICION_SOLUCION,
    )


def _contar(
    estado: EstadoDelProblema, intencion: Intencion, repetida: bool
) -> tuple[EstadoDelProblema, bool, bool, bool, str]:
    """Las cuatro ramas del conteo, y son excluyentes.

    Confirmar no es insistir, insistir no es intentar y repetir no es intentar
    de nuevo. Las tres distinciones son las que hacen compatibles `RF-GEN-04` y
    `RF-GEN-05`, y por eso viven en una sola función y no repartidas.
    """
    if intencion.confirma_ayuda:
        return (
            replace(estado, peticion_confirmada=True),
            False,
            False,
            False,
            "confirmó la ayuda que se le ofreció (RF-GEN-05)",
        )
    if intencion.clase == PETICION_SOLUCION:
        return (
            replace(estado, insistencias=estado.insistencias + 1),
            False,
            True,
            False,
            "pidió la respuesta: insistir no escala (RF-GEN-04)",
        )
    if intencion.propone_solucion and repetida:
        # La regla que la política D pide con todas las letras: *«una
        # repetición idéntica de la misma expresión normalizada no es un
        # intento nuevo»*. Sin ella, reenviar el mismo mensaje tres veces abre
        # el desarrollo.
        return (
            estado,
            False,
            False,
            True,
            "repite una expresión ya escrita en este problema: no es un intento nuevo",
        )
    if intencion.propone_solucion:
        return (
            replace(estado, intentos=estado.intentos + 1),
            True,
            False,
            False,
            "propuso algo nuevo sobre este problema",
        )
    return estado, False, False, False, "el turno no aporta ni pide: no mueve ningún contador"


def _cambiar_de_problema(
    estado: EstadoDelProblema, unidad: UnidadDeProblema
) -> EstadoDelProblema:
    """Archiva el problema que se deja y abre —o recupera— el que entra.

    Las tres cosas que hace, y las tres son el contrato del paquete E:

    1. **guarda** el estado del problema saliente bajo su identidad;
    2. **restaura** el entrante si esta conversación ya lo había visto;
    3. **abre uno nuevo en cero** si no.

    Ninguna rama suma los contadores de un ejercicio a los de otro, que es lo
    que la escala de `RF-GEN-05` no puede permitirse.
    """
    saliente = estado.unidad.identidad
    # El archivo del estado que se guarda va vacío: los problemas cerrados no
    # anidan sus propios cerrados.
    guardado = replace(estado, archivados=())
    archivo = [(clave, valor) for clave, valor in estado.archivados if clave != saliente]
    if saliente:
        archivo.append((saliente, guardado))
    archivo = archivo[-_MAXIMO_ARCHIVADOS:]

    entrante = unidad.identidad
    recuperado = next((valor for clave, valor in archivo if clave == entrante), None)
    if recuperado is not None:
        archivo = [(clave, valor) for clave, valor in archivo if clave != entrante]
        return replace(recuperado, unidad=unidad, archivados=tuple(archivo))
    return EstadoDelProblema(unidad=unidad, archivados=tuple(archivo))


def observar(
    estado: EstadoDelProblema, observacion: Observacion
) -> tuple[EstadoDelProblema, EventoDeConteo]:
    """El estado del problema tras este turno, y qué cambió.

    Es **la única** función que cuenta intentos e insistencias en el sistema.
    `adaptadores/entrantes/http/rutas/turno.py::contabilizar` le delega, para
    que no haya dos ideas de qué es un intento.
    """
    unidad = unidad_de(observacion, estado.unidad)
    anterior = estado.unidad.identidad
    cambio = bool(anterior) and unidad.identidad != anterior

    # Cambiar de ejercicio **cambia de estado**, y sólo el del problema: el
    # historial auditado no se borra —vive en el perfil versionado— y las
    # preferencias de la conversación tampoco, porque no son del ejercicio.
    #
    # Paquete E · el estado que se deja no se tira: se archiva por identidad, y
    # si el estudiante vuelve se restaura entero. Ver la cabecera sobre por qué
    # ni se arrastra ni se reinicia.
    estado = (
        _cambiar_de_problema(estado, unidad) if cambio else replace(estado, unidad=unidad)
    )

    intencion = observacion.intencion
    estado = replace(estado, peticion_confirmada=False)
    escritas = (observacion.propuesta,) if observacion.propuesta else (
        () if observacion.expresiones_heredadas else observacion.expresiones
    )
    nuevas = tuple(normalizar_expresion(e) for e in escritas if e.strip())
    repetida = bool(nuevas) and all(e in estado.expresiones_vistas for e in nuevas)

    estado, conto_intento, conto_insistencia, repeticion_ignorada, motivo = _contar(
        estado, intencion, repetida
    )

    if nuevas:
        vistas = list(estado.expresiones_vistas)
        for e in nuevas:
            if e not in vistas:
                vistas.append(e)
        estado = replace(estado, expresiones_vistas=tuple(vistas))

    # ── Cuándo se cierra un episodio · paquete D ──────────────────────────
    #
    # Un episodio se cierra **al cerrar el turno que lo produjo**, y sólo si
    # ese turno TRABAJÓ sobre el problema activo: propuso algo, repitió una
    # propuesta o pidió la respuesta. Las tres son cosas que el estudiante
    # hizo con el ejercicio delante.
    #
    # 🔴 `intencion.es_cortesia` estaba en esta lista, y era la mitad del
    # defecto: «hola» abría un episodio con `evitacion_o_bajo_esfuerzo`
    # puesto, así que tres cortesías bastaban para llenar la ventana de
    # `DD-06`. Un saludo no es un episodio de nada.
    #
    # Desde qué turno puede afectar la decisión: **desde el siguiente**. Las
    # `Señales` del arbitraje se derivan al ENTRAR el turno, con el estado tal
    # como quedó al cerrar el anterior, así que un episodio nunca cambia la
    # decisión del turno que lo produjo. Es la misma disciplina que los
    # contadores de intentos.
    episodio_registrado = False
    if estado.unidad.abierto and (
        conto_intento or conto_insistencia or repeticion_ignorada
    ):
        episodios, _ = estado.episodios.registrar(
            _episodio(estado, observacion, repetida), turno=""
        )
        estado = replace(estado, episodios=episodios)
        episodio_registrado = True

    if observacion.estrategia:
        estado = replace(estado, estrategia_anterior=observacion.estrategia)
    estado = replace(estado, correccion_comprobada_anterior=observacion.correccion_comprobada)

    return estado, EventoDeConteo(
        problema_cambio=cambio,
        identidad=unidad.identidad,
        identidad_anterior=anterior,
        conto_intento=conto_intento,
        conto_insistencia=conto_insistencia,
        repeticion_ignorada=repeticion_ignorada,
        episodio_registrado=episodio_registrado,
        motivo=motivo,
    )


def reiniciar_por_cambio_de_problema(
    estado: EstadoDelProblema, intencion: Intencion, expresiones: tuple[str, ...], *, base: str = ""
) -> tuple[EstadoDelProblema, bool]:
    """Aplica el reinicio **antes** de que el turno decida, si el problema cambió.

    Sin esto, el reinicio ocurría al cerrar el turno y el primer mensaje de un
    ejercicio nuevo se arbitraba con los contadores del anterior: se veía en la
    instantánea del banco como una pista dada sobre un problema en el que el
    estudiante no había intentado nada todavía.

    Se usa **la misma** `unidad_de()` que al cerrar; lo que cambia es que aquí
    sólo se mira la identidad y no se cuenta nada. Sin el nodo del grafo —que lo
    fija el filtro 4, más adelante en la cadena— la lectura es más conservadora:
    un turno sin expresión conserva el problema, que es lo que la política D
    pide cuando no hay evidencia de cambio.
    """
    unidad = unidad_de(
        Observacion(intencion=intencion, expresiones=expresiones, base=base), estado.unidad
    )
    anterior = estado.unidad.identidad
    if anterior and unidad.identidad != anterior:
        return EstadoDelProblema(unidad=unidad), True
    return estado, False
