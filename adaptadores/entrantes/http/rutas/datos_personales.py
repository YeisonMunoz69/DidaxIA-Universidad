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


_RUTA_DEL_TRAMITE = "/api/datos/supresion"


def _retirada(que_hacia: str) -> JSONResponse:
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
        return _retirada(
            "borraba perfil, registro de turnos, historial y matrícula al recibir "
            "la petición, y además cerraba la sesión"
        )

    @router.delete("/api/datos-personales/por-identidad")
    def suprimir_por_identidad() -> Response:
        return _retirada(
            "borraba por identificador estable con sólo presentar un id_token"
        )

    return router
