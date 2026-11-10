from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.investigadores import es_propietario
from adaptadores.entrantes.http.rutas.comun import (
    json_del_cuerpo,
    mantenimiento,
    requerir_sesion,
)
from adaptadores.entrantes.http.sesiones import Sesiones
from adaptadores.salientes.notificacion.plantillas import (
    invitacion_institucional,
    supresion_recibida,
)
from dominio.modelo.propuestas import PropuestaInvalida
from dominio.modelo.roles import Rol, RolInvalido, puede_revisar_evidencia
from dominio.puertos.almacen import (
    AlmacenNoConfigurado,
    AlmacenNoDisponible,
    EscrituraRechazada,
    ReferenciaDesconocida,
)

if TYPE_CHECKING:
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
    from dominio.puertos.gobierno import (
        PuertoAuditoria,
        PuertoNotificacion,
        PuertoPropuestas,
        PuertoRetencion,
        PuertoSolicitudesDeSupresion,
    )
    from dominio.puertos.inventario_de_datos import PuertoInventarioDeDatos
    from dominio.puertos.invitaciones import PuertoInvitaciones
    from dominio.puertos.roles import PuertoAsignacionDeRoles

_ASUNTO_SUPRESION = "Solicitud de eliminación de datos recibida"


_CUERPO_SUPRESION = (
    "Recibimos tu solicitud de eliminación de datos y quedó registrada.\n\n"
    "Puedes consultar su estado, sus plazos y cancelarla dentro del plazo "
    "entrando a DidaxIa con tu cuenta institucional, en «Mis datos».\n\n"
    "Si no fuiste tú, entra y cancélala."
)


_CLAVE_SUPRESION = "supresion-solicitada/{secuencia}"


_OPERACION_RETENCION = "retencion.fijar"


@dataclass(frozen=True)
class RepositoriosDeGobierno:

    supresiones: PuertoSolicitudesDeSupresion
    retencion: PuertoRetencion
    auditoria: PuertoAuditoria
    inventario: PuertoInventarioDeDatos
    roles: PuertoAsignacionDeRoles
    notificacion: PuertoNotificacion
    propuestas: PuertoPropuestas | None = None
    identidades: object | None = None
    invitaciones: PuertoInvitaciones | None = None

def _solicitud_como_json(solicitud) -> dict:
    return {
        "estado": solicitud.estado.value,
        "solicitada_en": solicitud.solicitada_en.isoformat(),
        "cancelable_hasta": solicitud.cancelable_hasta.isoformat(),
        "resolver_antes_de": solicitud.resolver_antes_de.isoformat(),
        "plazo_vigente": solicitud.plazo_vigente.isoformat(),
        "extension_hasta": (
            solicitud.extension_hasta.isoformat() if solicitud.extension_hasta else None
        ),
        "extension_motivo": solicitud.extension_motivo,
        "cerrada_en": solicitud.cerrada_en.isoformat() if solicitud.cerrada_en else None,
    }

def _propuesta_como_json(propuesta) -> dict:
    return {
        "id": propuesta.secuencia,
        "operacion": propuesta.operacion,
        "payload": propuesta.payload,
        "huella": propuesta.huella,
        "estado": propuesta.estado.value,
        "propuesta_por": propuesta.propuesta_por,
        "propuesta_en": (
            propuesta.propuesta_en.isoformat() if propuesta.propuesta_en else None
        ),
        "aprobada_por": propuesta.aprobada_por,
        "aprobada_en": propuesta.aprobada_en.isoformat() if propuesta.aprobada_en else None,
    }

