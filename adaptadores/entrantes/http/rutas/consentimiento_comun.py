"""
consentimiento_comun.py — Lo que comparten las rutas del recorrido (`D1B`)
===========================================================================

Los puertos que la composición cablea y las cuatro traducciones a JSON que el
recorrido de `EQ-020`/`EQ-021` usa desde más de un módulo.

Por qué se separa de `rutas/consentimiento.py`
-------------------------------------------------------
Porque `D1B` añade la ruta transaccional de la decisión conjunta, y esa ruta
necesita exactamente lo mismo que las de aceptar y revocar: la agrupación de
puertos, el estado vigente con su acceso calculado y la serialización del estado
y de los recibos.

Dejarlo donde estaba obligaba a una de dos cosas, y las dos malas: escribir otro
bloque grande dentro de un archivo que ya rondaba las 800 líneas, o que el módulo
nuevo importara del viejo y el viejo del nuevo —un ciclo, porque
`consentimiento.py` incluye el router de la decisión conjunta—.

Aquí no hay ninguna ruta. Sólo el tipo que las compone y las funciones que
traducen lo que el dominio devuelve. la guía interna de mantenimiento pide separar por
responsabilidad; ésta es «cómo se le cuenta al cliente el estado del recorrido»,
y es una sola.


"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import mantenimiento
from dominio.modelo.acceso import AccesoCalculado, calcular_acceso, permite_tutoria_academica
from dominio.modelo.consentimiento import Alcance
from dominio.modelo.redecision import (
    AccionesDeDecision,
    DimensionDecidible,
    acciones_disponibles,
)
from dominio.puertos.almacen import AlmacenNoConfigurado, AlmacenNoDisponible

if TYPE_CHECKING:  # pragma: no cover
    from dominio.modelo.acceso import EstadoVigente
    from dominio.puertos.almacenamiento_privado import PuertoAlmacenamientoPrivado
    from dominio.puertos.consentimiento_versionado import (
        PuertoEventosDeConsentimiento,
        PuertoVersionesDeConsentimiento,
    )
    from dominio.puertos.decision_conjunta import PuertoDecisionConjunta
    from dominio.puertos.estado_vigente import PuertoEstadoVigente
    from dominio.puertos.gobierno import PuertoNotificacion
    from dominio.puertos.identidad import PuertoIdentidad
    from dominio.puertos.instantaneas import PuertoInstantaneasDeConsentimiento
    from dominio.puertos.menores import (
        PuertoAsentimiento,
        PuertoEvidenciaDelRepresentante,
    )


@dataclass(frozen=True)
class Repositorios:
    """Los ocho puertos que este recorrido consume, agrupados por composición.

    No es un contenedor de servicios: es un parámetro con nombre. `crear_router`
    ya recibía cinco dependencias antes de B2, y añadir siete más habría dejado
    una firma de doce posiciones donde cualquier reordenamiento pasa
    desapercibido —y donde dos puertos del mismo tipo se pueden intercambiar sin
    que nada falle—.

    `dataclass` con campos nombrados y no un `dict`: cada campo tiene su tipo, y
    quien componga mal lo sabrá al escribirlo y no en la primera petición.

    ⚠️ `decision_conjunta` **no tiene valor por defecto**, y es deliberado
    (`D1B`). Un `None` por defecto habría dejado que una composición se olvidara
    de cablearlo y que la ruta de la única acción visible fallara en producción
    con un `AttributeError` en vez de en el momento de componer.

    ⚠️ `notificacion` tampoco lo tiene, y por el mismo motivo (`D2`). Un
    `NotificacionRegistrada()` por defecto habría sido peor que un `None`: una
    composición que se olvidara de cablear Resend seguiría funcionando, seguiría
    devolviendo `aviso_enviado: false` y nadie tendría por qué sospechar que el
    canal estaba puesto y no se estaba usando. Es la MISMA instancia que recibe
    `RepositoriosDeGobierno`; ver `aplicacion.py`.
    """

    identidades: PuertoIdentidad
    versiones: PuertoVersionesDeConsentimiento
    eventos: PuertoEventosDeConsentimiento
    asentimientos: PuertoAsentimiento
    evidencias: PuertoEvidenciaDelRepresentante
    estado_vigente: PuertoEstadoVigente
    almacenamiento: PuertoAlmacenamientoPrivado
    decision_conjunta: PuertoDecisionConjunta
    notificacion: PuertoNotificacion
    #: `§8` · de dónde se lee el documento publicado de una versión. Es el MISMO
    #: adaptador que `versiones` cuando hay base; se declara aparte porque son
    #: dos contratos distintos y porque una composición sin instantáneas —o un
    #: doble de prueba escrito antes de que esto existiera— tiene que seguir
    #: funcionando.
    #:
    #: ⚠️ Con valor por defecto, al revés que `decision_conjunta`, y por un
    #: motivo opuesto: aquello es la única acción visible del recorrido y
    #: olvidarlo rompería producción en silencio; esto es una lectura añadida
    #: cuya ausencia la ruta declara —`instantanea: null`— en vez de fingir.
    instantaneas: PuertoInstantaneasDeConsentimiento | None = None


def leer_estado(repos: Repositorios, sujeto: str):
    """El estado vigente y el acceso calculado, o la respuesta que los niega.

    Devuelve `(estado, acceso, None)` o `(None, None, respuesta)`. Todas las
    rutas del recorrido empiezan igual, y tenerlo en un sitio evita que una
    olvide el `except` y responda como si la base hubiera contestado.
    """
    try:
        estado = repos.estado_vigente.estado_vigente(sujeto)
    except (AlmacenNoConfigurado, AlmacenNoDisponible):
        return None, None, mantenimiento("no se pudo leer el estado de consentimiento")
    if estado is None:
        # La sesión existe pero la persona no está en `persona`. No puede pasar
        # por el camino normal —B1 la registra antes de crear la sesión— así que
        # si pasa es que la fila desapareció: mantenimiento, no un onboarding en
        # blanco que perdería lo ya declarado.
        return None, None, mantenimiento("la identidad de esta sesión no está disponible")
    return estado, calcular_acceso(estado), None


def recibo_de(evento, alcance: Alcance) -> dict:
    """Lo que identifica **el evento real** que se acaba de registrar.

    Los seis campos que el hito R3 exige: secuencia, momento, versión, alcance,
    decisión y huella. Con ellos se puede localizar la fila y recomputar el
    comprobante; sin la secuencia y el momento, dos actos idénticos del mismo
    sujeto sobre la misma versión serían indistinguibles en el recibo.

    Sirve para los tres tipos de acto —`EventoConsentimiento`,
    `EventoAsentimiento` y el `ActoRegistrado` de la decisión conjunta— porque
    los tres comparten esos campos por diseño. Una función por tipo habría
    podido divergir, y entonces el recibo de una revocación y el de una
    aceptación no se leerían igual.

    El nombre del campo de la decisión difiere entre tipos —`estado` en los
    eventos, `decision` en el acto— y se resuelve aquí, en un sitio, en vez de
    en cada llamada.
    """
    decision = getattr(evento, "decision", None) or evento.estado
    return {
        "secuencia": evento.secuencia,
        "momento": evento.momento.isoformat(),
        "version": evento.version,
        "alcance": alcance.value,
        "decision": decision.value,
        "huella": evento.comprobante,
    }


def dimensiones_decidibles(estado: EstadoVigente) -> tuple[DimensionDecidible, ...]:
    """Las dimensiones que una decisión conjunta movería para ESTA persona.

    La misma forma que el adaptador construye desde el cursor, aquí construida
    desde el estado ya leído. **La política es una sola** —
    `dominio/modelo/redecision.py`— y tiene dos consumidores: el que decide si
    escribe y el que publica qué acciones caben. Recalcularla en el navegador
    habría hecho que la persona viera una regla y el servidor aplicara otra.

    Vacío en dos casos, y por motivos distintos:

    - **con un trámite de supresión abierto** · `EQ-022` admite consultar y
      cancelar, no decidir. El servidor rechaza cualquier decisión, así que
      ofrecerla sería ofrecer una acción que no puede terminar;
    - **sin edad declarada** · no se sabe si la persona tiene una dimensión o
      dos, y ofrecer una decisión sin saber cuántos actos produce sería
      adivinar. El recorrido pide antes el perfil.
    """
    if estado.eliminacion_solicitada:
        # `EQ-022` · durante el trámite no hay ninguna decisión que ofrecer, y
        # da igual cómo estén las dimensiones: pendientes, mixtas o rechazadas.
        # Sin esta línea la política diría «hay que decidir» justo cuando el
        # servidor va a rechazar cualquier decisión, y la pantalla ofrecería una
        # acción que no puede terminar.
        return ()
    perfil = estado.perfil
    if perfil is None or perfil.edad is None:
        return ()
    dimensiones = [
        DimensionDecidible(
            alcance=Alcance.TITULAR,
            estado=estado.consentimiento.value,
            version=estado.version_consentimiento,
            version_requerida=estado.requeridas.titular,
            categoria_del_acto=estado.categoria_edad_consentimiento,
            categoria_actual=perfil.categoria_de_edad,
        )
    ]
    if estado.es_menor:
        dimensiones.append(
            DimensionDecidible(
                alcance=Alcance.ASENTIMIENTO,
                estado=estado.asentimiento.value,
                version=estado.version_asentimiento,
                version_requerida=estado.requeridas.asentimiento,
            )
        )
    return tuple(dimensiones)


def acciones_de_decision(estado: EstadoVigente) -> AccionesDeDecision:
    """Qué admite la política de redecisión para esta persona, ahora."""
    return acciones_disponibles(dimensiones_decidibles(estado))


def version_como_json(version) -> dict:
    """Lo que el cliente necesita de una versión. **El cuerpo no va aquí.**

    ⚠️ Esta nota decía hasta `C1-A`: *«El texto no viaja porque no existe:
    `consentimiento_version` guarda la huella de lo publicado, no lo
    publicado»*. Dejó de ser cierto con la migración 13, que le dio al documento
    una tabla propia e inmutable.

    Lo que sigue siendo cierto es que **no viaja en esta respuesta**, y por otro
    motivo: un documento son páginas, y el estado del recorrido se pide en cada
    pantalla. Se lee aparte, por código, en
    `GET /api/consentimiento/version/{codigo}/texto`, que además recalcula el
    SHA-256 antes de servirlo.

    `documento_disponible` es **información, no seguridad** · `C1-A`
    -------------------------------------------------------------------
    Va para que la interfaz pueda decir *por qué* no se puede decidir en vez de
    quedarse muda. Quien lo impide no es este campo: desde la migración 14 una
    versión sin instantánea válida **no es la requerida**, así que el servidor
    ni siquiera la ofrece y el disparador rechaza cualquier acto contra ella.

    Por eso vale `True` en toda versión que llegue aquí como requerida — y se
    manda igualmente: un cliente que lo leyera como condición estaría leyendo la
    verdad, y el día que esta función sirva una versión histórica el campo dirá
    lo que corresponda sin que haya que acordarse de añadirlo.
    """
    return {
        "codigo": version.codigo,
        "alcance": version.alcance.value,
        "finalidades": sorted(f.value for f in version.finalidades),
        "huella_contenido": version.huella_contenido,
        "vigente_desde": version.vigente_desde.isoformat(),
        "vigente_hasta": version.vigente_hasta.isoformat() if version.vigente_hasta else None,
        "documento_disponible": True,
    }


def estado_como_json(estado: EstadoVigente, acceso: AccesoCalculado) -> dict:
    """El estado que el recorrido pinta. Sin datos de nadie más y sin texto libre.

    `asentimiento.al_dia` lo añadió `D1B`: la única acción visible tiene que
    saber si al menor le falta **algo** —no sólo si el titular está al día— y
    deducirlo en el navegador comparando la versión con la requerida habría
    puesto en el cliente una regla que ya vive en `dominio/modelo/acceso.py`.

    `decision` lo añadió `D1B` bis por el mismo motivo llevado hasta el final:
    con el estado mixto, «¿hay algo que decidir?» dejó de poder deducirse de dos
    banderas y pasó a ser una política. Se resuelve en el servidor y se publica.
    """
    perfil = estado.perfil
    return {
        "acceso": acceso.value,
        "tutoria_academica_sin_investigacion": (
            permite_tutoria_academica(estado)
        ),
        "perfil": {
            "completo": estado.perfil_completo,
            "pendientes": list(perfil.campos_pendientes) if perfil else ["edad", "facultad", "programa", "semestre", "clase"],
            "edad": perfil.edad if perfil else None,
            "facultad": perfil.facultad if perfil else "",
            "programa": perfil.programa if perfil else "",
            "semestre": perfil.semestre if perfil else None,
            "clase_vinculada": perfil.clase_vinculada if perfil else False,
        },
        "consentimiento": {
            "estado": estado.consentimiento.value,
            "version": estado.version_consentimiento,
            "al_dia": estado.consentimiento_al_dia,
        },
        "asentimiento": {
            "estado": estado.asentimiento.value,
            "version": estado.version_asentimiento,
            "al_dia": estado.asentimiento_al_dia,
        },
        "representante": {
            "estado": estado.representante.value,
            "motivo": estado.motivo_representante or None,
            "limite": (
                estado.limite_representante.isoformat()
                if estado.limite_representante
                else None
            ),
        },
        "versiones_requeridas": {
            "titular": estado.requeridas.titular,
            "asentimiento": estado.requeridas.asentimiento,
            "representante": estado.requeridas.representante,
        },
        # `D1B` bis · qué admite la POLÍTICA de redecisión conjunta, resuelta en
        # el servidor. `requerida` dice si el recorrido está pidiendo decidir;
        # los dos booleanos, qué acción cabe. **No dicen si hay documento
        # publicado**: eso lo responde `versiones_requeridas`, y la interfaz
        # necesita las dos cosas —sin política no sabe si ofrecer las acciones,
        # sin versión no puede habilitarlas—.
        "decision": _decision_como_json(acciones_de_decision(estado)),
    }


def _decision_como_json(acciones: AccionesDeDecision) -> dict:
    return {
        "requerida": acciones.requerida,
        "puede_aceptar": acciones.puede_aceptar,
        "puede_rechazar": acciones.puede_rechazar,
    }


def responder_con_estado(repos: Repositorios, sujeto: str, extra: dict) -> JSONResponse:
    """El estado recalculado después de escribir, más lo que la ruta añada.

    Se relee **después** del acto y desde la base, en vez de componerlo con lo
    que la ruta cree que cambió: el acceso lo calcula el dominio sobre el estado
    persistido, y adelantarlo aquí sería un éxito optimista de los que `EQ-024`
    prohíbe.
    """
    estado, acceso, fallo = leer_estado(repos, sujeto)
    if fallo is not None:
        return fallo
    return JSONResponse({**estado_como_json(estado, acceso), **extra})
