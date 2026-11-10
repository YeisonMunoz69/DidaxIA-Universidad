from __future__ import annotations

import base64
import binascii
import re
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import (
    json_del_cuerpo,
    mantenimiento,
    requerir_rol,
    requerir_sesion,
)
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones, sujeto_de
from adaptadores.salientes.almacenamiento.capturas_reportes import (
    LIMITE_ENTRADA_BYTES,
    CapturaNoAdmitida,
    normalizar_captura,
)
from dominio.puertos.almacen import (
    AlmacenNoConfigurado,
    AlmacenNoDisponible,
    EscrituraRechazada,
    ReferenciaDesconocida,
)
from dominio.puertos.gobierno import SupresionEnCurso

if TYPE_CHECKING:
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
    from dominio.puertos.reportes import PuertoReportes, Reporte

CATEGORIAS = frozenset({"funcional", "visual", "accesibilidad", "rendimiento", "contenido", "otro"})
ESTADOS = frozenset({"nuevo", "en_revision", "resuelto", "descartado"})
TIPOS_CAPTURA = frozenset({"image/png", "image/jpeg", "image/webp"})
BASE64_MAXIMO = ((LIMITE_ENTRADA_BYTES + 2) // 3) * 4 + 4
_RUTA = re.compile(r"^/[A-Za-z0-9/_-]*$")
_CABECERAS_IMAGEN = {
    "Cache-Control": "no-store, private, max-age=0, must-revalidate",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'",
}


def _json(reporte: Reporte, *, institucional: bool = False) -> dict:
    salida = {
        "id": reporte.identificador,
        "rol": reporte.rol,
        "categoria": reporte.categoria,
        "titulo": reporte.titulo,
        "descripcion": reporte.descripcion,
        "pasos": reporte.pasos,
        "ruta": reporte.ruta,
        "estado": reporte.estado,
        "tiene_captura": reporte.tiene_captura,
        "captura_bytes": reporte.captura_bytes,
        "respuesta": reporte.respuesta,
        "creado_en": reporte.creado_en.isoformat(),
        "actualizado_en": reporte.actualizado_en.isoformat(),
    }
    if institucional:
        salida["reportante"] = reporte.reportante
    return salida

def _error(detalle: str, codigo: int = 400) -> JSONResponse:
    return JSONResponse({"detalle": detalle}, status_code=codigo)

def _captura(valor: object) -> bytes | None:
    if valor in (None, {}):
        return None
    if not isinstance(valor, dict):
        raise ValueError("la captura no tiene el formato esperado")
    tipo = str(valor.get("tipo") or "").strip().lower()
    contenido = str(valor.get("contenido") or "").strip()
    if tipo not in TIPOS_CAPTURA:
        raise ValueError("usa una captura PNG, JPEG o WebP")
    if len(contenido) > BASE64_MAXIMO:
        raise ValueError("la captura supera el límite de 5 MB")
    try:
        crudo = base64.b64decode(contenido, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("la captura no contiene Base64 válido") from None
    try:
        return normalizar_captura(crudo, tipo=tipo)
    except CapturaNoAdmitida as error:
        raise ValueError(str(error)) from None

def _datos_del_reporte(cuerpo: dict) -> tuple[str, str, str, str, str, bytes | None]:
    categoria = str(cuerpo.get("categoria") or "").strip()
    titulo = str(cuerpo.get("titulo") or "").strip()
    descripcion = str(cuerpo.get("descripcion") or "").strip()
    pasos = str(cuerpo.get("pasos") or "").strip()
    ruta = str(cuerpo.get("ruta") or "/").strip()
    if categoria not in CATEGORIAS:
        raise ValueError("elige una categoría disponible")
    if len(titulo) < 5 or len(titulo) > 120:
        raise ValueError("el título debe tener entre 5 y 120 caracteres")
    if len(descripcion) < 10 or len(descripcion) > 4000:
        raise ValueError("la descripción debe tener entre 10 y 4000 caracteres")
    if len(pasos) > 3000:
        raise ValueError("los pasos no pueden superar 3000 caracteres")
    if len(ruta) > 240 or not _RUTA.fullmatch(ruta):
        raise ValueError("la ruta de la pantalla no es admisible")
    return categoria, titulo, descripcion, pasos, ruta, _captura(cuerpo.get("captura"))

def crear_router(
    sesiones: Sesiones,
    reportes: PuertoReportes,
    puerta: PuertaDeSupresion,
) -> APIRouter:
    router = APIRouter()

    def _sesion(peticion: Request):
        datos, negativa = requerir_sesion(sesiones, peticion)
        return datos, negativa

    def _investigador(peticion: Request):
        negativa = requerir_rol(sesiones, peticion, "investigador")
        if negativa is not None:
            return None, negativa
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        return datos, puerta.negativa(sujeto_de(datos))

    @router.post("/api/reportes")
    async def crear(peticion: Request):
        datos, negativa = _sesion(peticion)
        if negativa is not None:
            return negativa
        congelada = puerta.negativa(sujeto_de(datos))
        if congelada is not None:
            return congelada

        longitud = peticion.headers.get("content-length", "")
        if longitud.isdecimal() and int(longitud) > 8 * 1024 * 1024:
            return _error("el reporte supera el límite de carga", 413)
        cuerpo = await json_del_cuerpo(peticion)
        if cuerpo.get("confirmado") is not True:
            return _error("confirma que revisaste la captura y el contenido")
        try:
            categoria, titulo, descripcion, pasos, ruta, captura = _datos_del_reporte(cuerpo)
            reporte = reportes.crear(
                actor=sujeto_de(datos), rol=str(datos.get("rol") or "estudiante"),
                categoria=categoria, titulo=titulo, descripcion=descripcion,
                pasos=pasos, ruta=ruta, captura=captura,
            )
        except ValueError as error:
            return _error(str(error))
        except EscrituraRechazada as error:
            return _error(str(error), 409)
        except SupresionEnCurso:
            return puerta.negativa(sujeto_de(datos)) or _error("supresión en curso", 409)
        except ReferenciaDesconocida:
            return _error("la cuenta no está registrada", 409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo guardar el reporte; conserva el texto e inténtalo luego")
        return JSONResponse({"reporte": _json(reporte)}, status_code=201)

    @router.get("/api/reportes/mios")
    def mios(peticion: Request):
        datos, negativa = _sesion(peticion)
        if negativa is not None:
            return negativa
        try:
            filas = reportes.mios(sujeto_de(datos))
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudieron consultar tus reportes")
        return {"reportes": [_json(fila) for fila in filas]}

    @router.get("/api/reportes/mios/{reporte}/captura")
    def captura_propia(reporte: int, peticion: Request):
        datos, negativa = _sesion(peticion)
        if negativa is not None:
            return negativa
        try:
            cuerpo = reportes.captura_propia(sujeto_de(datos), reporte)
        except ReferenciaDesconocida:
            return _error("el reporte no existe", 404)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("la captura no está disponible")
        if cuerpo is None:
            return _error("este reporte no tiene captura", 404)
        return Response(cuerpo, media_type="image/webp", headers=_CABECERAS_IMAGEN)

    @router.get("/api/investigacion/reportes")
    def institucionales(peticion: Request, estado: str = ""):
        datos, negativa = _investigador(peticion)
        if negativa is not None:
            return negativa
        if estado and estado not in ESTADOS:
            return _error("estado de reporte no admisible")
        try:
            filas = reportes.institucionales(sujeto_de(datos), estado)
        except EscrituraRechazada:
            return _error("esta consulta requiere el rol investigador", 403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudieron consultar los reportes institucionales")
        return {"reportes": [_json(fila, institucional=True) for fila in filas]}

    @router.get("/api/investigacion/reportes/{reporte}/captura")
    def captura_institucional(reporte: int, peticion: Request):
        datos, negativa = _investigador(peticion)
        if negativa is not None:
            return negativa
        try:
            cuerpo = reportes.captura(sujeto_de(datos), reporte)
        except ReferenciaDesconocida:
            return _error("el reporte no existe", 404)
        except EscrituraRechazada:
            return _error("esta consulta requiere el rol investigador", 403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("la captura no está disponible")
        if cuerpo is None:
            return _error("este reporte no tiene captura", 404)
        return Response(cuerpo, media_type="image/webp", headers=_CABECERAS_IMAGEN)

    @router.patch("/api/investigacion/reportes/{reporte}")
    async def actualizar(reporte: int, peticion: Request):
        datos, negativa = _investigador(peticion)
        if negativa is not None:
            return negativa
        cuerpo = await json_del_cuerpo(peticion)
        estado = str(cuerpo.get("estado") or "").strip()
        respuesta = str(cuerpo.get("respuesta") or "").strip()
        if estado not in ESTADOS:
            return _error("estado de reporte no admisible")
        if len(respuesta) > 2000:
            return _error("la respuesta no puede superar 2000 caracteres")
        try:
            fila = reportes.actualizar(
                sujeto_de(datos), reporte, estado=estado, respuesta=respuesta
            )
        except ReferenciaDesconocida:
            return _error("el reporte no existe", 404)
        except EscrituraRechazada:
            return _error("esta operación requiere el rol investigador", 403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo actualizar el reporte")
        return {"reporte": _json(fila, institucional=True)}

    return router
