from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http import aviso_legal, cookies, identidad
from adaptadores.entrantes.http.docentes import RegistroDeDocentes
from adaptadores.entrantes.http.investigadores import aprovisionar_rol_configurado
from adaptadores.entrantes.http.rol_de_presentacion import rol_de_presentacion
from adaptadores.entrantes.http.rutas.comun import (
    json_del_cuerpo,
    mantenimiento,
    requerir_sesion,
)
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones
from dominio.modelo.identidad import Identidad, IdentidadInvalida, PerfilOnboarding
from dominio.modelo.supresion import (
    SEGUNDOS_DE_REAUTENTICACION_RECIENTE,
    emision_recien_firmada,
)
from dominio.puertos.almacen import ErrorDeAlmacen

if TYPE_CHECKING:
    from adaptadores.salientes.almacenamiento.fotos_perfil import AlmacenFotosPerfil
    from dominio.puertos.consentimiento import PuertoConsentimiento
    from dominio.puertos.identidad import PuertoIdentidad
    from dominio.puertos.roles import PuertoAsignacionDeRoles

_EDAD_MINIMA_ADMISIBLE = 0
_EDAD_MAXIMA_ADMISIBLE = 120


def edad_del_cuerpo(valor) -> int | None:
    if isinstance(valor, bool):
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        if not valor.isdigit():
            return None
        valor = int(valor)
    if not isinstance(valor, int):
        return None
    if not _EDAD_MINIMA_ADMISIBLE <= valor <= _EDAD_MAXIMA_ADMISIBLE:
        return None
    return valor

COOKIE_DURACION_SEGUNDOS = cookies.DURACION_SEGUNDOS


def _persistir_identidad(
    identidades: PuertoIdentidad | None, verificada: identidad.IdentidadVerificada
) -> PerfilOnboarding | JSONResponse:

    if identidades is None:
        return mantenimiento("el registro de identidad no está disponible")
    try:
        return identidades.registrar(
            Identidad(
                sujeto_google=verificada.identificador,
                correo=verificada.correo,
                nombre=verificada.nombre,
            )
        )
    except IdentidadInvalida:
        return JSONResponse(
            {"detalle": "la identidad verificada no es utilizable"}, status_code=401
        )
    except ErrorDeAlmacen:

        return mantenimiento("no se pudo registrar la identidad en este momento")

def _con_cookie(cuerpo: dict, identificador: str) -> JSONResponse:
    respuesta = JSONResponse(cuerpo)
    respuesta.set_cookie(
        COOKIE, identificador, max_age=COOKIE_DURACION_SEGUNDOS, **cookies.atributos()
    )
    return respuesta

