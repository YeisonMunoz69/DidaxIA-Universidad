"""
salud.py — `GET /api/salud` · qué se pudo armar y qué no (`PM-B27`)
============================================================================

Una sola ruta, y con archivo propio porque no es de ninguna familia: no la
consume el estudiante ni el docente, sino **quien opera el sistema**. `RP-17`
pide degradación explícita; esto es esa misma idea para el que despliega.


"""

from __future__ import annotations

import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http import formato_representante, identidad
from adaptadores.entrantes.http.composicion import Composicion
from dominio.modelo.consentimiento import Alcance
from dominio.modelo.factores_conductuales import VERSION as VERSION_FACTORES


def _estado_formato_representante(versiones) -> dict:
    """Banderas públicas, sin texto, código ni huella del documento legal."""
    if versiones is None:
        return {"comprobado": False, "descargable": False, "motivo": "sin_almacen"}
    try:
        version = versiones.version_requerida(Alcance.REPRESENTANTE)
    except Exception:  # noqa: BLE001 — salud debe responder incluso sin base
        return {"comprobado": False, "descargable": False, "motivo": "consulta_fallida"}
    motivo = formato_representante.disponibilidad(version)
    return {
        "comprobado": True,
        "descargable": motivo == "disponible",
        "motivo": None if motivo == "disponible" else motivo,
    }


def _sin_monitor() -> dict:
    """Lo que se publica cuando no hay vigilancia · `D2-B`.

    Se importa del módulo del monitor en vez de escribirlo aquí: si algún día
    cambiara la forma del bloque, dos redacciones darían dos respuestas distintas
    a la misma pregunta según hubiera `AGENTE_BD` o no.
    """
    from adaptadores.salientes.disponibilidad.postgres import SIN_MONITOR

    return dict(SIN_MONITOR)


_SIN_MONITOR = _sin_monitor()


def faltantes_del_borde() -> list[str]:
    """Lo que le falta a ESTE adaptador, que `composicion.py` no puede saber.

    La composición arma la cadena del dominio y declara lo suyo; la identidad
    delegada (`PM-B15`) es del borde HTTP y no pasa por ella. Sin
    `GOOGLE_CLIENT_ID` el sistema arranca y funciona entero salvo el login de
    Google —está razonado en `compose.produccion.yaml`—, y esta línea es lo
    que impide que ese hueco sea invisible para quien opera el sistema.
    """
    if identidad.esta_configurado():
        return []
    return [
        "GOOGLE_CLIENT_ID no está en el entorno: el login de Google (PM-B15) "
        "rechaza cualquier token con 401. El resto del sistema funciona; el "
        "rol docente solo se puede alcanzar por esa vía."
    ]


def _generacion_configurada() -> dict:
    """Qué proveedor y qué modelo hay puestos · `PM-B42`.

    Lee el entorno y **no** construye el adaptador: esta ruta tiene que
    responder aunque el proveedor esté mal configurado — es justo cuando más
    falta hace. Si `AGENTE_LLM_MODELO` no está, se dice cuál es el respaldo en
    vez de callarlo, que es la misma regla de `faltantes`.
    """
    from adaptadores.salientes.generacion.deepseek import _MODELO_POR_DEFECTO

    pedido = os.environ.get("AGENTE_LLM_MODELO", "").strip()
    return {
        "proveedor": os.environ.get("AGENTE_LLM", "").strip() or None,
        "modelo": pedido or _MODELO_POR_DEFECTO,
        "modelo_del_entorno": bool(pedido),
        # ⚠️ Es el modelo PEDIDO. El que se registra por turno es el que el
        # proveedor responde (`deepseek.py`), porque un alias puede resolverse a
        # una versión concreta.
        "nota": "modelo pedido; RF-REG-04 registra el que responde el proveedor",
    }


#: Lo que se publica cuando la composición no trae custodia · `D3`.
#:
#: No es «no configurado»: es «esta composición no pasó el adaptador». Se
#: distingue con `declarado` para que nadie lea un despliegue mal cableado como
#: un despliegue sin volumen — son dos problemas y se arreglan distinto.
SIN_CUSTODIA = {
    "declarado": False,
    "configurado": False,
    "tipo": None,
    "disponible": False,
}


def _custodia(almacenamiento) -> dict:
    """Las banderas de la custodia privada. **Ningún valor.**

    Las redacta el propio adaptador (`estado_publicable()`) y esta función sólo
    las copia: ni la ruta del volumen, ni un nombre de archivo, ni una
    referencia, ni el SHA-256 de ningún documento, ni el texto de una excepción
    pueden llegar aquí, porque esta capa no los tiene.

    Se pregunta al adaptador y no al entorno por el mismo motivo que `canal`: una
    segunda lectura de `ALMACENAMIENTO_PRIVADO_RUTA` podría decir «configurado»
    mientras la aplicación tiene cableado el que no guarda nada.

    Un adaptador que no supiera responder —uno de prueba, por ejemplo— no
    revienta la salud: se publica lo mínimo cierto, que es si dice estar
    configurado.
    """
    if almacenamiento is None:
        return dict(SIN_CUSTODIA)
    publicable = getattr(almacenamiento, "estado_publicable", None)
    if publicable is None:
        return {
            "declarado": True,
            "configurado": bool(almacenamiento.esta_configurado()),
            "tipo": None,
            "disponible": False,
        }
    return {"declarado": True, **publicable()}


