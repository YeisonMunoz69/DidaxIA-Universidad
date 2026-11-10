"""
datos_personales.py — Consultar y exportar · `RP-19` · Ley 1581
==================================================================================

Las dos rutas de lectura de los derechos del titular. Las dos de borrado
inmediato **están retiradas** desde el hito R2; ver más abajo.

⚠️ No confundir con `adaptadores/entrantes/http/datos_personales.py`, que es
la lógica —qué alcanza la cascada, qué se declara sin alcanzar—. Ver
`rutas/__init__.py`.

Por qué exportar no es lo mismo que consultar
----------------------------------------------------
`RP-19` distingue las dos operaciones y aquí se conservan separadas: mirar no
es llevarse una copia. La segunda añade la marca de tiempo de la exportación,
que es lo que la convierte en un documento y no en una respuesta más.

⚠️ Los dos `DELETE` están retirados · hito R2
---------------------------------------------------
`DELETE /api/datos-personales` y `DELETE /api/datos-personales/por-identidad`
ejecutaban la cascada de `RD-22` **en el acto**: perfil versionado, registro del
turno, historial de conversación y matrícula en clases, y la primera además
cerraba la sesión. Se escribieron cuando `RP-19` era todo el contrato; `EQ-022`
lo sustituyó y dice otra cosa:

    «La supresión es un trámite distinto: exige reautenticación reciente con
    Google, diálogo explícito, frase de confirmación y aviso al correo
    institucional; dispone de 24 horas para cancelar antes de ejecutarse.»

Un `DELETE` que borra al recibir la petición **no tiene ninguna de las cuatro
cosas**. No es que estuviera incompleto: es que era la vía por la que todo el
trámite se podía saltar, y bastaba con llamar al API directamente. La auditoría
V-B lo puso el primero de sus nueve invariantes.

Ahora responden **410** y señalan `POST /api/datos/supresion`, que abre el
trámite reversible. No mutan nada: no llaman a `datos_personales.suprimir()`,
no tocan `clases_almacen` y no cierran la sesión. Y no reciben ya los
adaptadores que harían falta para hacerlo, que es lo que impide que vuelvan a
hacerlo por descuido.

⚠️ **La cascada irreversible sigue sin implementarse, y es deliberado.** Qué se
borra, qué se conserva seudonimizado y qué puede anonimizarse de verdad es la
decisión humana que el cierre V-B reserva al equipo. `plan_de_supresion()` y
`GET /api/datos/inventario` describen **qué alcanzaría**; nada la ejecuta.


"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http import datos_personales
from adaptadores.entrantes.http.rutas.comun import mantenimiento, requerir_sesion
from adaptadores.entrantes.http.sesiones import Sesiones
from adaptadores.salientes.almacenamiento.fotos_perfil import (
    LIMITE_ENTRADA_BYTES,
    AlmacenFotosPerfil,
    FotoNoAdmitida,
)
from dominio.puertos.almacen import ErrorDeAlmacen, ReferenciaDesconocida

#: Adónde va quien llamaba a los `DELETE` retirados. Una constante y no tres
#: cadenas sueltas: si la ruta del trámite cambiara, las respuestas no pueden
#: quedarse señalando a un sitio que ya no existe.
_RUTA_DEL_TRAMITE = "/api/datos/supresion"


def _retirada(que_hacia: str) -> JSONResponse:
    """La respuesta de una vía de borrado inmediato que ya no existe.

    **410 y no 404.** `Gone` dice «existió aquí y ya no», que es exactamente lo
    ocurrido y lo que necesita saber un cliente antiguo; un 404 se lee como «este
    backend se rompió» y mandaría a depurar el despliegue. Tampoco 405: el verbo
    no es el problema.

    El cuerpo explica **qué hacía** y **adónde ir**, porque quien llegue aquí
    estaba ejerciendo un derecho y no puede quedarse sin saber cómo ejercerlo.
    """
    return JSONResponse(
        {
            "detalle": (
                f"esta ruta fue retirada: {que_hacia}. EQ-022 exige un trámite "
                "reversible con reautenticación reciente, frase de confirmación, "
                "aviso al correo institucional y 24 horas para cancelar"
            ),
            "estado": "retirada",
            "usar": _RUTA_DEL_TRAMITE,
        },
        status_code=410,
    )


def crear_router(
    sesiones: Sesiones,
    identidades: Any | None = None,
    fotos: AlmacenFotosPerfil | None = None,
    puerta: Any | None = None,
    preferencias_interfaz: Any | None = None,
    recursos: Any | None = None,
) -> APIRouter:
    """Derechos del titular y foto privada de la cuenta.

    Los adaptadores opcionales pertenecen sólo a la foto. Este router sigue sin
    recibir los almacenes de historial, turnos o clases que permitirían revivir
    el borrado inmediato retirado en R2.
    """
    router = APIRouter()

    def _dependencias_disponibles() -> JSONResponse | None:
        if identidades is None or fotos is None or not fotos.configurado:
            return JSONResponse(
                {
                    "detalle": "las fotos de perfil no están disponibles en este momento",
                    "estado": "mantenimiento",
                },
                status_code=503,
                headers={"Retry-After": "30"},
            )
        return None

    async def _imagen_limitada(peticion: Request) -> bytes:
        """Lee como máximo el límite más un byte; no confía en Content-Length."""
        cuerpo = bytearray()
        async for fragmento in peticion.stream():
            cuerpo.extend(fragmento)
            if len(cuerpo) > LIMITE_ENTRADA_BYTES:
                raise FotoNoAdmitida("la imagen supera el límite de 4 MB")
        return bytes(cuerpo)

    @router.get("/api/datos-personales/foto")
    def consultar_foto(peticion: Request) -> Response:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        if (indisponible := _dependencias_disponibles()) is not None:
            return indisponible
        try:
            referencia = identidades.referencia_foto(datos["identificador_estable"])
            cuerpo = fotos.recuperar(referencia) if referencia else None
        except (ErrorDeAlmacen, OSError, FotoNoAdmitida):
            return _dependencias_disponibles() or Response(status_code=503)
        if referencia and cuerpo is None:
            return JSONResponse(
                {"detalle": "la foto registrada no está disponible en este momento"},
                status_code=503,
                headers={"Retry-After": "30"},
            )
        if cuerpo is None:
            return JSONResponse({"detalle": "esta cuenta no tiene foto"}, status_code=404)
        return Response(
            content=cuerpo,
            media_type="image/webp",
            headers={
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @router.put("/api/datos-personales/foto")
    async def guardar_foto(peticion: Request) -> Response:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        if (indisponible := _dependencias_disponibles()) is not None:
            return indisponible
        if puerta is not None and (
            congelada := puerta.negativa(datos["identificador_estable"])
        ) is not None:
            return congelada
        tipo = (peticion.headers.get("content-type") or "").split(";", 1)[0].lower()
        if tipo not in {"image/jpeg", "image/png", "image/webp"}:
            return JSONResponse(
                {"detalle": "usa una imagen JPEG, PNG o WebP"}, status_code=415
            )
        nueva: str | None = None
        try:
            nueva = fotos.guardar(await _imagen_limitada(peticion))
            anterior = identidades.cambiar_foto(datos["identificador_estable"], nueva)
        except FotoNoAdmitida as exc:
            if nueva:
                fotos.retirar(nueva)
            return JSONResponse({"detalle": str(exc)}, status_code=400)
        except (ErrorDeAlmacen, OSError, ReferenciaDesconocida):
            if nueva:
                fotos.retirar(nueva)
            return JSONResponse(
                {"detalle": "no se pudo guardar la foto en este momento"},
                status_code=503,
                headers={"Retry-After": "30"},
            )
        if anterior:
            fotos.retirar(anterior)
        return JSONResponse({"foto": "/api/datos-personales/foto"})

    @router.delete("/api/datos-personales/foto")
    def retirar_foto(peticion: Request) -> Response:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        if (indisponible := _dependencias_disponibles()) is not None:
            return indisponible
        if puerta is not None and (
            congelada := puerta.negativa(datos["identificador_estable"])
        ) is not None:
            return congelada
        try:
            anterior = identidades.cambiar_foto(datos["identificador_estable"], None)
            if anterior:
                fotos.retirar(anterior)
        except (ErrorDeAlmacen, OSError, FotoNoAdmitida, ReferenciaDesconocida):
            return JSONResponse(
                {"detalle": "no se pudo retirar la foto en este momento"},
                status_code=503,
                headers={"Retry-After": "30"},
            )
        return Response(status_code=204)

    @router.get("/api/datos-personales")
    def consultar_datos_personales(peticion: Request) -> Response:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        cuerpo = datos_personales.consultar(datos)
        # La cuenta profesional no pasa por el onboarding, pero su facultad
        # sigue viviendo en `persona`. Exponer el perfil propio aquí evita que
        # la pantalla tenga que consultar el directorio de terceros para saber
        # algo que pertenece al titular de esta sesión.
        if identidades is not None:
            try:
                perfil = identidades.consultar(datos["identificador_estable"])
            except ErrorDeAlmacen:
                perfil = None
            if perfil is not None:
                cuerpo["perfil"] = {
                    "facultad": perfil.facultad,
                    "programa": perfil.programa,
                    "semestre": perfil.semestre,
                }
        return JSONResponse(cuerpo)

    @router.get("/api/datos-personales/exportar")
    def exportar_datos_personales(peticion: Request) -> Response:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        cuerpo = datos_personales.exportar(datos)
        if recursos is not None:
            try:
                cuerpo['recursos'] = recursos.exportar_titular(datos['identificador_estable'])
            except ErrorDeAlmacen:
                return mantenimiento('No se pueden exportar las respuestas de recursos ahora.')
        if preferencias_interfaz is not None:
            try:
                cuerpo["preferencias_interfaz"] = preferencias_interfaz.consultar(datos["identificador_estable"])
            except ErrorDeAlmacen:
                cuerpo["preferencias_interfaz"] = {"estado": "no_disponible"}
        return JSONResponse(cuerpo)

    @router.delete("/api/datos-personales")
    def suprimir_datos_personales() -> Response:
        """Retirada en el hito R2. Ver la cabecera del módulo.

        No pide sesión antes de responder: comprobarla no cambia la respuesta y
        haría creer que con la sesión correcta pasaría algo distinto.
        """
        return _retirada(
            "borraba perfil, registro de turnos, historial y matrícula al recibir "
            "la petición, y además cerraba la sesión"
        )

    @router.delete("/api/datos-personales/por-identidad")
    def suprimir_por_identidad() -> Response:
        """La vía sin sesión de `PM-B15` C, retirada en el hito R2.

        ⚠️ **El derecho que resolvía sigue existiendo y no queda huérfano.** Esta
        ruta servía a quien había cerrado el navegador y perdido la cookie: con un
        `id_token` fresco podía ejercer la supresión sin sesión activa. Ese caso
        se resuelve hoy autenticándose otra vez —lo que crea sesión— y abriendo el
        trámite, que además exige la reautenticación reciente que aquí ya se
        estaba haciendo. No se pierde ninguna vía; se pierde la inmediatez, que es
        justamente lo que `EQ-022` retira.

        Lo que `DD-18` ya declaraba aparte —quien perdió del todo el correo
        institucional y no puede obtener ningún `id_token`— sigue sin resolverse
        por API, y sigue siendo el caso que el equipo debe cerrar antes del piloto.
        """
        return _retirada(
            "borraba por identificador estable con sólo presentar un id_token"
        )

    return router
