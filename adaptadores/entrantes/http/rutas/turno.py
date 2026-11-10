"""
turno.py — `POST /api/turno` · la ruta que hace todo lo demás necesario
================================================================================

Una sola ruta, y la más cara del sistema: es la que ejecuta la cadena de
`ADR-001` §6.3 entera. Lo que vive aquí y no en `AdaptadorTurno` es lo que
depende de **la sesión** y no del turno — los contadores del arbitraje, la
clase, el sujeto del perfil—: `turno.py` (el adaptador) traduce dominio a
contrato, y este archivo le da el contexto de sesión que el dominio no puede
deducir de su propio texto.

⚠️ No confundir con `adaptadores/entrantes/http/turno.py`, que es el adaptador
—`AdaptadorTurno`, `TurnoEntrante`, la traducción del contrato—. Esto son las
rutas; ver el docstring de `rutas/__init__.py` sobre por qué se llaman igual.

La emisión por partes es del transporte, no del cálculo · `DD-11`
--------------------------------------------------------------------------
Responde **NDJSON**: una línea por fase y una última con el cuerpo o la
degradación. `AdaptadorTurno.manejar()` es síncrono y devuelve las dos partes
ya construidas. El orquestador notifica el inicio de cada filtro a una cola
por petición; las fases salen durante el trabajo y el cuerpo al terminar.
Un reintento devuelve la emisión conservada y no ejecuta otro turno.


"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import asdict, dataclass
from dataclasses import replace as dataclasses_replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool

from adaptadores.entrantes.http import aviso_legal
from adaptadores.entrantes.http.concurrencia import (
    CandadoPorConversacion,
    RegistroDeIdempotencia,
    clave_de,
)
from adaptadores.entrantes.http.contexto_conversacional import (
    contexto_de_sesion,
    reconstruir_contexto_factual,
    recordar_contexto_factual,
)
from adaptadores.entrantes.http.instrumentacion import (
    SIN_INSTRUMENTAR,
    Instrumentador,
    ResultadoDelTurno,
    SelloDelTurno,
)
from adaptadores.entrantes.http.limitador import LimitadorDePeticiones
from adaptadores.entrantes.http.progreso import EmisionDelTurno
from adaptadores.entrantes.http.rutas.comun import json_del_cuerpo, mantenimiento
from adaptadores.entrantes.http.rutas.historial import OPERACION_CONSULTA
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones, sujeto_de
from adaptadores.entrantes.http.turno import AdaptadorTurno, TurnoEntrante
from dominio.arbitraje.divulgacion import Señales
from dominio.diagnostico.clasificador import RespuestaAlItem
from dominio.filtros.intencion import (
    destino_solicitado_para_limite,
    extraer_curva_solicitada,
    extraer_ejercicio_explicito,
)
from dominio.filtros.normalizacion import segmentar
from dominio.modelo.acceso import (
    AccesoCalculado,
    calcular_acceso,
    permite_tutor,
    permite_tutoria_academica,
)
from dominio.modelo.contexto_de_uso import (
    ROL_ESTUDIANTE,
    ContextoDeUso,
    PoliticaDelTurno,
    contexto_de_uso_de,
    puede_consultar_como_profesional,
)
from dominio.modelo.deteccion_matematica import hallar_matematica
from dominio.pedagogia.conversacion import EstadoDeConversacion
from dominio.pedagogia.intenciones import PETICION_SOLUCION, clasificar
from dominio.pedagogia.problema import reiniciar_por_cambio_de_problema
from dominio.pedagogia.sondeo import EstadoDeSondeo, ItemOfrecido
from dominio.puertos.almacen import ErrorDeAlmacen
from dominio.puertos.supervision import (
    TIPO_DEGRADADO,
    TIPO_SIN_FUENTE,
    NuevoItem,
)

if TYPE_CHECKING:  # pragma: no cover
    from dominio.puertos.clases import PuertoClases
    from dominio.puertos.estado_vigente import PuertoEstadoVigente
    from dominio.puertos.supervision import PuertoColaDeRevision



def es_un_intento(mensaje: str) -> bool:
    """Si este mensaje es un intento de **resolver** algo.

    🐛 **Corregido dos veces, y la segunda es la fase 4.**

    La primera —2026-08-13, `D-20`, lo destapó `PM-V15`— cambió «cualquier
    mensaje que no pida la respuesta» por «el mensaje trae matemática»: `E04`
    había medido que **«hola», «gracias», «vale, entendido» llevaban el
    arbitraje a nivel 3**, tres cortesías y el sistema daba al estudiante por
    atascado hasta entregarle la corrección.

    La segunda es ésta. «Traer matemática» dejaba fuera el intento escrito
    **sólo en palabras** —*«yo primero aplicaría la regla del producto»*—, y su
    propio docstring lo declaraba como falso negativo asumido. La política de
    la fase 4 lo cierra: *«un razonamiento sólo verbal sí puede ser intento si
    propone qué hacer o por qué, aunque no contenga notación»*. Quien pregunta
    ahora es `dominio/pedagogia/intenciones.py`, que ya distingue proponer de
    pedir, y **no una segunda lista en el borde**.

    ⚠️ **La unidad de conteo es el problema activo** (`DEC-R2`), y la lleva
    `dominio/pedagogia/problema.py`, que es quien la conoce; esta función
    contesta la mitad que se puede contestar mirando un solo mensaje. Ya no
    queda ningún «paso» en el sistema: no lo producía nadie.
    """
    intencion = clasificar(mensaje, bool(hallar_matematica(mensaje)))
    return intencion.propone_solucion


def contabilizar(datos: dict, mensaje: str) -> None:
    """Actualiza los contadores de la sesión con este mensaje.

    **Un intento no es una insistencia**, y la distinción es la que hace
    compatibles `RF-GEN-05` y `RF-GEN-04`: pedir la respuesta cinco veces no
    escala nada; intentarlo y fallar, sí. Aquí sólo se cuenta; quién escala lo
    decide el filtro 6.

    ⚠️ **Las dos listas que vivían aquí ya no existen.** `_PIDE_LA_RESPUESTA` y
    `_CONFIRMA` eran un clasificador de intención escrito en el borde, y su
    propio comentario lo admitía: *«duplicar aquí un clasificador sería tener
    dos que pueden discrepar»*. El catálogo v1 del filtro 2 es ahora la fuente
    única, y esta función le pregunta en vez de mantener su propia copia.
    """
    intencion = clasificar(mensaje, bool(hallar_matematica(mensaje)))
    if intencion.confirma_ayuda:
        datos["peticion_confirmada"] = True
    elif intencion.clase == PETICION_SOLUCION:
        datos["insistencias"] += 1
    elif intencion.propone_solucion:
        datos["intentos"] += 1


def estado_de_conversacion_de(datos: dict) -> EstadoDeConversacion:
    """El estado temporal que toma las decisiones de este turno · política F.6.

    Sale del almacén de sesiones y **no de PostgreSQL**: el perfil versionado
    sigue reconstruyéndose para auditar, pero no decide. Una sesión abierta
    antes de que este campo existiera devuelve el estado en blanco, que es
    exactamente cómo empieza una conversación nueva.
    """
    return EstadoDeConversacion.desde_dict(datos.get("estado_pedagogico"))


def reiniciar_si_cambio_el_problema(
    estado: EstadoDeConversacion, mensaje: str, ejercicio_activo: dict | None = None
) -> EstadoDeConversacion:
    """El reinicio de contadores, aplicado **antes** de que el turno decida.

    Usa las mismas funciones que la cadena —`clasificar()` y `segmentar()`—, no
    copias suyas: dos ideas de qué es una expresión producirían dos ideas de
    cuándo cambió el ejercicio.
    """
    expresiones, _ = segmentar(mensaje)
    intencion = clasificar(mensaje, bool(hallar_matematica(mensaje)))
    from dominio.filtros.intento import ejercicio_de_intento_explicito
    from dominio.pedagogia.confirmacion import base_de_ejercicio
    from dominio.pedagogia.problema import normalizar_expresion

    nuevo = extraer_ejercicio_explicito(mensaje) or ejercicio_de_intento_explicito(mensaje)
    base = base_de_ejercicio(nuevo)
    if not nuevo and ejercicio_activo and expresiones and (
        len(expresiones) >= 2 or not intencion.propone_solucion
    ) and normalizar_expresion(expresiones[0]) == normalizar_expresion(ejercicio_activo.get("expresion", "")):
        base = base_de_ejercicio(ejercicio_activo)
    problema, cambio = reiniciar_por_cambio_de_problema(
        estado.problema, intencion, expresiones, base=base
    )
    return estado.con_problema(problema) if cambio else estado


def corregir_inferencia_si_lo_pide(
    estado: EstadoDeConversacion, mensaje: str
) -> EstadoDeConversacion:
    """Invalida la inferencia conductual cuando el estudiante la niega.

    Paquete F · usa la misma `clasificar()` que la cadena, no una copia suya, y
    delega en `EstadoDeConversacion.con_inferencia_corregida()`, que es donde
    está escrito **qué** se invalida y qué no se toca.
    """
    intencion = clasificar(mensaje, bool(hallar_matematica(mensaje)))
    if not intencion.corrige_inferencia:
        return estado
    return estado.con_inferencia_corregida()


def anotar_el_estado(datos: dict, estado: EstadoDeConversacion) -> None:
    """Guarda en la sesión lo que este turno dejó del estado pedagógico."""
    datos["estado_pedagogico"] = estado.como_dict()
    # Se conservan también sueltos porque `Señales` los lee por separado y el
    # arbitraje es quien los usa; es la misma proyección, no una segunda cuenta.
    datos["intentos"] = estado.problema.intentos
    datos["insistencias"] = estado.problema.insistencias
    datos["peticion_confirmada"] = estado.problema.peticion_confirmada
    datos["sin_adaptacion"] = estado.sin_adaptacion
    datos["estrategia_previa"] = estado.estrategia_previa


def recordar_preferencias(datos: dict, mensaje: str) -> None:
    """Anota en la sesión lo que el estudiante pidió sobre CÓMO se le responde.

    Hoy sólo una: **que el estilo no se adapte a sus expresiones**. La política
    F.9 de la fase 4 la autoriza —*«el estudiante puede pedir que el estilo no
    se adapte a sus expresiones durante la conversación»*— y exige que se
    respete **y quede trazada**, sin mostrarle ninguna etiqueta conductual.

    El alcance del opt-out, decidido y escrito · paquete F
    --------------------------------------------------------
    Es **de la conversación**, no persistente. Se pide una vez y rige hasta que
    la conversación termine; una conversación nueva empieza con la adaptación
    puesta. Por eso vive en la sesión, igual que los contadores del arbitraje.

    La alternativa —guardarlo en el perfil del titular— se descarta **en esta
    entrega y con motivo**: sería un dato de preferencia ligado a la persona,
    así que necesitaría entrar en el consentimiento de `EQ-016` y en la cascada
    de supresión de `RD-22`, y ninguna de las dos cosas se decide aquí. Es la
    misma frontera que la política F.6 fija para el resto del estado que
    decide. Hacerlo persistente es una decisión del equipo, no un ajuste.

    ⚠️ **No se apaga ni se enciende sola.** Retirar la preferencia es un acto
    del estudiante, no una consecuencia de que deje de repetirla; y volver a
    permitir la adaptación exige una orden explícita —«ya puedes adaptarte»—.
    🔴 Hasta la revisión R1 **esa orden no existía**: `sin_adaptacion` se ponía
    y no había forma de quitarla, y una preferencia que no se puede retirar
    deja de ser una preferencia.

    Si un mismo mensaje pidiera las dos cosas gana **apagarla**, que es el
    estado que protege: ante una petición contradictoria, el sistema no elige
    la que le da más margen.
    """
    intencion = clasificar(mensaje, bool(hallar_matematica(mensaje)))
    if intencion.sin_adaptacion:
        datos["sin_adaptacion"] = True
    elif intencion.reactiva_adaptacion:
        datos["sin_adaptacion"] = False


def claves_del_titular(datos: dict) -> tuple[str, str]:
    """Las DOS claves de este turno, que no son la misma · `DD-27`, 2026-08-18.

    Devuelve `(titular, sujeto_conductual)`:

    - **`titular`** · la clave de **supresión** (`RD-22`). Sale de
      `sujeto_de(datos)` **sin gatear**: `RL-09` deshabilita el módulo
      conductual, no el derecho de supresión del titular.
    - **`sujeto_conductual`** · la clave del **perfil** (`PM-B11`), vacía
      cuando `RL-09` no permite inferir. Es la que ya existía.

    **Por qué están separadas, y qué pasa si se vuelven a fundir.** Hasta el
    2026-08-18 había una sola, gateada, y el registro del turno se archivaba
    con ella. Eso hoy no rompe nada en producción porque `DD-26` §4 pone la
    edad por defecto en 18 dentro del modo piloto y `AGENTE_PILOTO_TESIS`
    viene encendida en `compose.produccion.yaml`. Pero el día que ese
    interruptor se apague —que es exactamente lo que `DD-26` §4 planea— un
    estudiante autenticado archivaría sus turnos bajo su sesión en vez de bajo
    su identidad estable, y la cascada por sujeto de `RD-22` no los
    alcanzaría. En silencio, y por una línea de configuración.
    """
    titular = sujeto_de(datos)
    return titular, (titular if aviso_legal.modulo_conductual_habilitado(datos) else "")


def clase_de_la_sesion(clases_almacen: PuertoClases, sujeto: str) -> str | None:
    """`PM-B21`. El identificador de la única clase de este sujeto, o `None`.

    «Una sesión puede pertenecer a varias» (`DD-12`) sigue siendo cierto, y
    sigue sin haber una noción de «clase activa» que el estudiante elija —
    eso sería un subsistema nuevo, no este campo. Mientras no exista, la
    única resolución que no inventa nada es la que solo tiene una respuesta
    posible: exactamente una clase. Cero o varias se declaran vacías, no se
    adivinan.

    `sujeto` es `sujeto_de(datos)`, no el identificador de conversación — el almacén de
    clases matricula por identidad estable desde el arreglo del 2026-08-22
    (ver `adaptadores/salientes/registro/clases_memoria.py`); pasar la sesión
    efímera aquí volvería a perder la coincidencia si la sesión rotó.
    """
    propias = clases_almacen.mias(sujeto)
    if len(propias) == 1:
        return propias[0].identificador
    return None


def rechazo_previo(
    sesiones: Sesiones,
    limitador: LimitadorDePeticiones,
    peticion: Request,
    estado_vigente: PuertoEstadoVigente | None = None,
) -> tuple[dict | None, JSONResponse | None]:
    """Las guardas de entrada del turno, con la forma de `requerir_rol()`.

    Devuelve `(datos_de_sesión, None)` cuando puede seguir, y `(None,
    respuesta)` cuando no. Están juntas porque son la **misma** clase de
    decisión —si este turno llega a la cadena o no— y ninguna mira lo que el
    estudiante escribió; el cuerpo de la petición ni siquiera se ha leído
    todavía. Los códigos son distintos a propósito y ninguno es 401 por
    defecto: `RP-02` y `DD-26` §3 dependen de que se distinga «no hay sesión»
    de «la sesión vale y lo que no procede es participar».

    ⚠️ **El hito B2 cambió quién autoriza el tutor.**
    ------------------------------------------------------------------
    Hasta B2 la puerta era `aviso_legal.puede_participar(datos)`, que mira un
    `dict` de sesión en memoria: el `consentimiento` que aquel `dict` llevaba lo
    escribía `POST /api/consentimiento` sobre `consentimiento_usuario`, la tabla
    heredada. `EQ-016` dice que *«el consentimiento gobernará qué funciones se
    habilitan»* y que *«el tutor no se habilita antes de la verificación»*, y un
    valor en memoria no es una verificación: se pierde en cada reinicio, no
    conoce versiones y no distingue a un menor sin autorización aprobada.

    Ahora manda `dominio/modelo/acceso.py` sobre el estado **persistido**, y sólo
    `habilitado` deja pasar. Los demás estados calculados tienen su propio
    código para que el cliente sepa qué hacer en vez de ver un 403 genérico.

    `estado_vigente` es opcional para no romper a quien componga sin base, y esa
    ausencia **cierra** el turno en vez de abrirlo: sin poder leer el estado no
    se puede afirmar que alguien esté habilitado (`EQ-024`).
    """
    datos = sesiones.leer(peticion.cookies.get(COOKIE))
    if datos is None:
        return None, JSONResponse({"detalle": "sin sesión"}, status_code=401)

    negativa = _puerta_del_turno(datos, estado_vigente)
    if negativa is not None:
        return None, negativa

    ip = peticion.client.host if peticion.client else "desconocida"
    # `sesion_autenticada` y no el token (hito R1): el tope es por sesión, y el
    # secreto de la cookie no tiene por qué circular por un contador en memoria
    # que además se puede volcar al depurar.
    if not limitador.admite_turno(ip, datos["sesion_autenticada"], sujeto_de(datos)):
        # 429, no 401: la sesión es válida, lo que se agotó es el tope.
        return None, JSONResponse({"detalle": "demasiadas peticiones"}, status_code=429)

    return datos, None


def _puerta_del_turno(
    datos: dict, estado_vigente: PuertoEstadoVigente | None
) -> JSONResponse | None:
    """Por qué puerta entra este turno. `None` si puede seguir · `EQ-031`.

    **Tres roles y tres tratos, con una allowlist explícita.** No es
    «estudiante o lo demás»: un rol que este servidor no reconozca recibe 403,
    no la puerta que no exige consentimiento. Ver la advertencia de
    `dominio/modelo/contexto_de_uso.py` sobre por qué la clasificación
    —que sí falla hacia «no evaluar»— no puede decidir también quién entra.

    - **estudiante** · la puerta de `EQ-016` intacta: sólo pasa quien tiene el
      acceso calculado en `habilitado`, con perfil, consentimiento vigente y,
      si es menor, autorización del representante aprobada. No se toca ni una
      línea de esa comprobación.
    - **docente / investigador** · `EQ-031` les concede el modo Tutor. No pasan
      por el consentimiento del estudiante porque **no tienen uno que dar**: el
      recorrido de `EQ-020` autoriza el tratamiento de datos de un participante
      del piloto, y un docente que pregunta por una derivada no es un
      participante. Exigírselo lo dejaría fuera para siempre —su acceso
      calculado es `onboarding_pendiente` y no hay onboarding que completar— y
      no protegería nada: sus turnos no alimentan perfil ni diagnóstico.
    - **cualquier otro rol** · 403.

    ⚠️ **El rol sale de la sesión del servidor**, nunca del cuerpo. `RP-17` ya
    lo fija en general; aquí importa especialmente porque las dos puertas son
    distintas y elegir la propia sería saltarse el consentimiento o meterse en
    los agregados de una clase ajena.
    """
    rol = datos.get("rol")
    if rol == ROL_ESTUDIANTE:
        return _rechazo_por_acceso(datos, estado_vigente)
    if puede_consultar_como_profesional(rol):
        return _apertura_profesional(datos)
    return JSONResponse(
        {
            "detalle": "esta cuenta no tiene el tutor habilitado",
            "estado": "rol_sin_tutor",
        },
        status_code=403,
    )


def _apertura_profesional(datos: dict) -> None:
    """La consulta profesional de `EQ-031` pasa, y deja dicho que no evalúa.

    Escribe los dos campos que `_rechazo_por_acceso()` deja para el estudiante,
    **explícitamente en `None`**, y no se limita a no ponerlos:

    - `consentimiento_evento` · no hay ninguno que referenciar. `None` es «no
      consta», que es la verdad; inventar un vínculo ataría el historial de un
      docente a una autorización de participante que nunca firmó.
    - `acceso_calculado` · no se calculó, porque no hay recorrido que evaluar.
      `aviso_legal.permite_escritura_conductual()` devuelve `False` ante `None`
      —«no sé si puedo escribir» se resuelve no escribiendo, `EQ-024`—, así que
      esta línea es además la primera de las tres barreras que impiden que un
      turno profesional toque el perfil longitudinal.

    Se escriben aquí y no se dejan al azar de que la sesión no los trajera: un
    `dict` de sesión es reutilizable entre turnos y podría conservar el valor de
    otro. Mismo motivo por el que `_rechazo_por_acceso()` los reinicia al entrar.
    """
    datos["consentimiento_evento"] = None
    datos["acceso_calculado"] = None
    datos["contexto_de_uso_turno"] = ContextoDeUso.CONSULTA_PROFESIONAL
    return None


#: Qué respuesta corresponde a cada estado calculado que NO habilita el tutor.
#: Códigos distintos porque el cliente hace cosas distintas con cada uno: 403 es
#: «no procede», 409 «falta un paso tuyo», 503 «vuelve más tarde».
_CODIGO_POR_ACCESO = {
    AccesoCalculado.ONBOARDING_PENDIENTE: 409,
    AccesoCalculado.ESPERANDO_REPRESENTANTE: 409,
    AccesoCalculado.BLOQUEADO_POR_RECHAZO: 403,
    AccesoCalculado.BLOQUEADO_POR_REVOCACION: 403,
    AccesoCalculado.ELIMINACION_SOLICITADA: 403,
    AccesoCalculado.MANTENIMIENTO: 503,
}


def _rechazo_por_acceso(
    datos: dict, estado_vigente: PuertoEstadoVigente | None
) -> JSONResponse | None:
    """`None` si el acceso calculado habilita el tutor; si no, la negativa.

    Sin puerto de estado no se abre: `EQ-024` prohíbe afirmar lo que no se sabe,
    y «no puedo leer el consentimiento» no puede resolverse dejando pasar.

    **Efecto lateral deliberado (hito B3):** cuando deja pasar, anota en la
    sesión el evento de consentimiento vigente. `EQ-016` pide que cada turno lo
    referencie, y volver a consultarlo al construir el turno daría dos respuestas
    distintas si el consentimiento cambiara entre medias — que es exactamente la
    ventana donde el vínculo importaría.
    """
    datos["consentimiento_evento"] = None
    datos["acceso_calculado"] = None
    datos["contexto_de_uso_turno"] = None
    if estado_vigente is None:
        return mantenimiento("no se puede comprobar el consentimiento en este momento")
    try:
        estado = estado_vigente.estado_vigente(datos["identificador_estable"])
    except ErrorDeAlmacen:
        return mantenimiento("no se puede comprobar el consentimiento en este momento")
    if estado is None:
        # Sesión viva y persona ausente: no puede pasar por el camino normal —B1
        # registra la identidad antes de crear la sesión— así que es un estado
        # que no se sabe leer, no un onboarding en blanco.
        return mantenimiento("la identidad de esta sesión no está disponible")

    acceso = calcular_acceso(estado)
    # Se anota junto al evento y por el mismo motivo (`EQ-016`, hito B3): quien
    # decide si este turno escribe en el perfil longitudinal tiene que usar
    # **el mismo estado** con el que se autorizó, no volver a consultarlo. Entre
    # las dos consultas cabe un cambio de consentimiento, y ésa es justo la
    # ventana donde el vínculo importaría.
    datos["acceso_calculado"] = acceso
    if permite_tutor(acceso) or permite_tutoria_academica(estado):
        if acceso is AccesoCalculado.HABILITADO:
            datos["consentimiento_evento"] = estado.evento_consentimiento
            datos["contexto_de_uso_turno"] = ContextoDeUso.APRENDIZAJE_ESTUDIANTE
        else:
            datos["contexto_de_uso_turno"] = (
                ContextoDeUso.TUTORIA_ACADEMICA_SIN_INVESTIGACION
            )
        return None
    return JSONResponse(
        {"detalle": "el tutor no está habilitado para esta cuenta", "acceso": acceso.value},
        status_code=_CODIGO_POR_ACCESO.get(acceso, 403),
    )


def respuesta_al_item_de(cuerpo: dict) -> RespuestaAlItem | None:
    """`PM-B08` · lo que el estudiante contestó a un ítem de dos niveles.

    `None` cuando el cuerpo no lo trae, que es **el caso normal de hoy**: el
    sistema no plantea ítems todavía. Se lee aquí y no en el dominio porque es
    traducción del contrato (`08-Contrato-del-Turno.md` §3.bis), igual que
    `mensaje` y `momento`.

    ⚠️ **Se aceptan los tres campos y ni uno más.** Si el cliente pudiera
    mandar `es_correcta` o la concepción, el estudiante se diagnosticaría a sí
    mismo escribiendo un campo — la misma razón por la que `Señales` no viaja
    desde el navegador. Quién es correcta y qué delata lo resuelve el filtro
    6.75 contra el banco del servidor.
    """
    crudo = cuerpo.get("dos_niveles")
    if not isinstance(crudo, dict):
        return None
    nodo = str(crudo.get("nodo") or "").strip()
    resultado = str(crudo.get("resultado") or "").strip()
    razon = str(crudo.get("razon") or "").strip()
    if not (nodo and resultado and razon):
        # Un ítem a medias no se completa con supuestos: el filtro lo trataría
        # como no diagnosticable de todas formas, y así el motivo que sale en
        # la traza es el de verdad y no «no es una razón de este ítem».
        return None
    return RespuestaAlItem(nodo=nodo, resultado=resultado, razon=razon)


def recordar_expresion(datos: dict, mensaje: str) -> None:
    """Guarda en la sesión la última expresión que el estudiante escribió.

    `PM-B31`. Usa **el mismo segmentador que el filtro 1** —`segmentar()`, que
    se expuso para esto— en vez de una copia: dos criterios de qué es una
    expresión podrían discrepar, y entonces la que el sistema recuerda no sería
    la que normalizó.

    Solo se sobrescribe cuando hay una nueva, así que la conversación conserva
    la última mientras el estudiante hable de ella sin volver a escribirla.
    """
    activo = datos.get("ejercicio_activo") or {}
    if activo and activo.get("tipo") != "limite":
        # Una propuesta breve no puede convertirse en la función del siguiente turno.
        datos["expresion_previa"] = activo.get("expresion", "")
        return
    if activo and extraer_ejercicio_explicito(mensaje) is None:
        # Conservar también el operador y el destino escritos en un límite.
        return
    expresiones, _ = segmentar(mensaje)
    if expresiones:
        datos["expresion_previa"] = expresiones[0]


def recordar_ejercicio(datos: dict, mensaje: str) -> None:
    """Conserva el enunciado explícito, sin sustituirlo por un resultado.

    La comprobación se hace más adelante por SymPy. Aquí sólo se registra la
    referencia del turno para que «me da -1» tenga un ejercicio inequívoco.
    """
    from dominio.filtros.intento import ejercicio_de_intento_explicito
    from dominio.modelo.referencias_matematicas import recordar_funciones_y_resolver

    ejercicio = recordar_funciones_y_resolver(datos, mensaje)
    if ejercicio is None:
        ejercicio = extraer_ejercicio_explicito(mensaje) or ejercicio_de_intento_explicito(mensaje)
        if ejercicio is not None:
            datos.pop("funcion_vigente", None)
    if ejercicio is not None:
        datos["ejercicio_activo"] = ejercicio
        datos.pop("ejercicio_en_pausa", None)
    elif not datos.get("ejercicio_activo") and datos.get("ejercicio_en_pausa"):
        # Dibujar otra curva es una consulta lateral, no necesariamente el fin
        # del problema. Sólo se retoma si el estudiante nombra explícitamente
        # el tipo anterior: una respuesta suelta no se atribuye a ciegas.
        previo = datos["ejercicio_en_pausa"]
        nombre = r"l[ií]mite" if previo.get("tipo") == "limite" else r"derivada"
        retoma = re.search(
            r"\b(?:resultado|respuesta|valor|retomemos|retomar|volver|vuelvo|antes)\b",
            mensaje, re.I,
        )
        if retoma and re.search(rf"\b{nombre}\b", mensaje, re.I):
            datos["ejercicio_activo"] = datos.pop("ejercicio_en_pausa")
            destino = destino_solicitado_para_limite(mensaje, previo.get("destino", ""))
            if destino and previo.get("tipo") == "limite":
                datos["ejercicio_activo"] = {**previo, "destino": destino}
    elif (datos.get("ejercicio_activo") or {}).get("tipo") == "limite":
        destino = destino_solicitado_para_limite(mensaje, datos["ejercicio_activo"].get("destino", ""))
        if destino:
            datos["ejercicio_activo"] = {**datos["ejercicio_activo"], "destino": destino}
        elif (re.search(r"\b(?:grafica|graficar|dibuja|simplifica|factoriza|integra)\b", mensaje, re.I)
              and segmentar(mensaje)[0]
              and not re.search(r"\b(?:a[nñ]ade|agrega|compara)\b", mensaje, re.I)
              and extraer_curva_solicitada(mensaje) != datos["ejercicio_activo"].get("expresion")):
            datos["ejercicio_en_pausa"] = datos.pop("ejercicio_activo")
    elif (re.search(r"\b(?:grafica|graficar|dibuja|simplifica|factoriza|integra)\b", mensaje, re.I)
          and segmentar(mensaje)[0]
          and not re.search(r"\b(?:a[nñ]ade|agrega|compara)\b", mensaje, re.I)
          and extraer_curva_solicitada(mensaje) != (datos.get("ejercicio_activo") or {}).get("expresion")):
        # Una operación nueva explícita sobre otra fórmula cierra la referencia
        # anterior; no se verifica después contra un límite ya abandonado.
        datos["ejercicio_en_pausa"] = datos.pop("ejercicio_activo", None)


def recuperar_ejercicio_del_historial(datos: dict, contexto: list[dict]) -> None:
    """Reconstruye el problema del hilo completo, incluso si hubo una gráfica."""
    datos.pop("ejercicio_activo", None)
    datos.pop("ejercicio_en_pausa", None)
    datos.pop("funciones_declaradas", None)
    datos.pop("funcion_vigente", None)
    datos.pop("expresion_previa", None)
    for par in contexto:
        mensaje = str(par.get("estudiante", ""))
        recordar_ejercicio(datos, mensaje)
        recordar_expresion(datos, mensaje)


def estado_de_sondeo_de(datos: dict) -> EstadoDeSondeo:
    """`PM-B28` · lo que la sesión recuerda de los ítems ya planteados.

    Se lee del almacén de sesiones y **no del cliente**, por la misma razón
    que las señales del arbitraje: si el navegador pudiera decir «hace mucho
    que no me preguntas», el tope de frecuencia dejaría de ser del dominio.
    """
    return EstadoDeSondeo(
        turnos_desde_el_ultimo=int(datos.get("turnos_desde_el_sondeo", 0)),
        ofrecidos=tuple(
            ItemOfrecido(nodo=str(o.get("nodo", "")), razones=tuple(o.get("razones", ())))
            for o in datos.get("sondeos_ofrecidos", ())
            if isinstance(o, dict)
        ),
        contestados=tuple(str(n) for n in datos.get("sondeos_contestados", ())),
    )


def anotar_el_item_contestado(datos: dict, desenlace) -> None:
    """Cierra el ítem **sólo si el servidor procesó la respuesta** · `R2-B`.

    🐛 **El defecto que esto corrige, reproducido por la revisión R2.**

    Esta función recibía `entrante.respuesta_al_item` —lo que el CLIENTE
    mandó— y anotaba el nodo sin más. Su versión anterior lo defendía: *«lo
    que cierra el ítem es que el estudiante lo contestó, no que su respuesta
    fuera clasificable»*. El argumento se cae en cuanto el que manda el payload
    no es el estudiante:

    1. una supuesta respuesta a `N08` llega **antes** de que el servidor lo
       ofreciera;
    2. `validar_respuesta()` la rechaza —y aun así `N08` queda contestado—;
    3. la conversación llega de verdad a `N08` y el servidor lo ofrece;
    4. la respuesta legítima ya no se diagnostica: el ítem está cerrado.

    Ese payload lo produce un cliente manipulado, una pestaña vieja o un
    reintento obsoleto, no el frontend normal. Da igual: el servidor es la
    frontera de autoridad.

    Ahora la decisión llega **del dominio**, en `DesenlaceDelSondeo`, y esta
    función no vuelve a mirar el payload. Lo que se acepta y lo que no está en
    esa clase y en `validar_respuesta()`, en un solo sitio.

    ⚠️ **Y el ítem se queda abierto cuando la respuesta se admitió pero no se
    pudo clasificar** —el motor simbólico no pudo corregir el turno 1—. Es
    deliberado y es lo contrario de lo que hacía antes: sin diagnóstico, cerrar
    el ítem le gasta al estudiante su única oportunidad sobre esas cuatro
    razones a cambio de nada.

    Idempotente por construcción: un nodo ya anotado no se anota dos veces, así
    que un reintento que vuelva a llegar aquí no duplica nada.
    """
    if not desenlace.cierra_el_item:
        return
    contestados = list(datos.get("sondeos_contestados", ()))
    if desenlace.nodo and desenlace.nodo not in contestados:
        contestados.append(desenlace.nodo)
    datos["sondeos_contestados"] = contestados


def anotar_el_sondeo(datos: dict, salida) -> None:
    """Actualiza el contador de la sesión con lo que este turno hizo.

    **El contador avanza se haya ofrecido o no**, y ahí está la respuesta a
    «qué pasa si el estudiante lo ignora»: ignorar un ítem **aleja** el
    siguiente en vez de acercarlo, sin que haga falta ningún mecanismo de
    reintento. Ver `dominio/pedagogia/sondeo.py` §3.
    """
    sondeo = salida.cuerpo.sondeo if salida.cuerpo is not None else None
    if sondeo is None:
        datos["turnos_desde_el_sondeo"] = int(datos.get("turnos_desde_el_sondeo", 0)) + 1
        return
    datos["turnos_desde_el_sondeo"] = 0
    # 🔴 Fase 4 · se guardan **las razones que se emitieron**, no sólo el nodo.
    # Sin ellas el servidor podía respetar el tope de frecuencia y aun así
    # clasificar una respuesta a un ítem que nunca planteó, o con una razón de
    # otro ítem. Ver `dominio/pedagogia/sondeo.py::validar_respuesta`.
    ofrecidos = list(datos.get("sondeos_ofrecidos", ()))
    if all(o.get("nodo") != sondeo.nodo for o in ofrecidos):
        ofrecidos.append(
            {"nodo": sondeo.nodo, "razones": [r.id for r in sondeo.razones]}
        )
    datos["sondeos_ofrecidos"] = ofrecidos


def encolar_si_es_excepcion(
    cola: PuertoColaDeRevision,
    mensaje: str,
    salida,
    clase: str | None = None,
    estudiante: str = "",
    sesion: str = "",
):
    """Añade el turno a la cola de supervisión si degradó o si respondió sin
    fuente — la mitad de «muestreo y excepción» que este sistema sabe hacer
    hoy. Ver el docstring de `dominio/puertos/supervision.py` sobre la otra
    mitad, el muestreo, que no está implementada.

    `clase` la resuelve `clase_de_la_sesion()` antes de llamar aquí — sigue
    pudiendo ser `None` si la sesión no está en ninguna clase o está en más
    de una, y en ese caso el ítem entra igual: `FiltrosDeCola` sigue pudiendo
    filtrar por urgencia y tipo sin ella.

    Fase 8 · **devuelve el elemento encolado, o `None`**. Antes no devolvía
    nada, y la instrumentación de la derivación necesita el identificador que
    la cola acaba de asignar: sin él, la clave de idempotencia tendría que
    inventarse a partir del turno y un mismo turno derivado dos veces por dos
    motivos distintos colapsaría en un solo evento.
    """
    if salida.degradado is not None:
        return cola.agregar(NuevoItem(
            urgencia="normal", clase=clase, tipo=TIPO_DEGRADADO, mensaje=mensaje,
            turno={"situacion": "degradado", **asdict(salida.degradado)},
            estudiante=estudiante, sesion=sesion,
        ))
    if salida.cuerpo is not None and salida.cuerpo.procedencia.origen == "sin-fuente":
        return cola.agregar(NuevoItem(
            urgencia="normal", clase=clase, tipo=TIPO_SIN_FUENTE, mensaje=mensaje,
            turno=asdict(salida.cuerpo),
            estudiante=estudiante, sesion=sesion,
        ))
    return None


def contexto_retomado(
    adaptador_historial, identificador_sesion: str, datos: dict
) -> list[dict] | None:
    """El `historial_reciente` de una conversación pasada, listo para
    sembrar la sesión en vivo — o `None` si no aplica.

    Es lo que hace posible escribir directamente en un hilo pasado y que
    el tutor responda con memoria real de él, en vez de con el contexto
    —vacío o ajeno— de la sesión en vivo. `08-Contrato-del-Turno.md` §13
    seguía sin ofrecer esto cuando se escribió; el frontend manda
    `retomar_sesion` solo en el primer turno de cada retoma, así que los
    siguientes ya construyen sobre el `historial_reciente` que este turno
    deja escrito.

    Mismo candado de privacidad que `GET /api/historial/{sesion}`: sujeto
    AUTENTICADO (`identificador_estable`, `D-30`) y el sujeto va en el
    `WHERE` del adaptador —una sesión ajena no devuelve nada que distinga
    «no existe» de «no es tuya»—. `None` de vuelta significa **no se pudo
    confirmar que sea suya**, nunca un error de contenido: el turno sigue
    con el contexto que ya traía la sesión en vivo.

    ⚠️ **`None` y `[]` no significan lo mismo, y el llamador —`rutas/turno.py`—
    decide a qué conversación archivar este turno mirando cuál de los dos
    volvió.** `None` es «no se pudo verificar que `identificador_sesion` sea
    de este sujeto» —la única razón para NO archivar aquí—. `[]` es «se
    verificó, pero no hay un intercambio completo que sembrar como
    memoria» —que **no** es motivo para negarse a archivar—. Antes del
    2026-08-22 esta función confundía las dos cosas: un turno degradado no
    deja `bloques` (`http/turno.py::_entradas_del_turno`), así que su mitad
    del par nunca se completaba, `completos` quedaba vacío, la función
    devolvía `None` como si la sesión no fuera del sujeto, y el turno que
    debía archivarse en la conversación retomada se archivaba en la EN VIVO
    en su lugar —el síntoma reportado como «se actualiza la hora/turnos de
    otra fila»—. La propiedad ya la confirmó `mensajes` (línea de abajo, vía
    el `WHERE` del adaptador); la ausencia de un par completo es un dato
    sobre la MEMORIA a sembrar, no sobre la TITULARIDAD de la sesión.
    """
    if adaptador_historial is None:
        return None
    sujeto = datos.get("identificador_estable") or ""
    if not sujeto:
        return None
    try:
        # `EQ-023` · retomar un hilo **es** consultar una conversación, así que
        # se audita igual que `GET /api/historial/{sesion}`, en la misma
        # transacción. Si la constancia no se puede escribir, no se devuelve el
        # contexto y el turno se queda en la conversación en curso: es el mismo
        # desenlace conservador que ya tenía cualquier otro fallo de lectura.
        mensajes = adaptador_historial.hilo_de(
            identificador_sesion, sujeto, actor=sujeto, operacion=OPERACION_CONSULTA
        )
    except ErrorDeAlmacen:
        return None
    if not mensajes:
        return None

    pares: dict[int, dict] = {}
    for m in mensajes:
        par = pares.setdefault(m["turno"], {})
        if m["autor"] == "estudiante":
            par["estudiante"] = m["contenido"]
        else:
            # Igual que se arma más abajo para el turno en vivo: la prosa y
            # la notación citada de los bloques, no `contenido` crudo —ese
            # es el que trae un bloque `grafica` en JSON, por ejemplo—. Un
            # turno degradado no deja bloques —`_entradas_del_turno` no se
            # los pone—, así que su «tutor» sale vacío y el par no cuenta
            # como completo más abajo. Eso es correcto PARA LA MEMORIA: no
            # hay nada útil que sembrarle al modelo de un intercambio que
            # falló. No lo es para la titularidad, que ya se confirmó arriba.
            par["tutor"] = " ".join(
                b["contenido"] for b in m.get("bloques", [])
                if b.get("tipo") in ("prosa", "notacion", "expresion-citada")
            )

    # `mensajes` no vacío YA confirmó que `identificador_sesion` es de este
    # sujeto —es la propiedad que `rutas/turno.py` necesita para archivar
    # aquí—. Que no haya par completo que sembrar es una razón para volver
    # con la lista vacía, NUNCA con `None`: `None` haría que el turno se
    # archivara en la sesión en vivo aunque la sesión retomada sí sea suya.
    recuperar_ejercicio_del_historial(datos, list(pares.values()))
    completos = [p for p in pares.values() if p.get("estudiante") and p.get("tutor")]
    reconstruir_contexto_factual(datos, identificador_sesion, [
        {**par, "turno_id": str(turno)} for turno, par in pares.items()
        if par.get("estudiante") and par.get("tutor")
    ])
    return completos[-6:]


@dataclass(frozen=True)
class DependenciasDelTurno:
    """Lo que la ruta del turno necesita de fuera, agrupado por composición.

    Eran seis parámetros posicionales y el hito B2 añade el séptimo —quién
    autoriza el tutor—. Siete posiciones del mismo estilo son siete
    oportunidades de intercambiar dos sin que nada falle; con campos nombrados,
    componer mal se ve al escribirlo.

    `estado_vigente` admite `None` para no romper a quien componga sin base, y
    esa ausencia **cierra** la ruta: sin poder leer el consentimiento persistido
    no se puede afirmar que alguien esté habilitado (`EQ-024`).
    """

    sesiones: Sesiones
    adaptador: AdaptadorTurno
    limitador: LimitadorDePeticiones
    clases_almacen: PuertoClases
    cola: PuertoColaDeRevision
    adaptador_historial: object | None = None
    estado_vigente: PuertoEstadoVigente | None = None
    #: Fase 8 · los puntos canónicos de telemetría. Opcional y con un valor por
    #: defecto que no instrumenta, para que componer sin base —o sin esta
    #: entrega— deje la ruta exactamente como estaba.
    instrumentador: Instrumentador = SIN_INSTRUMENTAR


def _turno_emitido(salida) -> str:
    """El identificador del turno, venga de la respuesta o de la degradación.

    Los dos caminos lo llevan —`CuerpoTurno.turno` y `Degradado.turno`— y hace
    falta el de los dos: un turno degradado se envió igual, y excluirlo de la
    telemetría dejaría la actividad medida por debajo justo en los periodos
    con más incidencias.
    """
    if salida.cuerpo is not None:
        return salida.cuerpo.turno
    if salida.degradado is not None:
        return salida.degradado.turno
    return ""


def _instrumentar_el_turno(
    instrumentador: Instrumentador,
    sello: SelloDelTurno,
    salida,
    instante_envio,
    encolado,
    notacion: str,
) -> None:
    """Los tres hechos que este turno pudo producir, en su orden real.

    Se sale sin hacer nada si el turno no llegó a tener identificador: sin él
    no hay clave de idempotencia estable, y una clave inventada convertiría
    cada reintento en una observación más.
    """
    if not sello.turno:
        return
    instrumentador.turno_enviado(sello, notacion=notacion, ocurrido_en=instante_envio)
    instrumentador.turno_respondido(
        sello,
        ResultadoDelTurno(
            nivel=salida.cuerpo.nivel if salida.cuerpo is not None else "",
            procedencia=(
                salida.cuerpo.procedencia.origen if salida.cuerpo is not None else ""
            ),
            degradado=salida.degradado is not None,
            version_modelo=getattr(salida, "version_modelo", ""),
            version_corpus=instrumentador.version_del_corpus(),
        ),
    )
    if encolado is not None:
        instrumentador.supervision_derivada(
            sello,
            item=encolado.identificador,
            tipo_de_item=encolado.tipo,
            urgencia=encolado.urgencia,
        )


def crear_router(deps: DependenciasDelTurno) -> APIRouter:
    sesiones = deps.sesiones
    adaptador = deps.adaptador
    limitador = deps.limitador
    clases_almacen = deps.clases_almacen
    cola = deps.cola
    adaptador_historial = deps.adaptador_historial
    estado_vigente = deps.estado_vigente
    instrumentador = deps.instrumentador
    # Paquete J · un turno a la vez POR CONVERSACION, y reintentos que no
    # cuentan dos veces. Los dos almacenes son de este router —no del
    # proceso—: dos conversaciones distintas no se estorban, que es la
    # diferencia entre serializar y volver el servidor secuencial.
    candados = CandadoPorConversacion()
    registro_idempotencia = RegistroDeIdempotencia()
    router = APIRouter()

    def _ndjson(emitidas: tuple[bytes, ...]) -> Response:
        return StreamingResponse(iter(emitidas), media_type="application/x-ndjson")

    @router.post("/api/turno")
    async def turno(peticion: Request) -> Response:
        """El borde del turno, con el contrato de concurrencia del paquete J.

        Tres cosas antes de dejar entrar el turno, y en este orden:

        1. **las guardas de siempre** —sesión, límite, acceso—, que no cuestan
           nada y rechazan antes de tomar ningún candado;
        2. **el candado de ESTA conversación**, para que dos turnos suyos no
           lean el mismo estado y se sobrescriban. Otras conversaciones siguen
           en paralelo: no es un candado de proceso;
        3. **la clave de idempotencia**, si el cliente mandó una. Con el
           candado ya tomado, un reintento que llegó mientras el primero corría
           encuentra aquí la respuesta ya calculada en vez de contar otro turno.
        """
        datos, rechazo = rechazo_previo(sesiones, limitador, peticion, estado_vigente)
        if datos is None:
            # `rechazo_previo` devuelve siempre exactamente uno de los dos. El
            # `or` no es defensa contra el flujo de hoy sino contra el de
            # mañana: si alguien añade una guarda y olvida su respuesta, esta
            # ruta rechaza en vez de seguir con `datos` en `None`.
            return rechazo or JSONResponse({"detalle": "sin sesión"}, status_code=401)

        cuerpo = await json_del_cuerpo(peticion)
        conversacion_activa = str(datos.get("conversacion") or "")
        if getattr(adaptador, "continuidad", False):
            conversacion_activa = str(cuerpo.get("retomar_sesion") or cuerpo.get("sesion") or conversacion_activa)
            if conversacion_activa != datos.get("conversacion"):
                sujeto = datos.get("identificador_estable", "")
                try:
                    mensajes = await run_in_threadpool(
                        adaptador_historial.hilo_de, conversacion_activa, sujeto,
                        actor=sujeto, operacion=OPERACION_CONSULTA,
                    ) if adaptador_historial else []
                except ErrorDeAlmacen:
                    return JSONResponse({"detalle": "No se pudo recuperar esta charla. Reintenta."}, status_code=503)
                if not mensajes:
                    return JSONResponse({"detalle": "No se pudo recuperar esta charla."}, status_code=404)
        clave = clave_de(cuerpo)
        huella = RegistroDeIdempotencia.huella_de(cuerpo)

        candado = candados.obtener(conversacion_activa)
        await candado.acquire()
        try:
            if clave:
                recordada = registro_idempotencia.recordada(conversacion_activa, clave)
                if recordada is not None and recordada.huella != huella:
                    # Dos turnos distintos presentándose como el mismo. Elegir
                    # uno en silencio dejaría al estudiante sin saber cuál se
                    # contó, así que se dice.
                    candado.release()
                    return JSONResponse(
                        {
                            "detalle": (
                                "esa clave de idempotencia ya se usó en esta "
                                "conversación con otro mensaje"
                            )
                        },
                        status_code=409,
                    )
                if recordada is not None:
                    candado.release()
                    return _ndjson(recordada.lineas)

        except BaseException:
            candado.release()
            raise

        def recordar(emitidas):
            if clave:
                registro_idempotencia.recordar(conversacion_activa, clave, huella, emitidas)

        emision = EmisionDelTurno(
            lambda al_iniciar: _turno_completo(datos, cuerpo, al_iniciar),
            recordar, candado.release,
        )
        return emision.respuesta()

    async def _turno_completo(datos: dict, cuerpo: dict, al_iniciar=None) -> tuple[bytes, ...]:
        if not getattr(adaptador, "continuidad", False):
            return await _procesar_turno(datos, cuerpo, al_iniciar)
        from dominio.modelo.continuidad import ejercicio

        destino = str(cuerpo.get("retomar_sesion") or cuerpo.get("sesion") or datos["conversacion"])
        if adaptador_historial is None or not hasattr(adaptador_historial, "abrir_estado_operativo"):
            raise RuntimeError("continuidad requiere almacenamiento operativo")
        checkpoint = await run_in_threadpool(
            adaptador_historial.abrir_estado_operativo, datos["identificador_estable"], destino,
        )
        try:
            recordada = checkpoint.respuesta_recordada(clave_de(cuerpo), RegistroDeIdempotencia.huella_de(cuerpo))
            if recordada is not None:
                return recordada
            trabajo = deepcopy(datos)
            trabajo.pop("continuidad_completada", None)
            estado = deepcopy(checkpoint.estado)
            # Hilos antiguos: una única reconstrucción conservadora, sin inventar veredictos.
            if not estado.get("voces") and destino != datos.get("conversacion"):
                mensajes = await run_in_threadpool(
                    adaptador_historial.hilo_de, destino, datos["identificador_estable"],
                    actor=datos["identificador_estable"], operacion=OPERACION_CONSULTA,
                )
                from dominio.modelo.continuidad import preparar
                voces = []
                for m in mensajes:
                    if m["autor"] == "estudiante":
                        estado = preparar(estado, m["contenido"])
                        voces.append({"estudiante": m["contenido"]})
                    elif voces and m.get("bloques"):
                        voces[-1]["tutor"] = " ".join(
                            f"${b['contenido']}$" if b.get("tipo") in ("notacion", "expresion-citada") else b["contenido"]
                            for b in m["bloques"] if b.get("tipo") in ("prosa", "notacion", "expresion-citada")
                        )
                estado["voces"] = voces[-6:]
                estado["aclaracion"] = ""
            trabajo.update(conversacion=destino, estado_operativo=estado,
                           ejercicio_activo=ejercicio(estado),
                           expresion_previa=(ejercicio(estado) or {}).get("expresion", ""),
                           estado_pedagogico=estado.get("pedagogia", {}),
                           sin_adaptacion=bool(estado.get("pedagogia", {}).get("sin_adaptacion")),
                           historial_reciente=deepcopy(estado.get("voces", [])),
                           contexto_factual={"total": 0, "turnos": []}, sesion_contexto_factual="")
            trabajo.pop("retomando_activo", None)
            lineas = await _procesar_turno(trabajo, {**cuerpo, "retomar_sesion": ""}, al_iniciar)
            resuelto = trabajo.get("estado_operativo")
            if resuelto is not None and trabajo.get("continuidad_completada"):
                resuelto["pedagogia"] = trabajo.get("estado_pedagogico", {})
                # La adaptación afectiva no se transforma en perfil longitudinal por guardar un hilo.
                resuelto["pedagogia"].pop("afectivo", None)
                resuelto["voces"] = trabajo.get("historial_reciente", [])[-6:]
                checkpoint.recordar_respuesta(resuelto, clave_de(cuerpo), RegistroDeIdempotencia.huella_de(cuerpo), lineas)
                await run_in_threadpool(checkpoint.guardar, resuelto)
            return lineas
        finally:
            await run_in_threadpool(checkpoint.cerrar)

    async def _procesar_turno(datos: dict, cuerpo: dict, al_iniciar=None) -> tuple[bytes, ...]:
        """El turno entero, ya serializado. Se ejecuta con el candado tomado.

        Devuelve las líneas en vez de una respuesta porque quien decide qué se
        devuelve —una emisión nueva o una recordada— es la envoltura de arriba,
        y porque una respuesta ya construida no se puede guardar para reintentar.
        """
        mensaje = str(cuerpo.get("mensaje") or "")
        # `EQ-031` · qué puede producir este turno, decidido UNA vez y desde el
        # rol real de la sesión. Se resuelve aquí arriba, antes de tocar nada,
        # para que cada productor de señales de abajo pregunte a la misma
        # política en vez de repetir la condición con sus propias palabras.
        politica = PoliticaDelTurno.del_contexto(
            datos.get("contexto_de_uso_turno")
            or contexto_de_uso_de(datos.get("rol"))
        )

        # `retomar_sesion`: el cliente escribió directamente en un hilo
        # pasado —ver `Conversacion.svelte::enviar`—. Sembrar
        # `historial_reciente` para que el modelo responda con memoria real
        # no basta: si el turno se registra igual bajo la conversación EN
        # VIVO, la conversación retomada nunca gana fila propia y el hilo que
        # se ve al volver sigue siendo el mismo de antes tras recargar la
        # página. `identificador_sesion_turno` es a qué conversación se
        # archiva ESTE turno; por defecto la conversación en curso, y la
        # retomada solo cuando `contexto_retomado()` -o un turno anterior de
        # este mismo intercambio, ver `retomando_activo` abajo- ya confirmó
        # que es de quien escribe.
        #
        # ⚠️ Desde el hito R1 esto es `datos["conversacion"]` y no el valor de
        # la cookie: son identificadores distintos, y el historial siempre usó
        # —y sigue usando— el de conversación.
        identificador_sesion_turno = datos["conversacion"]
        retomar_sesion = str(cuerpo.get("retomar_sesion") or "").strip()
        if retomar_sesion:
            if datos.get("retomando_activo") == retomar_sesion:
                # Ya se verificó y sembró en un turno anterior de esta misma
                # retoma: no hay que repetir la consulta a Postgres en cada
                # mensaje, solo en el primero.
                identificador_sesion_turno = retomar_sesion
            else:
                # `run_in_threadpool`: es una consulta a Postgres
                # —bloqueante, ver `conexion.py`— y esta ruta es
                # `async def`. Sin esto corre en el hilo del bucle de
                # eventos y bloquea TODO el servidor mientras dura, el
                # mismo motivo por el que `adaptador.manejar()` más abajo
                # también lo lleva.
                contexto = await run_in_threadpool(
                    contexto_retomado, adaptador_historial, retomar_sesion, datos
                )
                # `contexto is None` es «no es tuya, no existe, o no se
                # pudo leer» —mismo candado de privacidad que
                # `GET /api/historial/{sesion}`—, y en los tres casos el
                # turno se queda en la sesión en vivo: nunca se archiva
                # bajo un identificador que no se pudo confirmar como del
                # sujeto que escribe. `[]` —lista vacía, no `None`— SÍ pasa
                # este `if`: la propiedad ya se confirmó dentro de
                # `contexto_retomado()`, lo único que faltó fue un par
                # completo que sembrar como memoria. Ver su docstring.
                if contexto is not None:
                    datos["historial_reciente"] = contexto
                    datos["retomando_activo"] = retomar_sesion
                    identificador_sesion_turno = retomar_sesion

        # `PM-B05` · las señales del filtro 6 se derivan AQUÍ, que es donde se
        # conoce la sesión. El turno no puede deducir de su propio texto cuántos
        # intentos lleva el estudiante, y el cliente no puede mandarlo o se
        # escalaría a sí mismo. Ver `TurnoEntrante`.
        # Fase 4 · el estado pedagógico de la conversación, que es el que
        # decide (política F.6). Los contadores ya no se suman aquí: los lleva
        # `dominio/pedagogia/problema.py` al cerrar el turno, porque contar un
        # intento exige saber si repite algo ya escrito **en este problema**, y
        # eso no se puede saber mirando sólo el mensaje.
        estado_pedagogico = _preparar_estado_del_turno(datos, mensaje, getattr(adaptador, "continuidad", False))
        # `PM-B21` · misma razón que las señales: la clase es contexto de
        # sesión, no del turno. Se resuelve una sola vez y se reutiliza para
        # el dominio y para la cola de supervisión.
        clase = clase_de_la_sesion(clases_almacen, sujeto_de(datos)) if politica.resuelve_matricula else None
        # `PM-B10`/`PM-B15` · el sujeto del perfil versionado. Vacío cuando
        # `RL-09` no habilita el módulo conductual —sin modo piloto y sin edad
        # declarada—: `AdaptadorTurno` ya trata el sujeto vacío como «no
        # persistas», así que el gate de `RL-09` no necesita ningún mecanismo
        # nuevo ni tocar `ContextoTurno`, que era el coste que `DD-26` evita.
        # ⚠️ El filtro 3 SIGUE calculando `ctx.señales` para ese turno y el
        # arbitraje las usa; lo que no ocurre es que nada se guarde. Cortar
        # también el cómputo es la alternativa que `DD-26` descartó, y no se
        # hace por la puerta de atrás.
        identificador_titular, identificador_sujeto = claves_del_titular(datos)
        # `EQ-031` · segunda barrera. `claves_del_titular()` ya devolvería el
        # sujeto conductual vacío si `RL-09` no habilitara el módulo, pero el
        # modo piloto lo habilita por defecto (`DD-26` §4), así que para un
        # docente vendría relleno. Se vacía aquí, con su nombre, en vez de
        # confiar en que otra guarda lo impida: es la misma lección que
        # `permite_escritura_conductual()` dejó escrita —una protección que
        # vive en el valor de una variable y no en una comprobación se pierde
        # en cuanto alguien rellena esa variable por otra vía—.
        if not politica.escribe_perfil_longitudinal:
            identificador_sujeto = ""
        entrante = TurnoEntrante(
            sesion=identificador_sesion_turno,
            mensaje=mensaje,
            continuidad=datos.get("estado_operativo") if getattr(adaptador, "continuidad", False) else None,
            # `EQ-016`, hito B3 · lo anotó `rechazo_previo()` con el mismo estado
            # que usó para autorizar. Ver `_rechazo_por_acceso()`.
            consentimiento_evento=datos.get("consentimiento_evento"),
            momento=str(cuerpo.get("momento") or ""),
            señales=Señales(
                # Fase 4 · los contadores son **del problema activo**, no de la
                # sesión: `dominio/pedagogia/problema.py` los lleva, y hasta
                # ahora tres intentos repartidos entre tres ejercicios abrían el
                # desarrollo del cuarto. Las conductuales siguen llegando en
                # `None` desde aquí: las produce el filtro 3, y una condición
                # que no se puede evaluar es distinta de una que no se cumple.
                intentos_en_el_problema=estado_pedagogico.problema.intentos,
                insistencias=estado_pedagogico.problema.insistencias,
                peticion_confirmada=estado_pedagogico.problema.peticion_confirmada,
            ),
            estado_conversacion=estado_pedagogico,
            # Política F.11 · la puerta se comprueba **aquí**, en el borde de
            # escritura, y no se deja al azar de que el sujeto viniera vacío.
            # `EQ-031` · tercera barrera, y la que de verdad decide en el borde
            # de escritura: sin ella, un despliegue que algún día rellenara el
            # sujeto por otra vía volvería a escribir perfil.
            escritura_longitudinal_permitida=(
                politica.escribe_perfil_longitudinal
                and aviso_legal.permite_escritura_conductual(
                    datos, datos.get("acceso_calculado")
                )
            ),
            clase=clase or "",
            identificador_sujeto=identificador_sujeto,
            # `DD-27` · la clave de supresión, sin gatear. Ver `claves_del_titular`.
            identificador_titular=identificador_titular,
            # `PM-B08` · `None` en todo turno de texto libre, que hoy son
            # todos. Ver `respuesta_al_item_de`.
            # `EQ-031` · un sondeo existe para evaluar. A un profesional no se
            # le clasifica una concepción errónea ni se le guarda el resultado.
            respuesta_al_item=respuesta_al_item_de(cuerpo) if politica.diagnostica else None,
            # `PM-B28` · el tope de frecuencia de los ítems es de la sesión,
            # igual que los contadores del arbitraje.
            estado_de_sondeo=estado_de_sondeo_de(datos) if politica.diagnostica else None,
            expresion_previa=str(datos.get("expresion_previa", "")),
            ejercicio_activo=datos.get("ejercicio_activo"),
            # `PM-B32` · §3.ter del contrato. Se pasa TAL CUAL y no se valida
            # aquí: quien sabe qué notaciones existen es el adaptador
            # simbólico, y una lista de nombres repetida en el borde HTTP se
            # queda vieja el día que se añada una. Una desconocida cae al
            # defecto allí y el turno sigue.
            notacion=str(cuerpo.get("notacion") or ""),
            historial_reciente=tuple(datos.get("historial_reciente", [])),
            contexto_conversacional=(contexto_de_sesion(
                datos, identificador_sesion_turno, mensaje, datos.get("ejercicio_activo"),
            ) if getattr(adaptador, "contexto_reforzado", False) else {}),
            # `EQ-031` · viaja hasta el filtro 12 y se persiste con el turno y
            # con sus dos voces. Es lo que permitirá excluir estas filas de KPI
            # y conjuntos de investigación **sin volver a preguntar por el rol
            # de nadie**, que es lo que un rol revocable no puede contestar.
            contexto_de_uso=politica.contexto,
        )
        # `run_in_threadpool`: `manejar()` es una llamada síncrona por
        # decisión propia —ver su docstring, §12 del contrato— y adentro
        # incluye la llamada de red al proveedor del modelo
        # (`adaptadores/salientes/generacion/deepseek.py`, con `urllib`,
        # también síncrona) y el cómputo simbólico. Sin este hilo aparte,
        # ese tramo —hasta 30 s por turno, el mismo plazo que el cliente
        # espera— bloqueaba el ÚNICO hilo del bucle de eventos de este
        # servidor de un solo proceso: ninguna otra petición se atendía
        # mientras tanto, ni siquiera un reintento de este mismo turno tras
        # que el cliente se rindiera. `08-08-26`, reportado como «reintenté
        # y volvió a fallar».
        #
        # ✅ **Corregido en la revisión R1 · paquete J.** Aquí decía que la
        # ruta no llevaba candado por sesión y que el riesgo era «de bajo
        # costo: una cuenta del arbitraje de más». Con la fase 4 dejó de
        # serlo: los contadores del problema gobiernan la escala de
        # `RF-GEN-05`, así que dos turnos que se pisan pueden **abrir el
        # desarrollo** de un ejercicio que el estudiante no intentó tres
        # veces, o perderle dos que sí hizo. Y el estado ya no es un entero:
        # es el problema activo, sus expresiones vistas, sus episodios y su
        # archivo.
        #
        # El candado lo toma la envoltura de esta función y es **por
        # conversación**, no de proceso: el argumento de entonces —no dejar
        # al reintento haciendo fila detrás de un turno que el cliente ya dio
        # por perdido— se atiende con la clave de idempotencia, que le
        # devuelve la respuesta ya calculada en vez de hacerle esperar por
        # nada. Ver `adaptadores/entrantes/http/concurrencia.py`.
        # Fase 8 · el instante del ENVÍO, tomado antes de la cadena. El evento
        # se escribe después —el identificador del turno lo genera `manejar()`—
        # pero fechado aquí: con la hora de después, un turno lento movería el
        # envío hasta treinta segundos y el intervalo entre sesiones mediría de
        # más.
        instante_envio = datetime.now(UTC)
        manejar_con_progreso = getattr(
            adaptador, "manejar_con_progreso", lambda entrada, _: adaptador.manejar(entrada),
        )
        salida = (await run_in_threadpool(manejar_con_progreso, entrante, al_iniciar)
                  if al_iniciar is not None
                  else await run_in_threadpool(adaptador.manejar, entrante))
        _anotar_continuidad(datos, salida)
        recordar_contexto_factual(
            datos, identificador_sesion_turno, mensaje, salida,
            habilitado=getattr(adaptador, "contexto_reforzado", False),
        )
        if salida.estado_conversacion is not None:
            anotar_el_estado(datos, salida.estado_conversacion)
        # `EQ-031` · los efectos de DESPUÉS del turno, con la misma política.
        #
        # El estado de conversación sí se anota para todos: son los contadores
        # de intentos e insistencias del problema activo, viven en memoria del
        # proceso y son lo que hace que el tutor responda con continuidad. No
        # son evaluación —no se persisten, no se agregan y mueren con la
        # sesión—, y apagarlos dejaría al profesional con un tutor peor sin
        # proteger nada.
        if politica.diagnostica:
            anotar_el_sondeo(datos, salida)
            # `R2-B` · desde el DESENLACE que el dominio decidió, nunca desde el
            # payload que el cliente mandó. Ver `anotar_el_item_contestado`.
            anotar_el_item_contestado(datos, salida.desenlace_del_sondeo)
        encolado = None
        if politica.encola_supervision:
            encolado = encolar_si_es_excepcion(
                cola, mensaje, salida, clase=clase,
                estudiante=identificador_titular,
                sesion=identificador_sesion_turno,
            )

        # Fase 8 · los puntos canónicos. Van DESPUÉS de que el turno esté
        # resuelto y de que la cola haya recibido lo suyo, porque miden lo que
        # ocurrió y no lo que se intentó. `instrumentador` absorbe cualquier
        # fallo: ver `adaptadores/entrantes/http/instrumentacion.py` sobre por
        # qué un turno del estudiante no se pierde por una medición.
        _instrumentar_el_turno(
            instrumentador,
            SelloDelTurno(
                sujeto=identificador_titular,
                conversacion=identificador_sesion_turno,
                turno=_turno_emitido(salida),
                contexto_de_uso=politica.contexto,
                clase=clase or None,
            ),
            salida,
            instante_envio,
            encolado,
            str(cuerpo.get("notacion") or ""),
        )

        # Registrar el turno en el historial reciente de la sesión para memoria continua
        if "historial_reciente" not in datos:
            datos["historial_reciente"] = []
        texto_tutor = ""
        if salida.cuerpo and salida.cuerpo.bloques:
            texto_tutor = " ".join(
                (f"${b.contenido}$" if getattr(adaptador, "continuidad", False) and b.tipo in ("notacion", "expresion-citada") else b.contenido)
                for b in salida.cuerpo.bloques if b.tipo in ("prosa", "notacion", "expresion-citada")
            )
        elif salida.degradado:
            texto_tutor = salida.degradado.explicacion
        if texto_tutor:
            datos["historial_reciente"].append({"estudiante": mensaje, "tutor": texto_tutor})
            datos["historial_reciente"] = datos["historial_reciente"][-6:]

        def lineas() -> Iterator[bytes]:
            for fase in salida.fases:
                yield (json.dumps(asdict(fase), ensure_ascii=False) + "\n").encode()
            final: dict = {}
            if salida.cuerpo is not None:
                final["cuerpo"] = asdict(salida.cuerpo)
            if salida.degradado is not None:
                # `situacion` la pone este adaptador y no el dominio: §8.3 la
                # declara y `Degradado` no la lleva. Es el borde traduciendo,
                # que es exactamente lo que le toca.
                final["degradado"] = {"situacion": "degradado", **asdict(salida.degradado)}
            yield (json.dumps(final, ensure_ascii=False) + "\n").encode()

        return tuple(lineas())

    return router


def _preparar_estado_del_turno(datos, mensaje, continuidad):
    estado_pedagogico = estado_de_conversacion_de(datos)
    if not continuidad:
        estado_pedagogico = reiniciar_si_cambio_el_problema(
            estado_pedagogico, mensaje, datos.get("ejercicio_activo")
        )
    recordar_preferencias(datos, mensaje)
    # La preferencia se copia en los DOS sentidos · paquete F. Antes sólo
    # se copiaba el `True`, así que reactivar la adaptación en la sesión no
    # llegaba nunca al estado que decide y la orden del estudiante moría
    # aquí.
    estado_pedagogico = dataclasses_replace(
        estado_pedagogico, sin_adaptacion=bool(datos.get("sin_adaptacion"))
    )
    # Paquete F · la corrección se consume **antes** de que el turno decida,
    # igual que el reinicio por cambio de problema. Aplicarla al cerrar
    # dejaría que este turno —el que corrige— se decidiera con la inferencia
    # que el estudiante acaba de negar, que es justo lo que se corrige.
    estado_pedagogico = corregir_inferencia_si_lo_pide(estado_pedagogico, mensaje)
    # `PM-B31` · antes de armar el turno: si este mensaje trae expresión,
    # es la que la conversación recuerda a partir de ahora.
    if not continuidad:
        recordar_ejercicio(datos, mensaje)
        recordar_expresion(datos, mensaje)
    return estado_pedagogico


def _anotar_continuidad(datos, salida):
    if getattr(salida, "continuidad", None) is not None and salida.cuerpo is not None:
        from dominio.modelo.continuidad import ejercicio
        datos["estado_operativo"] = salida.continuidad
        datos["ejercicio_activo"] = ejercicio(salida.continuidad)
        datos["continuidad_completada"] = True