def crear_router(
    composicion: Composicion,
    faltantes_almacenes: list[str] | tuple[str, ...] = (),
    *,
    canal=None,
    monitor=None,
    almacenamiento=None,
    versiones=None,
) -> APIRouter:
    """El router de la salud.

    `canal` es el `Canal` de avisos ya compuesto (`D2`). Se **recibe** y no se
    recalcula leyendo el entorno: si esta ruta volviera a mirar `RESEND_API_KEY`
    por su cuenta, podría decir «configurado» mientras la aplicación tiene
    cableado el adaptador que no envía —dos lecturas de la misma pregunta, que
    es el defecto que `aplicacion.py` acaba de cerrar componiendo una sola
    instancia—.

    Admite `None` para quien componga sin canal —las pruebas de la cadena, que
    no lo necesitan—: entonces el bloque no se publica en vez de publicar un
    estado inventado.

    `monitor` es el vigilante de PostgreSQL de `D2-B`, y es opcional por otra
    razón: sin `AGENTE_BD` **no existe**, y eso es un estado real del despliegue
    que sí se publica —`configurado: false`—. Se distingue de `canal=None`, que
    significa «esta composición no trae canal» y no se publica.

    `almacenamiento` es la custodia privada de `D3`, y llega por el mismo camino
    y por el mismo motivo que `canal`: es **el objeto que la aplicación tiene
    compuesto**, no una segunda lectura del entorno. Ver `_custodia()`.
    """
    router = APIRouter()

    @router.get("/api/salud")
    def salud() -> JSONResponse:
        """Qué se pudo armar y qué no.

        Existe para que quien depure no tenga que adivinar si un turno degrada
        por su petición o porque a esta máquina le falta el índice o el
        generador. `RP-17` pide degradación **explícita**, y esto es la versión
        de esa idea para quien opera el sistema.

        `composicion.faltantes` cubre la CADENA —índice, generador—;
        `faltantes_del_borde()` lo que la composición no conoce porque no es
        del dominio (`GOOGLE_CLIENT_ID`); `faltantes_almacenes` —desde el
        2026-08-22— si `Clases`/`ColaDeRevision`/las solicitudes docentes
        cayeron a memoria por falta de `AGENTE_BD`, que `aplicacion.py` decide
        al construirlos y esta ruta no puede recalcular sin repetir esa lógica.
        """
        cuerpo = {
            "faltantes": [*composicion.faltantes, *faltantes_del_borde(), *faltantes_almacenes],
            # `PM-B42`, 2026-08-18 · quien opera el sistema tiene que poder
            # saber QUÉ MODELO está configurado sin leer el código ni entrar al
            # contenedor. `RF-REG-04` registra el modelo por turno, así que un
            # cambio invalida la comparación de latencias anteriores: verlo aquí
            # es lo que permite darse cuenta antes de comparar peras con
            # manzanas.
            "generacion": _generacion_configurada(),
            "tutor": {
                "interpretacion": composicion.interpretacion,
                "contexto": "reforzado" if composicion.contexto_reforzado else "actual",
            "retroalimentacion_directa": composicion.retroalimentacion_directa,
            "continuidad": "estado_operativo.v1" if composicion.continuidad else "anterior",
            "factores_conductuales": composicion.factores_conductuales,
            "version_factores": VERSION_FACTORES,
                "progreso_en_vivo": True,
            },
        }
        if canal is not None:
            # `D2` · si el canal de avisos puede enviar, y qué le falta si no.
            # **Banderas, nunca valores**: ni la clave, ni el remitente, ni el
            # correo de privacidad. Ver `notificacion/canal.py::como_json()`.
            cuerpo["notificacion"] = canal.como_json()
        # `D2-B` · qué se sabe de PostgreSQL, y de dónde se sabe.
        #
        # ⚠️ **El estado sale del sondeo y de ningún otro sitio.** Resend no
        # aparece aquí: `EQ-024` dice que el canal no decide el diagnóstico, así
        # que un correo que no salió no puede hacer que la base parezca caída
        # —ni al revés—. `aviso_intentado` cuenta lo que se hizo con la alerta,
        # no lo que le pasa a la base.
        cuerpo["disponibilidad"] = (
            monitor.como_json() if monitor is not None else _SIN_MONITOR
        )
        # `D3` · si este despliegue puede custodiar la autorización del
        # representante, y si la custodia responde.
        #
        # ⚠️ **Banderas y un conteo, nunca valores.** Ni la raíz del volumen, ni
        # un nombre de archivo, ni una referencia, ni el sujeto, ni el SHA-256
        # del documento, ni el texto de la excepción que lo dejó inservible. El
        # conteo de reservas pendientes dice que hay que mirar; **cuáles** son se
        # averigua entrando al servidor, que es donde corresponde.
        cuerpo["almacenamiento_privado"] = _custodia(almacenamiento)
        cuerpo["formato_representante"] = _estado_formato_representante(versiones)
        return JSONResponse(cuerpo)

    return router