def crear_router(
    sesiones: Sesiones,
    registro_docentes: RegistroDeDocentes,
    consentimiento_almacen: PuertoConsentimiento,
    identidades: PuertoIdentidad | None = None,
    *,
    roles: PuertoAsignacionDeRoles | None = None,
    fotos: AlmacenFotosPerfil | None = None,
    invitaciones=None,
) -> APIRouter:

    router = APIRouter()

    @router.get("/api/sesion")
    def sesion_actual(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        return JSONResponse(sesiones.publico(datos))

    @router.post("/api/sesion")
    def abrir_sesion() -> JSONResponse:
        return JSONResponse(
            {
                "detalle": (
                    "esta aplicación exige una cuenta institucional: "
                    "inicie sesión con Google"
                ),
                "estado": "sin_sesion",
            },
            status_code=401,
        )

    @router.post("/api/sesion/google")
    async def abrir_sesion_google(peticion: Request) -> JSONResponse:
        cuerpo = await json_del_cuerpo(peticion)
        identidad_verificada = identidad.verificar_id_token(str(cuerpo.get("id_token") or ""))
        if identidad_verificada is None:
            return JSONResponse(
                {"detalle": "token de Google no válido, expirado o fuera de dominio"},
                status_code=401,
            )

        persistida = _persistir_identidad(identidades, identidad_verificada)
        if isinstance(persistida, JSONResponse):
            return persistida

        invitacion_token = str(cuerpo.get("invitacion") or "").strip()
        roles_aceptados = ()
        if invitacion_token and invitaciones is not None:
            try:
                roles_aceptados = invitaciones.aceptar_del_primer_inicio(
                    identidad_verificada.correo,
                    identidad_verificada.identificador,
                    hashlib.sha256(invitacion_token.encode("utf-8")).hexdigest(),
                )
            except ErrorDeAlmacen:
                return mantenimiento("no se pudo aceptar la invitación institucional")
            except ValueError:
                return JSONResponse({"detalle": "la invitación no es válida"}, status_code=400)

        if fotos is not None and fotos.configurado and identidad_verificada.foto_url:
            try:
                referencia_actual = identidades.referencia_foto(
                    identidad_verificada.identificador
                )
                if not referencia_actual:
                    from adaptadores.salientes.almacenamiento.foto_google import (
                        descargar_foto_google,
                    )
                    cuerpo_foto = descargar_foto_google(identidad_verificada.foto_url)
                    if cuerpo_foto:
                        nueva = fotos.guardar(cuerpo_foto)
                        try:
                            identidades.cambiar_foto(
                                identidad_verificada.identificador, nueva
                            )
                        except Exception:
                            fotos.retirar(nueva)
            except Exception:

                pass

        if not aprovisionar_rol_configurado(
            roles=roles,
            sujeto_google=identidad_verificada.identificador,
            correo=identidad_verificada.correo,
        ):
            return mantenimiento("no se pudo aprovisionar el rol de esta cuenta")

        try:
            rol = rol_de_presentacion(
                roles=roles,
                registro_docentes=registro_docentes,
                sujeto_google=identidad_verificada.identificador,
                correo=identidad_verificada.correo,
            )
        except ErrorDeAlmacen:

            return mantenimiento("no se pudo determinar el rol de esta cuenta")

        datos = sesiones.abrir(
            rol=rol,
            identificador_estable=identidad_verificada.identificador,
            correo=identidad_verificada.correo,
            nombre=identidad_verificada.nombre,
        )

        if persistida.edad is not None:
            datos["edad"] = persistida.edad
        previo = consentimiento_almacen.consultar(
            identidad_verificada.identificador, identidad_verificada.correo
        )
        if previo and previo.get("decision"):
            datos["consentimiento"] = previo["decision"]

            if persistida.edad is None and previo.get("edad") is not None:
                datos["edad"] = previo["edad"]

        publico = sesiones.publico(datos)
        if roles_aceptados:
            publico["invitacion_aceptada"] = [rol.value for rol in roles_aceptados]
        return _con_cookie(publico, datos["token"])

    @router.post("/api/sesion/reautenticar")
    async def reautenticar(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        cuerpo = await json_del_cuerpo(peticion)
        verificada = identidad.verificar_id_token(str(cuerpo.get("id_token") or ""))
        if verificada is None:
            return JSONResponse(
                {"detalle": "token de Google no válido, expirado o fuera de dominio"},
                status_code=401,
            )
        if verificada.identificador != datos["identificador_estable"]:

            return JSONResponse(
                {
                    "detalle": "ese token no corresponde a la cuenta de esta sesión",
                    "estado": "sujeto_distinto",
                },
                status_code=401,
            )
        if not emision_recien_firmada(
            verificada.emitido_en,
            datetime.now(UTC),
            autenticado_en=verificada.autenticado_en,
        ):

            return JSONResponse(
                {
                    "detalle": (
                        "ese token no es lo bastante reciente para reautenticar: "
                        "vuelva a iniciar sesión con Google"
                    ),
                    "estado": "token_no_fresco",
                },
                status_code=401,
            )

        acreditada = sesiones.marcar_reautenticacion(datos)
        return JSONResponse(
            {
                "reautenticada": True,

                "vigente_por_segundos": SEGUNDOS_DE_REAUTENTICACION_RECIENTE,
                "acreditada_en": acreditada.isoformat(),
            }
        )

    @router.delete("/api/sesion")
    def cerrar_sesion(peticion: Request) -> Response:
        sesiones.cerrar(peticion.cookies.get(COOKIE))
        respuesta = Response(status_code=204)
        respuesta.delete_cookie(COOKIE, **cookies.atributos_de_borrado())
        return respuesta

    @router.post("/api/sesion/renovar")
    def renovar(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        return JSONResponse(sesiones.publico(datos))

    @router.post("/api/sesion/reiniciar")
    def reiniciar_sesion(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa

        sesiones.nueva_conversacion(datos)

        return JSONResponse(sesiones.publico(datos))

    @router.post("/api/consentimiento")
    def consentimiento_retirado() -> JSONResponse:
        return JSONResponse(
            {
                "detalle": (
                    "esta ruta fue retirada: el consentimiento versionado de EQ-021 "
                    "se decide en POST /api/consentimiento/decision-conjunta y la "
                    "edad se declara en POST /api/onboarding/perfil"
                ),
                "estado": "retirada",

                "usar": [
                    "/api/consentimiento/decision-conjunta",
                    "/api/onboarding/perfil",
                ],
            },
            status_code=410,
        )

    @router.get("/api/aviso-legal")
    def aviso_legal_ruta() -> JSONResponse:
        return JSONResponse(aviso_legal.bloque_legal())

    return router
