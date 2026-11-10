from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.docentes import RegistroDeDocentes
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones


CODIGO_MANTENIMIENTO = 503
REINTENTAR_EN_SEGUNDOS = 30


async def json_del_cuerpo(peticion: Request) -> dict:
    try:
        datos = await peticion.json()
    except Exception:
        return {}
    return datos if isinstance(datos, dict) else {}

def mantenimiento(detalle: str = "") -> JSONResponse:
    return JSONResponse(
        {
            "detalle": detalle or "el servicio no está disponible en este momento",
            "estado": "mantenimiento",
        },
        status_code=CODIGO_MANTENIMIENTO,
        headers={"Retry-After": str(REINTENTAR_EN_SEGUNDOS)},
    )

def requerir_sesion(sesiones: Sesiones, peticion: Request) -> tuple[dict | None, JSONResponse | None]:
    datos = sesiones.leer(peticion.cookies.get(COOKIE))
    if datos is None:
        return None, JSONResponse(
            {"detalle": "sin sesión", "estado": "sin_sesion"}, status_code=401
        )
    if not datos.get("identificador_estable"):

        return None, JSONResponse(
            {"detalle": "sesión sin identidad verificada", "estado": "sin_sesion"},
            status_code=401,
        )
    return datos, None

def requerir_rol(sesiones: Sesiones, peticion: Request, rol: str) -> JSONResponse | None:
    datos = sesiones.leer(peticion.cookies.get(COOKIE))
    if datos is None:
        return JSONResponse({"detalle": "sin sesión"}, status_code=401)
    if datos["rol"] != rol:
        return JSONResponse({"detalle": f"esta ruta es de «{rol}»"}, status_code=403)
    return None

def requerir_lista_manual(
    sesiones: Sesiones, registro_docentes: RegistroDeDocentes, peticion: Request
) -> JSONResponse | None:

    datos = sesiones.leer(peticion.cookies.get(COOKIE))
    if datos is None:
        return JSONResponse({"detalle": "sin sesión"}, status_code=401)
    correo = datos.get("correo") or ""
    if not registro_docentes.es_de_la_lista_manual(correo):
        return JSONResponse(
            {"detalle": "solo quien está en la lista a mano puede resolver solicitudes"},
            status_code=403,
        )
    return None
