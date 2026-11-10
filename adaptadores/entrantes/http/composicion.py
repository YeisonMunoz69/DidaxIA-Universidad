"""
composicion.py — Quien arma la cadena con sus adaptadores reales
=================================================================

`dominio/orquestador.py` lo dice con todas las letras: *«armarlos con sus
adaptadores reales es asunto de quien compone el sistema (una prueba, o más
adelante un adaptador de entrada), nunca de este módulo»*. Y
`AdaptadorTurno` lo repite: *«Eso es del compositor del sistema, que todavía
no existe porque `adaptadores/entrantes/` no tenía nada que componer»*.

Esto es ese compositor, escrito el 2026-08-10 cuando `PM-F02` intentó hablar
con el backend y descubrió que no había servidor al que hablarle.

Por qué vive en `adaptadores/entrantes/` y no en `dominio/`
-------------------------------------------------------------
Porque importa adaptadores, y la regla **N1** prohíbe que el dominio lo haga.
Es el único sitio del sistema donde los dos lados se ven a la vez, y por eso
es también el único que puede quedarse sin una pieza: si falta el índice o el
generador, aquí se sabe y **se dice**, en lugar de descubrirse a mitad de un
turno.

Lo que faltaba, y se cerró el mismo día · `PM-B17`
---------------------------------------------------
Al escribir este módulo por la mañana, **nadie convertía el texto generado en
una `RespuestaGenerada`**: `FiltroVerificacion` solo la tomaba de su
constructor, que es una costura de prueba, así que en producción no había nada
que verificar y **todo turno terminaba en degradación**. Se midió contra
DeepSeek antes de tocarlo —la cadena corría entera, la respuesta era buena, y
el filtro la descartaba sin mirarla— y luego se cableó:

- el filtro 7 pide el objeto de `ADR-014` §5.1 en el prompt;
- el adaptador lo obtiene, con salida estructurada nativa si el proveedor la
  tiene, y lo deja en `RespuestaDeGeneracion.estructura` (§5.3);
- el filtro 9 lo recoge del turno y aplica `C3` si viene malformado.

**Y se midió lo que `ADR-014` §9 pide como entregable**, que es la otra mitad:
ver `OE2-Arquitectura/experimentos/E03-Formato-del-Bloque/`.

✅ Dos avisos de esta cabecera que la fase 4 dejó vencidos
-----------------------------------------------------------
**«El sistema opera siempre en nivel 1»** era cierto cuando `dominio/arbitraje/`
no estaba construido. Ya lo está: la escala de `RF-GEN-05` sube a nivel 2 y 3
con los intentos y la confirmación, y `DEC-R3` abre además el nivel 2 ante una
petición explícita de teoría o de ejemplo. El motor simbólico **sí** trabaja en
un turno real, y de ahí salió un defecto que sólo se veía con base: ninguna
narración con afirmaciones se registraba en el historial (ver
`http/turno.py::_como_registro`).

**El enrutamiento de `cos(x)^3` a `N14`** —«la familia de la función del ejemplo
gana a la regla que se pregunta»— lo corrigió el paquete B de la revisión R1: el
filtro 4 pregunta al contenido qué nodo plantea el ejercicio que el turno trae, y
eso manda sobre la coincidencia léxica. Ver `dominio/filtros/enrutamiento.py`.
El patrón que `PM-V12` midió sigue siendo cierto **para el resto de consultas**,
las que no coinciden con un ejercicio declarado.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dominio.filtros.arbitraje import FiltroArbitraje
from dominio.filtros.deteccion import FiltroDeteccion
from dominio.filtros.diagnostico import FiltroDiagnostico
from dominio.filtros.enrutamiento import FiltroEnrutamiento
from dominio.filtros.estrategia import FiltroEstrategia
from dominio.filtros.generacion import FiltroGeneracion
from dominio.filtros.intencion import FiltroIntencion
from dominio.filtros.intento import FiltroIntento
from dominio.filtros.juez import FiltroJuez
from dominio.filtros.normalizacion import FiltroNormalizacion
from dominio.filtros.precomputo import FiltroPrecomputo
from dominio.filtros.prompt import FiltroPrompt
from dominio.filtros.recuperacion import FiltroRecuperacion
from dominio.filtros.registro import FiltroRegistro
from dominio.filtros.sondeo import FiltroSondeo
from dominio.filtros.verificacion import FiltroVerificacion
from dominio.orquestador import Orquestador
from dominio.puertos.corpus import Recuperacion
from dominio.puertos.plantillas import PuertoPlantillas

if TYPE_CHECKING:  # pragma: no cover
    from adaptadores.salientes.registro.archivo import AdaptadorRegistroArchivo
    from adaptadores.salientes.registro.historial import AdaptadorHistorialPostgres
    from adaptadores.salientes.registro.postgres import AdaptadorPerfilPostgres


@dataclass(frozen=True)
class Composicion:
    """La cadena, y **qué le faltó** para armarse entera.

    `faltantes` no es una lista de avisos: es lo que explica por qué un turno
    se degrada. Se publica en `/api/salud` para que quien depure no tenga que
    adivinar si el problema es su petición o la máquina.
    """

    orquestador: Orquestador
    faltantes: tuple[str, ...]
    contexto_reforzado: bool = False
    continuidad: bool = False
    interpretacion: str = "desactivada"
    retroalimentacion_directa: bool = False
    factores_conductuales: bool = False
    #: `PM-B11`, enganchado el 2026-08-12: el mismo adaptador que persiste
    #: `perfil_previo`/`perfil_actualizado` del filtro 3 (`AdaptadorTurno`) es
    #: el que `aplicacion.py` ya usaba para `RP-19` — un solo objeto, dos
    #: consumidores, en vez de construir la conexión dos veces.
    adaptador_perfil: AdaptadorPerfilPostgres | None = None
    #: `PM-B28`, 2026-08-14: el mismo cargador de `contenido/plantillas/` que
    #: los filtros 6.75 y 7 reciben. Se publica aquí porque `AdaptadorTurno`
    #: también lo necesita —para plantear el ítem— y construirlo dos veces
    #: leería el directorio dos veces para obtener lo mismo.
    plantillas: PuertoPlantillas | None = None
    #: `A2`, 2026-08-18 · el mismo adaptador que el filtro 12 usa para
    #: escribir es el que la cascada de `RD-22` usa para borrar. Se publica
    #: aquí porque hasta hoy solo lo veía la cadena: `rutas/datos_personales.py`
    #: no tenía forma de alcanzarlo, y por eso los registros de turno
    #: sobrevivían a una solicitud de supresión. Un objeto, dos consumidores —
    #: igual que `adaptador_perfil` y `plantillas`.
    adaptador_registro_turno: AdaptadorRegistroArchivo | None = None
    #: `PM-B37`, 2026-08-18 · el historial de conversación. Se publica aquí por
    #: la MISMA razón que el de arriba y con dos consumidores desde el primer
    #: día: el filtro 12 escribirá en él (`B3`) y la cascada de `RD-22` lo
    #: borra (`B4`). El camino de borrado se cablea **antes** que el de
    #: escritura, y no al revés: así no existe ningún commit en el que el
    #: sistema persista texto de estudiantes en una tabla que la supresión no
    #: toca. Es la lección de `A2`, aplicada por adelantado.
    adaptador_historial: AdaptadorHistorialPostgres | None = None
    configuracion_sondeos: object | None = None


class _CorpusVacio:
    """Puerto de corpus que no recupera nada, y lo declara.

    No es un doble de pruebas disfrazado: es el comportamiento correcto cuando
    no hay índice. `ADR-006` U3 tiene un modo **sin fuente** y el sistema sabe
    operar en él —`FiltroPrompt` deja dicho en el prompt que no hay material—,
    así que la ausencia de base de datos degrada la calidad de la respuesta sin
    romper el turno. Inventar fragmentos para que «funcione» sería lo contrario
    de lo que `RP-18` pide.
    """

    def recuperar(self, consulta: str, nodo: str | None = None, k: int = 3) -> Recuperacion:
        return Recuperacion(fragmentos=(), similitudes=(), sin_fuente=True)


class _SinIdentificador:
    """Sin grafo no se identifica nodo, y `ADR-002` ya tiene esa rama.

    Devolver `None` es la entrada del respaldo vectorial plano, que es un caso
    normal y no un error — `identificar_nodo` lo documenta así.
    """

    def identificar_nodo(self, consulta: str) -> str | None:
        return None


class _IndiceVacio:
    """Índice que no busca nada, para poder identificar nodo sin base.

    `RecuperadorJerarquico` necesita un índice para **recuperar**, y no lo toca
    para **identificar**: `identificar_nodo()` sólo usa el grafo y el perfil
    léxico, los dos de disco. Ver `_identificador_sin_indice`.
    """

    def buscar(self, consulta: str, k: int = 3, nodo: str | None = None):
        return []


def _grafo_y_perfil(raiz: Path):
    """El grafo y el perfil léxico, los dos **de disco**.

    Es lo único que `identificar_nodo()` necesita: la cascada de formas
    nombradas sale del grafo y el perfil se deriva de los fragmentos. Ni
    PostgreSQL ni el encoder entran aquí, y por eso puede construirse aunque
    los dos falten.
    """
    from adaptadores.salientes.corpus.cargador import (  # noqa: PLC0415
        cargar,
        claves_de_obra,
    )
    from adaptadores.salientes.recuperacion import (  # noqa: PLC0415
        GrafoEnMemoria,
        PerfilLexico,
    )

    contenido = raiz / "contenido"
    grafo = GrafoEnMemoria.desde_archivo(contenido / "grafo" / "grafo.json")
    corpus_dir = contenido / "corpus"
    cargado = cargar(
        corpus_dir / "fragmentos", obras=claves_de_obra(corpus_dir / "FUENTES.md")
    )
    return grafo, PerfilLexico.desde_fragmentos(cargado.fragmentos)


def _identificador_local(raiz: Path, faltantes: list[str]):
    """El identificador de nodo **determinista y local**.

    🔴 **Fase 4 · paquete A.** Hasta aquí esta pieza sólo existía para la rama
    «sin `AGENTE_BD`», y con base la identificación viajaba dentro del mismo
    `try` que el encoder E5. La consecuencia se midió en la integración
    continua del 2026-09-02: con el modelo de `intfloat/multilingual-e5-base`
    sin descargar, `CodificadorE5()` levantaba, el `except` devolvía
    `_SinIdentificador()` y **`nodo_activo` salía vacío en todos los turnos**.
    Cayeron seis pruebas —la instantánea de selección y las cinco del recorrido
    de dos niveles— por una dependencia que el enrutamiento no tiene.

    El grafo y los fragmentos son **archivos versionados**; el perfil léxico se
    deriva de ellos. Nada de eso necesita PostgreSQL ni el encoder, así que se
    construye **siempre** y por separado: un fallo de la recuperación semántica
    puede dejar el turno sin material —`ADR-006` U3, modo sin fuente— pero no
    puede borrar un nodo que la ruta local reconoce.
    """
    try:
        from adaptadores.salientes.recuperacion import (  # noqa: PLC0415
            RecuperadorJerarquico,
        )

        grafo, perfil = _grafo_y_perfil(raiz)
        return RecuperadorJerarquico(_IndiceVacio(), grafo, perfil=perfil)
    except Exception as exc:  # noqa: BLE001 — el borde decide, no revienta
        faltantes.append(
            f"no se pudo levantar el enrutamiento por nodo sin índice: {exc}"
        )
        return _SinIdentificador()


def _recuperacion(raiz: Path, faltantes: list[str], cadena: str):
    """`(identificador, corpus)` — y las dos mitades se deciden por separado.

    **Ésa es la corrección del paquete A**: identificar un nodo es local y
    determinista; recuperar fragmentos necesita el índice y el encoder. Cuando
    la segunda no se puede armar, la primera sobrevive y la degradación se
    **dice** en `faltantes`, que es lo que `/api/salud` publica.
    """
    local = _identificador_local(raiz, faltantes)

    if not cadena:
        faltantes.append(
            "AGENTE_BD no está en el entorno: sin índice, los turnos van en "
            "modo sin fuente (ADR-006 U3). El enrutamiento por nodo sí sigue "
            "activo: no depende de la base"
        )
        return local, _CorpusVacio()

    try:
        from adaptadores.salientes.recuperacion import (  # noqa: PLC0415
            IndicePostgres,
            RecuperadorJerarquico,
        )
        from adaptadores.salientes.recuperacion import (  # noqa: PLC0415
            codificador as _codificador,
        )

        grafo, perfil = _grafo_y_perfil(raiz)
        recuperador = RecuperadorJerarquico(
            IndicePostgres(cadena, _codificador.CodificadorE5()), grafo, perfil=perfil
        )
        # El mismo objeto sirve de identificador y de corpus: es el que
        # `E01` midió, y separarlos aquí mediría otra cosa.
        return recuperador, recuperador
    except Exception as exc:  # noqa: BLE001 — el borde decide, no revienta
        # ⚠️ Degradar la recuperación **no** degrada el enrutamiento. El motivo
        # se escribe entero para que quien lea `/api/salud` pueda distinguir
        # «este turno va sin material» de «este turno va sin nodo», que se
        # atienden distinto.
        faltantes.append(
            f"recuperación semántica degradada: no se pudo levantar el índice "
            f"ni el encoder E5 ({exc}). Los turnos van en modo sin fuente "
            f"(ADR-006 U3); el enrutamiento por nodo sigue activo"
        )
        return local, _CorpusVacio()


def _generador(faltantes: list[str], cadena: str):
    """El proveedor de generación que el entorno indique, o ninguno."""
    cual = os.environ.get("AGENTE_LLM", "").strip().lower()
    if not cual:
        faltantes.append(
            "AGENTE_LLM no está en el entorno (ollama | deepseek): sin "
            "generador, el turno se degrada en el filtro 8"
        )
        return None
    try:
        registrador = None
        if cadena:
            from adaptadores.salientes.registro.consumo_ia_db import (  # noqa: PLC0415
                AdaptadorConsumoIAPostgres,
            )

            registrador = AdaptadorConsumoIAPostgres(cadena)
        else:
            faltantes.append(
                "AGENTE_BD no está en el entorno: las llamadas al proveedor no tendrán "
                "medición institucional de consumo ni costo"
            )
        if cual == "ollama":
            from adaptadores.salientes.generacion.ollama import (  # noqa: PLC0415
                AdaptadorOllama,
            )

            return AdaptadorOllama(registrador_consumo=registrador)
        if cual == "deepseek":
            from adaptadores.salientes.generacion.deepseek import (  # noqa: PLC0415
                AdaptadorDeepSeek,
            )

            return AdaptadorDeepSeek(registrador_consumo=registrador)
    except Exception as exc:  # noqa: BLE001
        faltantes.append(f"no se pudo construir el generador «{cual}»: {exc}")
        return None

    faltantes.append(f"AGENTE_LLM=«{cual}» no es un proveedor conocido")
    return None


def _plantillas(raiz: Path, faltantes: list[str]):
    """El andamiaje socrático de `PM-C14`, o `None` si no se pudo leer.

    No depende de `AGENTE_BD` ni de ningún proveedor: es contenido versionado
    del árbol, igual que el banco de conceptos de `DD-13`. Que falte degrada
    la pedagogía de la respuesta —el filtro 7 vuelve a su andamio genérico—
    pero no rompe ningún turno, así que se declara en `faltantes` en vez de
    reventar el arranque.
    """
    try:
        from adaptadores.salientes.plantillas import (  # noqa: PLC0415
            CargadorDePlantillas,
        )

        cargador = CargadorDePlantillas(raiz / "contenido" / "plantillas")
    except Exception as exc:  # noqa: BLE001
        faltantes.append(f"no se pudieron leer las plantillas socráticas (PM-C14): {exc}")
        return None

    secuencias, genericas = cargador.cuantas
    if not secuencias and not genericas:
        faltantes.append(
            "contenido/plantillas/ está vacío o no existe: el filtro 7 vuelve al "
            "andamio genérico y la pedagogía de PM-C14 no llega al generador"
        )
    # `D-5`, fase 4 · un archivo mal delimitado entra al sistema **sin
    # repertorio**, y eso no se puede notar porque «las respuestas empeoren».
    # Se publica en `/api/salud` con el resto de lo que faltó.
    for problema in cargador.problemas:
        faltantes.append(f"contenido/plantillas/{problema}")
    return cargador


def _perfil(faltantes: list[str], cadena: str):
    """El adaptador del perfil versionado (`PM-B11`), o `None` sin `AGENTE_BD`.

    Un solo lugar donde se construye — `crear_aplicacion()` lo reutiliza para
    `RP-19` en vez de abrir una segunda conexión con el mismo criterio.
    """
    if not cadena:
        # `A4`, 2026-08-18 · antes devolvía `None` en silencio. Sin esta línea,
        # un despliegue sin `AGENTE_BD` no persiste NADA del perfil y
        # `GET /api/salud` no lo menciona — que es exactamente el modo mock
        # silencioso que `CONTEXTO-MAESTRO.md` §5.1 prohíbe. Y arrastra a
        # `RD-22`: sin adaptador no hay cascada que alcance el perfil.
        faltantes.append(
            "AGENTE_BD no está en el entorno: el perfil versionado (PM-B11) no "
            "se carga ni se guarda, y la cascada de supresión de RD-22 no lo "
            "alcanza"
        )
        return None
    try:
        from adaptadores.salientes.registro.postgres import (  # noqa: PLC0415
            AdaptadorPerfilPostgres,
        )

        return AdaptadorPerfilPostgres(cadena)
    except Exception as exc:  # noqa: BLE001 — el borde decide, no revienta
        faltantes.append(f"no se pudo construir el adaptador de perfil (PM-B11): {exc}")
        return None


def _historial(faltantes: list[str], cadena: str):
    """El adaptador del historial de conversación (`PM-B37`), o `None`.

    Mismo criterio que `_perfil()` y `_registro_turno()`: sin `AGENTE_BD` no
    hay adaptador, y **se dice** — `A4` cerró que un adaptador de persistencia
    ausente no puede ser silencioso. Aquí arrastra además a `RD-22`: sin
    adaptador no hay quien borre el historial de un titular.
    """
    if not cadena:
        faltantes.append(
            "AGENTE_BD no está en el entorno: el historial de conversación "
            "(PM-B37) no se escribe ni se puede consultar, y la cascada de "
            "supresión de RD-22 no lo alcanza"
        )
        return None
    try:
        from adaptadores.salientes.registro.historial import (  # noqa: PLC0415
            AdaptadorHistorialPostgres,
        )

        return AdaptadorHistorialPostgres(cadena)
    except Exception as exc:  # noqa: BLE001 — el borde decide, no revienta
        faltantes.append(f"no se pudo construir el historial (PM-B37): {exc}")
        return None


def _registro_turno(raiz: Path, faltantes: list[str], cadena: str):
    """El adaptador de `DD-08` para el filtro 12, o `None` sin `AGENTE_BD`.

    ✅ **Corregido el 2026-08-18.** Aquí decía que el directorio de archivos
    —`infraestructura/registro_turnos/`— *«no tiene volumen persistente
    declarado en `compose.produccion.yaml` todavía»*, y que en producción
    sobrevivía «solo hasta el próximo despliegue». **Es falso**:
    `compose.produccion.yaml:131` monta el volumen `registro-turnos`
    (`agente-calculo-registro-turnos`, declarado en `:185-186`) justo en esa
    ruta. Se comprobó con `docker inspect` sobre el contenedor en marcha, no
    leyendo el compose.

    El aviso se escribió cuando era cierto y nadie lo retiró al declarar el
    volumen. Es el tercer comentario vencido de esta misma familia que `A7`
    corrige, y el único que **exageraba un problema** en vez de esconderlo:
    inducía a no confiar en una persistencia que sí existe.

    ⚠️ Lo que sí sigue siendo cierto y conviene no perder: son **dos
    almacenes distintos** —el volumen de producción y el árbol de trabajo en
    desarrollo—, así que una purga alcanza uno y no el otro. La migración
    `04-registro-turno-sujeto.sql` lo dice en su cabecera con el comando de
    cada uno.
    """
    if not cadena:
        # `A4`, 2026-08-18 · igual que en `_perfil()`. Sin este adaptador el
        # filtro 12 no entra en la cadena, así que NINGÚN turno se registra
        # —`RF-REG-01` pide registrar la totalidad de los turnos— y la cascada
        # de `RD-22` se queda sin el almacén que `A2` acaba de engancharle.
        faltantes.append(
            "AGENTE_BD no está en el entorno: el registro del turno (DD-08) no "
            "se escribe, el filtro 12 no entra en la cadena, y la cascada de "
            "supresión de RD-22 no lo alcanza"
        )
        return None
    try:
        from adaptadores.salientes.registro.archivo import (  # noqa: PLC0415
            AdaptadorRegistroArchivo,
        )

        return AdaptadorRegistroArchivo(cadena, raiz / "infraestructura" / "registro_turnos")
    except Exception as exc:  # noqa: BLE001
        faltantes.append(f"no se pudo construir el registro de turnos (DD-08): {exc}")
        return None


def _filtros_de_interpretacion(interprete, solo_observar):
    if interprete is None:
        return []
    from dominio.filtros.interpretacion import FiltroInterpretacion  # noqa: PLC0415

    return [FiltroInterpretacion(interprete, observar=solo_observar)]


def _interpretacion_del_entorno():
    modo = os.environ.get("AGENTE_INTERPRETACION", "desactivada")
    if modo == "desactivada":
        return None, False
    if modo not in ("corroboracion", "observacion"):
        raise ValueError("AGENTE_INTERPRETACION debe ser desactivada, corroboracion u observacion")
    from adaptadores.salientes.generacion.interpretacion_deepseek import (
        InterpretacionDeepSeek,  # noqa: PLC0415
    )

    factores = os.environ.get("AGENTE_FACTORES_CONDUCTUALES", "0") == "1"
    return InterpretacionDeepSeek(factores_conductuales=factores), modo == "observacion"


def _filtros_de_retroalimentacion(simbolico, habilitada):
    if not habilitada:
        return []
    from dominio.filtros.retroalimentacion import FiltroRetroalimentacion  # noqa: PLC0415

    return [FiltroRetroalimentacion(simbolico)]


def _verificador(simbolico, retroalimentacion):
    if not retroalimentacion:
        return FiltroVerificacion(simbolico)
    from dominio.filtros.verificacion_retroalimentacion import (
        FiltroVerificacionRetroalimentacion,  # noqa: PLC0415
    )

    return FiltroVerificacionRetroalimentacion(simbolico)


@dataclass(frozen=True)
class ModoExperimental:
    interprete: object | None = None
    observar: bool = False
    retroalimentacion_directa: bool = False
    filtros_antes_interpretacion: tuple = ()
    filtros_despues_prompt: tuple = ()
    contexto_reforzado: bool = False
    continuidad: bool = False


def componer(
    raiz: Path | None = None, generador=None, cadena_bd: str | None = None,
    *, experimento: ModoExperimental | None = None, filtros_adicionales: tuple = (),
) -> Composicion:
    """Arma la cadena de `ADR-001` §6.3 con lo que haya, y dice qué faltó.

    `generador` se puede inyectar para atravesar la cadena sin proveedor; sin
    él sale de `AGENTE_LLM`, que es lo que hace `crear_aplicacion()`.

    El orden es el que el orquestador espera recibir ya ordenado: 1, 2, **3**,
    4, 5, **6**, **6.5**, **6.6**, **6.75**, **6.9**, 7, 8, 9, el juicio
    complementario y **12**. El
    orquestador separa caliente de fría por `Filtro.ruta` al construir
    (`PM-B13`), así que basta con pasar una sola lista — el 12 no necesita
    entrar al final ni en un lugar especial. El 11 (modelo del estudiante,
    ruta fría) sigue sin existir y por eso no está.

    El 6 entró el 2026-08-10 con `PM-B05`, en su mitad de divulgación; la otra
    mitad —la jerarquía de intervención de `T6`— es `PM-B13`. El 6.5 entró el
    mismo día que este comentario se actualizó, con `PM-B22`: el motor
    determinista de `ADR-013`. El 3 y el 12 entraron el 2026-08-12, escritos y
    probados desde dos sesiones antes (`PM-B10`, `PM-B20`) pero sin
    consumidor real hasta hoy.
    """
    raiz = raiz or Path(__file__).resolve().parents[3]
    # La ruta normal puede activar el mismo recorrido probado en el laboratorio.
    # La inyección de un generador de pruebas no activa red por variables del PC.
    if experimento is None and generador is None:
        interprete, solo_observar_interpretacion = _interpretacion_del_entorno()
        retroalimentacion_directa = generador is None and os.environ.get("AGENTE_RETROALIMENTACION_DIRECTA") == "1"
        modo_contexto = os.environ.get("AGENTE_CONTEXTO_CONVERSACIONAL", "actual")
        if modo_contexto not in ("actual", "reforzado"):
            raise ValueError("AGENTE_CONTEXTO_CONVERSACIONAL debe ser actual o reforzado")
        contexto_reforzado = modo_contexto == "reforzado"
    else:
        experimento = experimento or ModoExperimental()
        interprete = experimento.interprete
        solo_observar_interpretacion = experimento.observar
        retroalimentacion_directa = experimento.retroalimentacion_directa
        contexto_reforzado = experimento.contexto_reforzado
    from adaptadores.entrantes.http.contexto_conversacional import (
        FiltroContextoEntrada,
        FiltroContextoPrompt,
    )
    faltantes: list[str] = []
    # `cadena_bd` es la decisión explícita del paquete I: `None` la lee del
    # entorno —producción, y `crear_aplicacion()` nunca pasa otra cosa— y `""`
    # significa **sin base**, que es lo que una prueba de unidad quiere decir.
    # Antes esa segunda posibilidad no existía y «sin base» dependía de que
    # nadie tuviera `AGENTE_BD` puesta; bajo el laboratorio efímero, donde la
    # barrera de sesión la pone, la suite escribía en PostgreSQL sin quererlo.
    cadena = os.environ.get("AGENTE_BD", "") if cadena_bd is None else cadena_bd

    identificador, corpus = _recuperacion(raiz, faltantes, cadena)
    # `generador` inyectado: es la costura que permite atravesar la cadena
    # entera **sin llamar a un proveedor**. La pide el encargo de la fase 4 y
    # la usa `pruebas/soporte/generador_controlado.py`; sin ella, o se llama a
    # DeepSeek por red —lo que el propio `test_diagnostico_llega_al_andamiaje`
    # declara como fuente de intermitencia— o no se atraviesa el filtro 8, y
    # entonces no se puede decir nada de la respuesta visible.
    #
    # No es un modo de operación: `crear_aplicacion()` no lo pasa nunca, así
    # que en producción el generador sigue saliendo de `AGENTE_LLM`.
    if generador is None:
        generador = _generador(faltantes, cadena)
    adaptador_perfil = _perfil(faltantes, cadena)
    adaptador_registro_turno = _registro_turno(raiz, faltantes, cadena)
    adaptador_historial = _historial(faltantes, cadena)
    plantillas = _plantillas(raiz, faltantes)
    configuracion_sondeos = None
    if cadena:
        from adaptadores.salientes.registro.configuracion_sondeos_db import (  # noqa: PLC0415
            AdaptadorConfiguracionSondeosPostgres,
        )
        configuracion_sondeos = AdaptadorConfiguracionSondeosPostgres(cadena)

    from adaptadores.salientes.simbolico.adaptador import (  # noqa: PLC0415
        AdaptadorSimbolico,
    )

    # Un solo motor simbólico para los tres filtros que lo usan —6.5, 6.75 y
    # 9—, que es lo que `ADR-013` §6.1 quiere decir con «un puerto, dos
    # operaciones»: la frontera de proceso de `RI-08` es lo caro, y abrirla
    # tres veces la pagaría tres veces.
    simbolico = AdaptadorSimbolico()
    continuidad = os.environ.get("AGENTE_CONTINUIDAD_TUTOR") == "1" if experimento is None else experimento.continuidad
    if continuidad:
        from adaptadores.salientes.simbolico.proceso_aislado import SimbolicoAislado
        simbolico = SimbolicoAislado(simbolico)
    from dominio.filtros.continuidad import (
        FiltroContinuidadEntrada,
        FiltroContinuidadObjetivo,
        FiltroContinuidadPrompt,
        FiltroContinuidadResolver,
        FiltroContinuidadSalida,
    )

    filtros = [
        FiltroNormalizacion(),
        *([FiltroContinuidadEntrada()] if continuidad else []),
        FiltroIntencion(),
        *([FiltroContextoEntrada()] if contexto_reforzado else []),
        *(experimento.filtros_antes_interpretacion if experimento else ()),
        *(_filtros_de_interpretacion(interprete, solo_observar_interpretacion)),
        *([FiltroContinuidadResolver()] if continuidad else []),
        # Filtro 3 · no depende de AGENTE_BD ni de ningún proveedor: no hace
        # ningún I/O (ver su propio docstring). `perfil_previo`/`perfil_
        # actualizado` los carga y los guarda `AdaptadorTurno`, no este filtro
        # — es capacidad del adaptador de entrada, la misma disciplina que
        # `precomputar_limite()` ya fijó para el adaptador simbólico.
        FiltroDeteccion(),
        # `plantillas` · paquete B, fase 4 R1. El filtro pregunta al contenido
        # qué nodo plantea el ejercicio que el turno trae, y eso manda sobre la
        # coincidencia léxica: `cos(x)^3` es el ítem de `N08` aunque su
        # vocabulario apunte a `N14`. Ver `_ejercicio_declarado`.
        FiltroEnrutamiento(identificador, plantillas),
        FiltroRecuperacion(corpus),
        # Filtro 6 · va ANTES del prompt y no es indiferente: `ADR-014` §5.1
        # dice que el nivel lo fija el arbitraje **antes** de generar, y el
        # filtro 7 lo inyecta en la instrucción. Al revés, el generador
        # decidiría cuánto revelar, que es lo que §2 del contrato prohíbe.
        FiltroArbitraje(),
        # Filtro 6.5 · entre el arbitraje y el prompt, y no es indiferente:
        # `ADR-013` §6.2 dice que el filtro 7 no puede empezar sin él. Usa el
        # mismo adaptador simbólico que el filtro 9 —`ADR-013` §6.1: un solo
        # puerto, dos operaciones—. El motor es local y no depende de
        # AGENTE_BD ni de ningún proveedor externo, así que siempre está
        # disponible aunque `identificador`/`corpus`/`generador` no lo estén.
        FiltroPrecomputo(simbolico),
        # Filtro 6.6 · fase 4 · comprueba con el motor lo que el estudiante
        # propuso. Va DESPUÉS del 6.5 —comparte su adaptador simbólico,
        # `ADR-013` §6.1: un puerto, dos operaciones— y antes del selector,
        # porque su veredicto es una entrada de la política.
        FiltroIntento(simbolico),
        *_filtros_de_retroalimentacion(simbolico, retroalimentacion_directa),
        # Filtro 6.75 · `PM-B08` enganchado el 2026-08-13. Va lo más TARDE
        # posible a propósito: su único consumidor es el 7, y puesto antes del
        # 5 el diagnóstico cambiaría lo que se recupera, que es la ruta
        # diagnóstica del grafo que `ADR-006` §3.3 tiene aplazada. Ver el
        # docstring del filtro, que compara los tres sitios posibles.
        FiltroDiagnostico(plantillas, simbolico),
        # Filtro 6.8 · fase 4 · si este turno plantea un ítem de dos niveles.
        # Estaba en el adaptador, después de la cadena, y por eso la regla de
        # la política que produce `diagnostico_two_tier` era inalcanzable: el
        # prompt no podía saber que el turno iba a preguntar aparte.
        FiltroSondeo(plantillas, configuracion_sondeos),
        # Filtro 6.9 · fase 4 · QUÉ CLASE DE RESPUESTA es el turno. Las dos
        # posiciones están forzadas: después del 6.75 porque la política
        # prefiere el diagnóstico a la conjetura del motor simbólico, y antes
        # del 7 porque el prompt tiene que saber qué pedir antes de escribir la
        # instrucción — el mismo argumento que `ADR-014` §5.1 usa para el nivel.
        FiltroEstrategia(),
        *([FiltroContinuidadObjetivo(simbolico)] if continuidad else []),
        # Filtro 7 · recibe el andamiaje de `PM-C14` por el puerto
        # (`PM-B06`, 2026-08-12). Va DESPUÉS del 6.5 y no es indiferente: la
        # elección de plantilla usa `precomputo.concepciones_candidatas`, que
        # el 6.5 es quien calcula.
        FiltroPrompt(plantillas),
        *([FiltroContextoPrompt()] if contexto_reforzado else []),
        *([FiltroContinuidadPrompt()] if continuidad else []),
        *(experimento.filtros_despues_prompt if experimento else ()),
    ]
    if generador is not None:
        # 🐛 **Corregido el 2026-08-17, y el defecto se destapó al llenar el
        # índice.** `FiltroGeneracion` traía `maximo_de_unidades = 800` por
        # defecto y aquí no se le pasaba nada. Con el índice VACÍO —que es como
        # estuvo hasta `PM-C21`— las respuestas eran cortas y cabían; con 248
        # fragmentos de material real el modelo escribe largo, **el JSON de
        # `ADR-014` se corta a mitad**, `json.loads` falla, `_estructura()`
        # devuelve `None` y el filtro 9 desciende SIN respuesta. El estudiante
        # ve «el sistema no generó una respuesta emitible» con las cinco fases
        # en verde, que parece un fallo de infraestructura y no lo es.
        #
        # 📐 **El valor sale del prototipo, no de una estimación:**
        # `Pre-Arquitectura-Empirica/03-Prototipo-Codigo/config/config.yaml`
        # declara `max_output_tokens.generation: 8192` para el generador
        # pedagógico. Se toma 4096 como punto medio defendible —el objeto de
        # `ADR-014` es más compacto que prosa libre— y **configurable**, porque
        # `RNF-EFI-01` presupuesta latencia y este techo la mueve: subirlo es
        # una decisión con coste, no un ajuste libre.
        maximo = int(os.environ.get("AGENTE_MAX_UNIDADES", "4096"))
        filtros.append(FiltroGeneracion(generador, maximo_de_unidades=maximo))
        if continuidad:
            from dominio.filtros.reparacion_formato import FiltroReparacionFormato

            filtros.append(FiltroReparacionFormato(generador, maximo_de_unidades=maximo, cas=simbolico))
    filtros += [
        # `respuesta=None` es lo correcto desde `PM-B17`: el filtro la toma del
        # turno —`ctx.generacion.estructura`—, y el constructor queda como lo
        # que siempre debió ser, una costura de prueba. Antes era la única vía
        # y por eso todo turno degradaba.
        _verificador(simbolico, retroalimentacion_directa),
        *([FiltroContinuidadSalida(simbolico)] if continuidad else []),
        FiltroJuez(),
    ]
    if adaptador_registro_turno is not None:
        # Filtro 12 · ruta fría (`Filtro.ruta`, no la posición en la lista).
        # `AdaptadorTurno` lo invoca con `Orquestador.ejecutar_fria()` después
        # de construir la respuesta del turno — nunca antes.
        # `PM-B37`, 2026-08-18 · dos colaboradores: `archivo.py` escribe el
        # turno completo (`DD-08`) y `historial.py` el texto literal
        # (`RF-REG-01`). Ver el constructor del filtro sobre por qué son dos y
        # no un adaptador compuesto.
        from adaptadores.salientes.registro.factores_db import (
            AdaptadorFactoresPostgres,  # noqa: PLC0415
        )

        factores = AdaptadorFactoresPostgres(cadena) if cadena and os.environ.get("AGENTE_FACTORES_CONDUCTUALES", "0") == "1" else None
        filtros.append(FiltroRegistro(adaptador_registro_turno, adaptador_historial, factores))

    filtros.extend(filtros_adicionales)
    return Composicion(
        orquestador=Orquestador(filtros),
        faltantes=tuple(faltantes),
        adaptador_perfil=adaptador_perfil,
        plantillas=plantillas,
        adaptador_registro_turno=adaptador_registro_turno,
        adaptador_historial=adaptador_historial,
        configuracion_sondeos=configuracion_sondeos,
        contexto_reforzado=contexto_reforzado,
        continuidad=continuidad,
        interpretacion=("desactivada" if interprete is None else
                        "observacion" if solo_observar_interpretacion else "corroboracion"),
        retroalimentacion_directa=retroalimentacion_directa,
        factores_conductuales=bool(getattr(interprete, "factores_conductuales", False)),
    )