def crear_router(
    sesiones: Sesiones,
    repos: RepositoriosDeGobierno,
    puerta: PuertaDeSupresion,
) -> APIRouter:
    router = APIRouter()

    def _instante_auditoria(valor: object) -> datetime | None:
        if not valor:
            return None
        try:
            instante = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("fecha de auditoría no válida") from exc
        return instante if instante.tzinfo else instante.replace(
            tzinfo=ZoneInfo("America/Bogota")
        )

    def _filtros_auditoria(origen) -> dict:
        return {
            "operacion": origen.get("operacion") or "",
            "actor_filtro": origen.get("actor") or "",
            "sujeto_filtro": origen.get("sujeto") or "",
            "desde": _instante_auditoria(origen.get("desde")),
            "hasta": _instante_auditoria(origen.get("hasta")),
            "categoria": origen.get("categoria") or "",
            "doble_aprobacion": origen.get("doble_aprobacion") or "",
        }

    def _congelada(sujeto: str) -> JSONResponse | None:
        return puerta.negativa(sujeto)

    def _es_investigador(sujeto: str) -> bool | None:
        try:
            return puede_revisar_evidencia(repos.roles.roles_de(sujeto))
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return None

    def _exigir_investigador(sujeto: str) -> JSONResponse | None:
        autorizado = _es_investigador(sujeto)
        if autorizado is None:
            return mantenimiento("no se pudieron comprobar los permisos")
        if not autorizado:
            return JSONResponse(
                {"detalle": "esta operación la reserva EQ-023 a un investigador autorizado"},
                status_code=403,
            )
        return None

    def _propuestas_o_mantenimiento():
        if repos.propuestas is None:
            return None, mantenimiento("el registro de propuestas no está disponible")
        return repos.propuestas, None

    def _invitaciones_o_mantenimiento():
        if repos.invitaciones is None:
            return None, mantenimiento("el registro de invitaciones no está disponible")
        return repos.invitaciones, None

    @router.get("/api/investigacion/auditoria")
    def consultar_auditoria(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        actor = datos["identificador_estable"]
        if (impedido := _exigir_investigador(actor)) is not None:
            return impedido
        if (congelada := _congelada(actor)) is not None:
            return congelada
        try:
            pagina = int(peticion.query_params.get("pagina") or "1")
        except ValueError:
            return JSONResponse({"detalle": "página no válida"}, status_code=400)
        try:
            resultado = repos.auditoria.consultar_institucional(
                actor,
                pagina,
                25,
                **_filtros_auditoria(peticion.query_params),
            )
        except ValueError as error_pagina:
            return JSONResponse({"detalle": str(error_pagina)}, status_code=400)
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo consultar la auditoría institucional")
        return JSONResponse(resultado)

    @router.post("/api/investigacion/auditoria/informe")
    async def descargar_informe_auditoria(peticion: Request) -> Response:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        actor = datos["identificador_estable"]
        if (impedido := _exigir_investigador(actor)) is not None:
            return impedido
        if (congelada := _congelada(actor)) is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        corte_instante = datetime.now(UTC)
        try:
            documento, recibo = repos.auditoria.informe_institucional(
                actor,
                filtros=_filtros_auditoria(cuerpo.get("filtros") or {}),
                confirmado=cuerpo.get("confirmado") is True,
                corte_instante=corte_instante,
            )
        except ValueError as error:
            return JSONResponse({"detalle": str(error)}, status_code=400)
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo generar y auditar el informe")
        fecha = corte_instante.astimezone(ZoneInfo("America/Bogota")).date().isoformat()
        return Response(
            documento,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="didaxia-auditoria-{fecha}.pdf"'
                ),
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "X-DidaxIA-Corte-Secuencia": str(recibo["corte_secuencia"]),
            },
        )

    @router.get("/api/gobierno/invitaciones")
    def listar_invitaciones(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        actor = datos["identificador_estable"]
        if (impedido := _exigir_investigador(actor)) is not None:
            return impedido
        if (congelada := _congelada(actor)) is not None:
            return congelada
        invitaciones, error = _invitaciones_o_mantenimiento()
        if error is not None:
            return error
        try:
            filas = invitaciones.listar(actor)
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudieron consultar las invitaciones")
        return JSONResponse({"invitaciones": [fila.como_publica() for fila in filas]})

    @router.post("/api/gobierno/invitaciones")
    async def emitir_invitacion(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        actor = datos["identificador_estable"]
        if (impedido := _exigir_investigador(actor)) is not None:
            return impedido
        if (congelada := _congelada(actor)) is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        correo = str(cuerpo.get("correo") or "").strip().lower()
        try:
            rol = Rol(str(cuerpo.get("rol") or ""))
        except ValueError:
            return JSONResponse({"detalle": "rol no admitido"}, status_code=400)
        if (reservado := _exigir_propietario_para_investigacion(datos, rol)) is not None:
            return reservado
        invitaciones, error = _invitaciones_o_mantenimiento()
        if error is not None:
            return error
        token = secrets.token_urlsafe(32)
        huella = hashlib.sha256(token.encode("utf-8")).hexdigest()
        try:
            invitacion = invitaciones.emitir(
                correo, rol, emisor=actor, token_huella=huella, vigencia=timedelta(days=7)
            )
        except ValueError as error_validacion:
            return JSONResponse({"detalle": str(error_validacion)}, status_code=400)
        except EscrituraRechazada as error_escritura:
            return JSONResponse({"detalle": str(error_escritura)}, status_code=409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo registrar la invitación")

        origen = os.environ.get("ORIGEN_APLICACION", "https://app.didaxia.pro").rstrip("/")
        enlace = f"{origen}/?{urlencode({'invitacion': token})}"
        nombre_rol = "investigador delegado" if rol is Rol.INVESTIGADOR_ADMINISTRADOR else "docente"
        texto = (
            f"Te invitaron a DidaxIa con la función de {nombre_rol}.\n\n"
            f"Acepta la invitación iniciando sesión con {correo} antes de "
            f"{invitacion.expira_en.isoformat()}:\n{enlace}\n\n"
            "El enlace sólo funciona para esa cuenta institucional."
        )
        aviso_enviado = repos.notificacion.avisar(
            correo,
            "Invitación institucional a DidaxIa",
            texto,
            clave_idempotencia=f"invitacion-rol/{invitacion.secuencia}",
            html=invitacion_institucional(
                destinatario="Hola",
                rol=nombre_rol,
                correo=correo,
                vence=invitacion.expira_en.isoformat(),
                url_accion=enlace,
            ),
        )
        publico = invitacion.como_publica()
        publico["aviso_enviado"] = aviso_enviado
        return JSONResponse({"invitacion": publico}, status_code=201)

    @router.delete("/api/gobierno/invitaciones/{secuencia}")
    def revocar_invitacion(secuencia: int, peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        actor = datos["identificador_estable"]
        if (impedido := _exigir_investigador(actor)) is not None:
            return impedido
        if (congelada := _congelada(actor)) is not None:
            return congelada
        invitaciones, error = _invitaciones_o_mantenimiento()
        if error is not None:
            return error
        try:
            invitacion = invitaciones.revocar(secuencia, actor=actor)
        except EscrituraRechazada as error_escritura:
            detalle = str(error_escritura)
            codigo = 403 if "propietaria" in detalle else 409
            return JSONResponse({"detalle": detalle}, status_code=codigo)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo revocar la invitación")
        if invitacion is None:
            return JSONResponse({"detalle": "invitación no encontrada"}, status_code=404)
        return JSONResponse({"invitacion": invitacion.como_publica()})

    @router.post("/api/datos/supresion")
    async def solicitar_supresion(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        cuerpo = await json_del_cuerpo(peticion)
        sujeto = datos["identificador_estable"]

        if not sesiones.reautenticacion_vigente(datos):
            return JSONResponse(
                {
                    "detalle": (
                        "hace falta una reautenticación reciente con Google: "
                        "use POST /api/sesion/reautenticar"
                    ),
                    "estado": "reautenticacion_requerida",
                },
                status_code=401,
            )
        reautenticada_en = sesiones.prueba_de_reautenticacion(datos)

        try:
            solicitud = repos.supresiones.abrir(
                sujeto,
                reautenticada_en=reautenticada_en,
                frase=str(cuerpo.get("frase") or ""),
                actor=sujeto,
            )
        except EscrituraRechazada as error:
            return JSONResponse({"detalle": str(error)}, status_code=409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):

            return mantenimiento("no se pudo registrar la solicitud")

        aviso = repos.notificacion.avisar(
            datos["correo"],
            _ASUNTO_SUPRESION,
            _CUERPO_SUPRESION,
            clave_idempotencia=_CLAVE_SUPRESION.format(secuencia=solicitud.secuencia),
            html=supresion_recibida(
                destinatario=str(datos.get("nombre") or ""),
                url_accion=(
                    f"{os.environ.get('ORIGEN_APLICACION', 'https://app.didaxia.pro').rstrip('/')}/mis-datos"
                ),
            ),
        )

        salida = _solicitud_como_json(solicitud)
        salida["aviso_enviado"] = aviso
        return JSONResponse(salida, status_code=201)

    @router.get("/api/datos/supresion")
    def estado_de_supresion(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        try:
            abierta = repos.supresiones.abierta_de(datos["identificador_estable"])
            historial = repos.supresiones.historial(datos["identificador_estable"])
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer el estado del trámite")
        return JSONResponse(
            {
                "abierta": _solicitud_como_json(abierta) if abierta else None,
                "historial": [_solicitud_como_json(s) for s in historial],
            }
        )

    @router.delete("/api/datos/supresion")
    def cancelar_supresion(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        sujeto = datos["identificador_estable"]
        try:
            cancelada = repos.supresiones.cancelar(
                sujeto, ahora=datetime.now(UTC), actor=sujeto
            )
        except EscrituraRechazada as error:
            return JSONResponse({"detalle": str(error)}, status_code=409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo cancelar el trámite")
        if not cancelada:
            return JSONResponse(
                {"detalle": "no hay ningún trámite abierto que cancelar"}, status_code=404
            )
        return JSONResponse({"estado": "cancelada"})

    @router.get("/api/datos/retencion")
    def retencion(peticion: Request) -> JSONResponse:
        _datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        try:
            politica = repos.retencion.vigente()
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la política de retención")
        return JSONResponse(
            {
                "sustentacion_en": (
                    politica.sustentacion_en.isoformat() if politica.sustentacion_en else None
                ),
                "meses_despues": politica.meses_despues,
                "limite": politica.limite.isoformat() if politica.limite else None,
                "nota": politica.nota,
            }
        )

    @router.get("/api/datos/inventario")
    def inventario(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        propio = datos["identificador_estable"]
        pedido = peticion.query_params.get("sujeto") or propio
        ajeno = pedido != propio

        if ajeno and (impedido := _exigir_investigador(propio)) is not None:
            return impedido

        if ajeno and (congelada := _congelada(propio)) is not None:
            return congelada

        try:
            resultado = repos.inventario.inventariar(pedido, actor=propio if ajeno else "")
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo construir el inventario")

        return JSONResponse(resultado.como_json())

    @router.post("/api/datos/retencion")
    async def proponer_retencion(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        actor = datos["identificador_estable"]
        if (impedido := _exigir_investigador(actor)) is not None:
            return impedido
        if (congelada := _congelada(actor)) is not None:
            return congelada

        if (congelada := _congelada(datos["identificador_estable"])) is not None:
            return congelada
        propuestas, sin_almacen = _propuestas_o_mantenimiento()
        if sin_almacen is not None:
            return sin_almacen

        cuerpo = await json_del_cuerpo(peticion)
        crudo = str(cuerpo.get("sustentacion_en") or "")
        try:
            sustentacion = datetime.fromisoformat(crudo)
        except ValueError:
            return JSONResponse({"detalle": "fecha de sustentación no admitida"}, status_code=400)
        if sustentacion.tzinfo is None:
            sustentacion = sustentacion.replace(tzinfo=UTC)

        payload = {"sustentacion_en": sustentacion.isoformat()}
        if "meses_despues" in cuerpo:
            try:
                payload["meses_despues"] = int(cuerpo["meses_despues"])
            except (TypeError, ValueError):
                return JSONResponse({"detalle": "meses_despues no admitido"}, status_code=400)

        try:
            propuesta = propuestas.crear(_OPERACION_RETENCION, payload, propuesta_por=actor)
        except PropuestaInvalida as error:
            return JSONResponse({"detalle": str(error)}, status_code=400)
        except EscrituraRechazada as error:
            return JSONResponse({"detalle": str(error)}, status_code=409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo registrar la propuesta")

        return JSONResponse(_propuesta_como_json(propuesta), status_code=201)

    @router.get("/api/gobierno/propuestas")
    def listar_propuestas(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        if (impedido := _exigir_investigador(datos["identificador_estable"])) is not None:
            return impedido

        if (congelada := _congelada(datos["identificador_estable"])) is not None:
            return congelada
        propuestas, sin_almacen = _propuestas_o_mantenimiento()
        if sin_almacen is not None:
            return sin_almacen
        try:
            pendientes = propuestas.pendientes()
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudieron leer las propuestas")
        return JSONResponse({"pendientes": [_propuesta_como_json(p) for p in pendientes]})

    @router.post("/api/gobierno/propuestas/{propuesta}/aprobar")
    def aprobar_propuesta(propuesta: int, peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        aprobador = datos["identificador_estable"]
        if (impedido := _exigir_investigador(aprobador)) is not None:
            return impedido
        if (congelada := _congelada(aprobador)) is not None:
            return congelada

        if (congelada := _congelada(datos["identificador_estable"])) is not None:
            return congelada
        propuestas, sin_almacen = _propuestas_o_mantenimiento()
        if sin_almacen is not None:
            return sin_almacen

        try:
            aprobada = propuestas.aprobar(propuesta, aprobador=aprobador)
        except ReferenciaDesconocida:
            return JSONResponse({"detalle": "esa propuesta no existe"}, status_code=404)
        except EscrituraRechazada as error:
            return _conflicto_de_propuesta(propuestas, propuesta, str(error))
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo aprobar la propuesta")

        return JSONResponse(_propuesta_como_json(aprobada))

    def _conflicto_de_propuesta(propuestas, identificador: int, motivo: str) -> JSONResponse:
        cuerpo = {"detalle": motivo}
        try:
            actual = propuestas.consultar(identificador)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            actual = None
        if actual is not None:
            cuerpo.update(_propuesta_como_json(actual))
            cuerpo["detalle"] = motivo
        return JSONResponse(cuerpo, status_code=409)

    def _rol_del_cuerpo(cuerpo: dict) -> tuple[str, Rol | None, JSONResponse | None]:
        sujeto = str(cuerpo.get("sujeto") or "").strip()
        if not sujeto:
            return "", None, JSONResponse(
                {"detalle": "hace falta el sujeto sobre el que actuar"}, status_code=400
            )
        try:
            rol = Rol(str(cuerpo.get("rol") or ""))
        except ValueError:
            return "", None, JSONResponse({"detalle": "rol no admitido"}, status_code=400)
        return sujeto, rol, None

    def _exigir_propietario_para_investigacion(
        datos: dict, rol: Rol
    ) -> JSONResponse | None:

        if rol is Rol.INVESTIGADOR_ADMINISTRADOR and not es_propietario(
            str(datos.get("correo") or "")
        ):
            return JSONResponse(
                {
                    "detalle": (
                        "sólo una cuenta propietaria puede asignar o retirar "
                        "investigadores"
                    )
                },
                status_code=403,
            )
        return None

    def _proteger_propietario(sujeto: str, rol: Rol) -> JSONResponse | None:
        if rol is not Rol.INVESTIGADOR_ADMINISTRADOR or repos.identidades is None:
            return None
        try:
            perfil_objetivo = repos.identidades.consultar(sujeto)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo comprobar la cuenta protegida")
        if perfil_objetivo is not None and es_propietario(
            perfil_objetivo.identidad.correo
        ):
            return JSONResponse(
                {"detalle": "esta cuenta propietaria se administra desde el entorno"},
                status_code=409,
            )
        return None

    @router.get("/api/gobierno/roles")
    def mis_roles(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        try:
            if (congelada := _congelada(datos["identificador_estable"])) is not None:
                return congelada
            roles = repos.roles.roles_de(datos["identificador_estable"])
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudieron leer los roles")
        return JSONResponse({"roles": sorted(r.value for r in roles)})

    @router.post("/api/gobierno/roles")
    async def asignar_rol(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        actor = datos["identificador_estable"]
        if (impedido := _exigir_investigador(actor)) is not None:
            return impedido
        if (congelada := _congelada(actor)) is not None:
            return congelada

        sujeto, rol, invalido = _rol_del_cuerpo(await json_del_cuerpo(peticion))
        if invalido is not None:
            return invalido
        if (reservado := _exigir_propietario_para_investigacion(datos, rol)) is not None:
            return reservado
        if sujeto == actor:
            return JSONResponse(
                {"detalle": "nadie puede otorgarse un rol a sí mismo (EQ-023)"},
                status_code=409,
            )

        try:
            asignacion = repos.roles.asignar(sujeto, rol, actor)
        except RolInvalido as error:
            return JSONResponse({"detalle": str(error)}, status_code=400)
        except ReferenciaDesconocida:
            return JSONResponse({"detalle": "esa persona no está registrada"}, status_code=404)
        except EscrituraRechazada as error:
            return JSONResponse({"detalle": str(error)}, status_code=409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo asignar el rol")

        return JSONResponse(
            {
                "sujeto": asignacion.sujeto_google,
                "rol": asignacion.rol.value,
                "otorgado_por": asignacion.otorgado_por,
                "otorgado_en": asignacion.otorgado_en.isoformat(),
            },
            status_code=201,
        )

    @router.delete("/api/gobierno/roles")
    async def revocar_rol(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        actor = datos["identificador_estable"]
        if (impedido := _exigir_investigador(actor)) is not None:
            return impedido
        if (congelada := _congelada(actor)) is not None:
            return congelada

        sujeto, rol, invalido = _rol_del_cuerpo(await json_del_cuerpo(peticion))
        if invalido is not None:
            return invalido
        if (reservado := _exigir_propietario_para_investigacion(datos, rol)) is not None:
            return reservado
        if sujeto == actor:
            return JSONResponse(
                {"detalle": "nadie puede retirarse su propio rol (EQ-023)"}, status_code=409
            )
        if (protegido := _proteger_propietario(sujeto, rol)) is not None:
            return protegido

        try:
            revocada = repos.roles.revocar(sujeto, rol, actor)
        except ReferenciaDesconocida:
            return JSONResponse({"detalle": "esa persona no está registrada"}, status_code=404)
        except EscrituraRechazada as error:
            return JSONResponse({"detalle": str(error)}, status_code=409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo retirar el rol")
        if not revocada:
            return JSONResponse(
                {"detalle": "esa persona no tiene ese rol vigente"}, status_code=404
            )
        return JSONResponse({"sujeto": sujeto, "rol": rol.value, "revocado_por": actor})

    return router

_ROL_DE_INVESTIGADOR = Rol.INVESTIGADOR_ADMINISTRADOR
