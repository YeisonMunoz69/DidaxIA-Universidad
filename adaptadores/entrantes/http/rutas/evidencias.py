"""
evidencias.py — La consulta segura de evidencia del representante (C2A)
=========================================================================

Tres rutas de **lectura** para quien revisa: la cola paginada, el detalle de una
evidencia y el archivo. Son la frontera mínima que C2B necesita para que un panel
pueda existir sin adivinar identificadores ni aprobar documentos que nunca mostró.

Por qué un módulo aparte de `rutas/consentimiento.py`
--------------------------------------------------------------
Por la misma razón por la que aquél se separó de `rutas/sesion.py`: son
autoridades distintas. `rutas/consentimiento.py` es **el recorrido del titular**
—qué he declarado, qué he aceptado, qué he cargado— y todas sus rutas responden
sobre la persona de la sesión. Esto es **la consola de quien revisa**: responde
sobre las evidencias de terceros y ninguna de sus rutas tiene sentido sin el rol
de `EQ-023`.

Juntarlas habría dejado un archivo de mil líneas donde una guarda «esto es tuyo»
y una guarda «tú puedes ver lo de otros» se leen igual — y confundirlas es cómo
se publica la cola entera a un estudiante. la guía interna de mantenimiento pide separar
por responsabilidad justamente para esto.

⚠️ **`POST /api/representante/evidencia/{id}/revisar` NO se movió.** Sigue en
`rutas/consentimiento.py` con su contrato y sus pruebas intactos. Mover una ruta
que funciona para que quede bonita al lado de las nuevas habría mezclado una
refactorización con una función nueva, que es lo que la guía interna de mantenimiento
prohíbe en el mismo cambio. Que la de escritura viva en otro archivo es deuda
declarada, no un olvido.

Singular y plural, y no es un descuido
------------------------------------------------
`/api/representante/evidencia` (singular) es lo que **el titular** hace con la
suya: cargarla, y que la revisen. `/api/representante/evidencias` (plural) es la
**colección** que ve quien revisa. La distinción se lee en la URL y no hace falta
mirar el código para saber de qué lado está una ruta.

Dónde se comprueba el permiso, en una frase
--------------------------------------------------
**En el repositorio, contra `rol_asignacion`, dentro de la transacción de la
propia consulta.** Aquí no hay ninguna comparación de correos, ninguna lista y
ningún `if datos["rol"] == ...`: el rol que trae una sesión es `estudiante` o
`docente` (`RP-17`) y no tiene nada que ver con `EQ-023`. Esta capa sólo hace dos
cosas —sacar el actor de la sesión verificada y traducir desenlaces a códigos—, y
las dos son visibles de un vistazo.

Y el orden, que es donde estaba el riesgo
--------------------------------------------------
El rol se exige **antes** de saber si la evidencia existe. Una implementación que
buscara primero y autorizara después respondería 404 para un identificador libre
y 403 para uno ocupado, y eso es un mapa de todas las autorizaciones firmadas por
representantes legales de menores, obtenible con un bucle. Aquí un usuario
autenticado sin rol recibe **exactamente el mismo 403** para un identificador que
existe y para uno que no, porque nadie llegó a mirar.

La referencia al archivo privado no sale de aquí
-------------------------------------------------------
Ni en un cuerpo, ni en una cabecera, ni en un mensaje de error, ni en el nombre
del archivo descargado. `EvidenciaRevisable` no tiene ese campo, así que las dos
rutas de JSON no podrían publicarlo aunque quisieran; la del archivo la obtiene
en una variable local, se la da al almacenamiento y la deja morir ahí.

El motivo de un rechazo, sólo en el detalle
--------------------------------------------------
`EQ-021` exige un motivo comprensible al rechazar, y una decisión de hace dos
semanas deja de serlo sin él: el detalle lo conserva. La cola no lo lleva —ni en
el JSON ni en la consulta— porque una lista no lo consume y es texto libre
escrito por una persona sobre otra.

`revisada_por` no sale por ninguna de las dos. Quién resolvió cada evidencia está
en `representante_revision` y es auditable; publicarlo en la consola convertiría
cada decisión en un señalamiento entre colegas sin que nadie lo haya decidido.

`Content-Disposition` lleva `evidencia-{id}.pdf` y no el nombre de nadie:
`EQ-021` no guarda nombre del representante y esta ruta tampoco lo inventa. Un
archivo descargado acaba en una carpeta compartida, y su nombre es lo primero que
se ve.


"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import mantenimiento, requerir_sesion
from adaptadores.entrantes.http.sesiones import Sesiones
from dominio.modelo.evidencia_revisable import (
    ConsultaInvalida,
    EvidenciaRevisable,
    cursor_desde,
    filtro_desde,
    limite_desde,
)
from dominio.puertos.almacen import (
    AlmacenNoConfigurado,
    AlmacenNoDisponible,
    EscrituraRechazada,
    ReferenciaDesconocida,
)
from dominio.puertos.almacenamiento_privado import (
    AlmacenamientoNoConfigurado,
    AlmacenamientoNoDisponible,
    DocumentoAusente,
    DocumentoPendienteDeConfirmacion,
)

if TYPE_CHECKING:  # pragma: no cover
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
    from dominio.puertos.almacenamiento_privado import PuertoAlmacenamientoPrivado
    from dominio.puertos.menores import PuertoEvidenciaDelRepresentante

#: Lo que se le dice a quien no tiene el rol. **Una sola redacción y sin datos**:
#: es la misma respuesta para una evidencia que existe y para una que no, así que
#: cualquier variación entre los dos casos sería precisamente la filtración que
#: el orden de las comprobaciones evita.
MOTIVO_SIN_ROL = "esta consulta la reserva EQ-023 a un investigador administrador vigente"

#: Lo que se le dice a quien tiene el rol y pregunta por algo que no está.
MOTIVO_NO_EXISTE = "esa evidencia no existe"

#: Las cabeceras del archivo privado. Van juntas porque protegen lo mismo desde
#: cuatro ángulos, y separarlas invita a que alguien añada una ruta con tres.
#:
#: - `no-store` prohíbe guardar la respuesta en cualquier caché, y `private`
#:   repite en negativo lo que de verdad importa: **ninguna caché compartida**
#:   —un proxy institucional, un CDN— puede quedarse la autorización firmada de
#:   un menor y servírsela a la siguiente petición. `max-age=0` y `must-
#:   revalidate` cubren a los intermediarios que ignoran `no-store`;
#: - `nosniff` impide que un navegador adivine el tipo y trate el cuerpo como
#:   otra cosa —HTML, por ejemplo—, que es el camino por el que un archivo subido
#:   se ejecuta en el origen de la aplicación;
#: - `default-src 'none'` deja el documento sin poder pedir nada a ninguna parte,
#:   por si el visor lo abre en un contexto que ejecute algo;
#: - `noopen` es para las versiones de Internet Explorer que abrían la descarga
#:   dentro del sitio. Cuesta una línea.
CABECERAS_DEL_ARCHIVO = {
    "Cache-Control": "no-store, private, max-age=0, must-revalidate",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'",
    "X-Download-Options": "noopen",
}

#: `EQ-021` sólo admite un tipo, y esta ruta sólo sirve ese. No se toma de la
#: fila: si algún día una tuviera otro valor, servirlo tal cual convertiría esta
#: ruta en un servidor de tipos arbitrarios sobre contenido subido.
TIPO_DEL_ARCHIVO = "application/pdf"


@dataclass(frozen=True)
class DependenciasDeEvidencias:
    """Los **dos** puertos que la consola del revisor consume.

    Dos y no los siete de `rutas/consentimiento.Repositorios`, aunque componerlos
    habría sido más cómodo: el radio de acción de un módulo se lee en lo que
    recibe, y unos `Repositorios` completos aquí dirían que estas rutas pueden
    tocar identidad, versiones, eventos y asentimiento — que no pueden y no
    deben. Reducir la superficie es la mitad de la revisión que este archivo se
    va a llevar.
    """

    evidencias: PuertoEvidenciaDelRepresentante
    almacenamiento: PuertoAlmacenamientoPrivado


def _evidencia_como_json(evidencia: EvidenciaRevisable) -> dict:
    """La proyección como cuerpo. **Campo a campo, nunca por reflexión.**

    Un `asdict()` habría sido una línea y habría publicado automáticamente
    cualquier campo que alguien añadiera después al tipo — incluido, el día que
    alguien lo añadiera por comodidad, la referencia al archivo privado. Escribir
    los campos obliga a que publicar uno nuevo sea una decisión.

    `estado` se deriva de la revisión (`EvidenciaRevisable.estado`) y se envía
    junto a `resultado` porque responden a preguntas distintas: `estado` siempre
    tiene valor y sirve para pintar la cola; `resultado` es `null` mientras nadie
    haya decidido, y es lo que distingue «sin revisar» de «revisada».

    ⚠️ **`motivo` no está, y la cola lo usa tal cual.** El texto libre de un
    rechazo lo transporta sólo el detalle (`_detalle_como_json`): una lista
    paginada no lo consume, y arrastrarlo por cada fila de cada página
    multiplicaría la circulación de algo que una persona escribió sobre otra. La
    consulta de la cola tampoco lo pide, así que esto no es la única defensa.
    """
    return {
        "evidencia": evidencia.evidencia,
        "sujeto": evidencia.sujeto_google,
        "intento": evidencia.intento,
        "version": evidencia.version,
        "sha256": evidencia.sha256,
        "tamano_bytes": evidencia.tamano_bytes,
        "tipo_mime": evidencia.tipo_mime,
        "recibido_en": evidencia.recibido_en.isoformat(),
        "estado": evidencia.estado.value,
        "resultado": evidencia.resultado.value if evidencia.resultado else None,
        "revisada_en": evidencia.revisada_en.isoformat() if evidencia.revisada_en else None,
        "estudiante": {
            "nombre": evidencia.estudiante_nombre,
            "clases": list(evidencia.clases),
        },
    }


def _detalle_como_json(evidencia: EvidenciaRevisable) -> dict:
    """El detalle: los mismos campos de la cola **más el motivo**.

    Se escribe como «la cola más uno» y no como una lista propia para que las
    dos no puedan divergir en los campos comunes: si alguien añadiera uno a
    la lista y olvidara el detalle, un panel que abriera una evidencia vería
    desaparecer un dato al hacer clic.

    `motivo` es `null` cuando no hay ninguno —una evidencia sin revisar, o una
    aprobada, que `EQ-021` no obliga a motivar—. Se envía siempre la clave, con
    `null`, en vez de omitirla: un campo ausente y un campo nulo se distinguen
    mal en el cliente, y el primero se lee como «esta versión del backend no lo
    tiene».
    """
    return {**_evidencia_como_json(evidencia), "motivo": evidencia.motivo or None}


def _sin_rol() -> JSONResponse:
    """403 y no 404 para quien no tiene el rol.

    Las dos opciones ocultan igual de bien si la evidencia existe —porque la
    respuesta es la misma para cualquier identificador—, así que se elige la que
    además es cierta: 403 dice «te conozco y no puedes», que es exactamente lo
    que ocurre, y le ahorra a quien lo reciba buscar un identificador equivocado
    que no es el problema.
    """
    return JSONResponse({"detalle": MOTIVO_SIN_ROL, "estado": "sin_rol"}, status_code=403)


def _no_existe() -> JSONResponse:
    """404 para quien **sí** tiene el rol y preguntó por algo que no está."""
    return JSONResponse(
        {"detalle": MOTIVO_NO_EXISTE, "estado": "no_encontrada"}, status_code=404
    )


def _peticion_invalida(error: ConsultaInvalida) -> JSONResponse:
    """400 con el motivo del dominio, que nunca interpola lo recibido.

    `ConsultaInvalida` la redacta `dominio/modelo/evidencia_revisable.py` y sus
    mensajes no llevan el valor que llegó: un cursor manipulado podría contener
    cualquier cosa, y devolverlo lo convertiría en un reflejo del que tirar.
    """
    return JSONResponse({"detalle": str(error), "estado": "peticion_invalida"}, status_code=400)


def crear_router(
    sesiones: Sesiones,
    deps: DependenciasDeEvidencias,
    puerta: PuertaDeSupresion,
) -> APIRouter:
    """La consola de revisión de `EQ-023`, con la puerta de `EQ-022` en las tres.

    ⚠️ **Las tres son lecturas, y las tres se bloquean.** Revisar autorizaciones
    firmadas por representantes legales de menores es la operación más sensible
    del sistema, y `ESTADO-ACTUAL.md` §10.2 suspende el uso del producto de quien
    tiene su propia supresión abierta. El derecho del titular es ver **sus**
    datos, no la cola de trabajo de un investigador.

    `puerta` es obligatoria: omitirla tiene que ser un error de construcción, no
    una forma silenciosa de desactivar la regla.
    """
    router = APIRouter()

    def _congelada(datos) -> JSONResponse | None:
        """La negativa si el ACTOR tiene su propio trámite abierto, o `None`.

        Va **antes** de llamar al repositorio, así que un actor congelado no
        aprende cuántas evidencias hay ni si un identificador existe — y en el
        archivo, no llega a recuperarse ni un byte del PDF privado.
        """
        return puerta.negativa(datos["identificador_estable"])

    @router.get("/api/representante/evidencias")
    def cola_de_evidencias(peticion: Request) -> JSONResponse:
        """La cola paginada de evidencias revisables (`EQ-023`).

        `?estado=` admite `pendiente` —el de por defecto—, `aprobada`,
        `rechazada` y `todos`. `?limite=` va de 1 a 100. `?cursor=` continúa
        donde terminó la página anterior y sólo se obtiene de `cursor_siguiente`;
        cuando ése es `null`, no hay más.

        **Los parámetros se validan antes de autorizar, y sólo aquí.** Un actor
        con sesión y sin rol que pida `?limite=999` recibe 400 en vez de 403, y
        es admisible: la respuesta depende **exclusivamente de lo que él mismo
        envió** y no dice absolutamente nada sobre qué evidencias hay. En el
        detalle y en el archivo no habría sido admisible —ahí el parámetro *es*
        un identificador— y por eso ahí el orden es el contrario.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa

        congelada = _congelada(datos)
        if congelada is not None:
            return congelada

        parametros = peticion.query_params
        try:
            filtro = filtro_desde(parametros.get("estado"))
            limite = limite_desde(parametros.get("limite"))
            cursor = cursor_desde(parametros.get("cursor"))
        except ConsultaInvalida as error:
            return _peticion_invalida(error)

        try:
            pagina = deps.evidencias.cola(
                actor=datos["identificador_estable"],
                filtro=filtro,
                limite=limite,
                cursor=cursor,
            )
        except EscrituraRechazada:
            # Cubre sólo «no tiene el rol»: una lectura no puede levantar
            # `ReferenciaDesconocida` porque no nombra ninguna fila.
            return _sin_rol()
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la cola de evidencias")

        return JSONResponse(
            {
                "filtro": filtro.value,
                "limite": limite,
                "evidencias": [_evidencia_como_json(e) for e in pagina.evidencias],
                "cursor_siguiente": pagina.cursor_siguiente,
                "hay_mas": pagina.hay_mas,
            }
        )

    @router.get("/api/representante/evidencias/{evidencia}")
    def detalle_de_evidencia(evidencia: int, peticion: Request) -> JSONResponse:
        """Una evidencia por identificador, para quien tiene el rol vigente.

        El orden —rol, después existencia— lo impone el repositorio y no esta
        ruta, a propósito: una comprobación que sólo viviera aquí se saltaría
        llamando al repositorio desde otro sitio, que es literalmente lo que la
        revisión R7-B hizo con `asignar()`.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa

        congelada = _congelada(datos)
        if congelada is not None:
            return congelada

        try:
            revisable = deps.evidencias.detalle(
                evidencia, actor=datos["identificador_estable"]
            )
        except ReferenciaDesconocida:
            # ⚠️ Antes que `EscrituraRechazada`: `ReferenciaDesconocida` hereda de
            # ella, y al revés este `except` no se alcanzaría nunca y una
            # evidencia inexistente respondería 403. Sería seguro y sería
            # confuso para quien sí tiene el rol.
            return _no_existe()
        except EscrituraRechazada:
            return _sin_rol()
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la evidencia")

        return JSONResponse(_detalle_como_json(revisable))

    @router.get("/api/representante/evidencias/{evidencia}/archivo")
    def archivo_de_evidencia(evidencia: int, peticion: Request) -> Response:
        """El PDF, servido a un investigador autorizado y a nadie más (`EQ-021`).

        El orden de las tres fases es el contrato:

        1. **sesión** — nadie llega aquí sin identidad verificada;
        2. **trámite del actor** — `EQ-022`: con su supresión abierta no usa el
           producto, y aquí eso significa que **no se recupera ni un byte** del
           PDF privado;
        3. **rol y referencia** — el repositorio exige `EQ-023` y sólo entonces
           devuelve la referencia opaca. Un actor sin rol no aprende si el
           identificador existe;
        4. **archivo** — el almacenamiento privado entrega los bytes.

        La referencia vive **únicamente** en la variable local de abajo. No entra
        en la respuesta, ni en las cabeceras, ni en el nombre del archivo, ni en
        ninguno de los mensajes de error de esta función.

        Los **cuatro** desenlaces del almacenamiento acaban en mantenimiento y
        ninguno en un cuerpo vacío con éxito: `EQ-024` prohíbe el éxito parcial,
        y un PDF de cero bytes que el visor de C2B pintara en blanco sería el
        peor de todos —dejaría aprobar una autorización que nadie llegó a ver—.

        ⚠️ El cuarto es **la reserva sin confirmar**, y es la corrección que
        devolvió la primera entrega de C2A. Ver
        `DocumentoPendienteDeConfirmacion`: una carga provisional no es evidencia
        aunque su fila esté en PostgreSQL, porque la petición que la dejó así ya
        respondió 503 a quien subió el documento.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa

        congelada = _congelada(datos)
        if congelada is not None:
            return congelada

        try:
            referencia = deps.evidencias.referencia_del_documento(
                evidencia, actor=datos["identificador_estable"]
            )
        except ReferenciaDesconocida:
            return _no_existe()
        except EscrituraRechazada:
            return _sin_rol()
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la evidencia")

        try:
            contenido = deps.almacenamiento.recuperar(referencia)
        except AlmacenamientoNoConfigurado:
            return mantenimiento(
                "el almacenamiento privado de la autorización no está configurado"
            )
        except DocumentoPendienteDeConfirmacion:
            # La carga no llegó a completarse: su petición respondió 503 a quien
            # la subió. Resolverla ahora haría decidir sobre un documento que el
            # sistema declaró no registrado, en las dos direcciones —aprobar algo
            # que su titular cree perdido, o rechazarlo sin que pudiera saberlo—.
            #
            # 503 y no 404: la fila existe. 503 y no 200: no es evidencia. El
            # motivo nombra la reconciliación porque es lo que desbloquea el
            # caso, y no la referencia, que no sale de aquí ni en este error.
            return mantenimiento(
                "la carga de esta evidencia quedó sin confirmar y no se puede "
                "revisar hasta que una reconciliación la complete o la retire"
            )
        except DocumentoAusente:
            # Antes que `AlmacenamientoNoDisponible`, de la que hereda. Motivo
            # propio porque es un desenlace distinto: la fila está y el archivo
            # no, y reintentar no lo arregla. No se responde 404 —eso diría que
            # la evidencia no existe, y sí existe— ni se nombra la referencia.
            return mantenimiento(
                "la evidencia está registrada y su archivo no se pudo recuperar "
                "del almacenamiento privado"
            )
        except AlmacenamientoNoDisponible:
            return mantenimiento("el almacenamiento privado no está disponible")

        return Response(
            content=contenido,
            media_type=TIPO_DEL_ARCHIVO,
            headers={
                # `inline` para que C2B pueda mostrarlo en un visor sin obligar a
                # descargarlo: `EQ-023` pide verificar, y un archivo que hay que
                # bajar al disco para mirarlo se acaba quedando ahí.
                #
                # El nombre lleva el identificador de la evidencia y nada más. Ni
                # el nombre del representante —que el sistema no tiene—, ni el
                # sujeto, ni la referencia del almacén.
                "Content-Disposition": f'inline; filename="evidencia-{evidencia}.pdf"',
                **CABECERAS_DEL_ARCHIVO,
            },
        )

    return router
