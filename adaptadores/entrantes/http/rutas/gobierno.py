"""
gobierno.py — Supresión solicitada, retención, propuestas, roles e inventario
===========================================================================

La parte **reversible y auditable** del gobierno de datos de `EQ-022`/`EQ-023`,
por API.

⚠️ Aquí no se borra nada, y es el límite del hito
------------------------------------------------------------
No hay ninguna ruta que elimine ni anonimice. `POST /api/datos/supresion` abre un
**trámite**; `DELETE` sobre él lo cancela. Lo que ocurre cuando el plazo vence lo
decide el cierre V-B, porque cambiar el sujeto técnico de una conversación sólo
la seudonimiza —su texto puede llevar dentro nombres y correos— y llamar anónimo
a eso sería falso.

`GET /api/datos/inventario` responde qué **alcanzaría** una supresión: tablas,
conteos y qué queda fuera del alcance de una cascada de hoy. Conteos, nunca
contenidos: un inventario que imprimiera lo que va a borrar sería una exportación
disfrazada.

⚠️ La reautenticación no llega en el cuerpo · hito R3
------------------------------------------------------------
`POST /api/datos/supresion` recibía `reautenticada_en` del cliente y lo
contrastaba con el reloj del servidor, declarándolo *«no es una comprobación
fuerte»*. No lo era en absoluto: cualquiera que llame al API escribe la fecha que
quiera, así que la condición de `EQ-022` no existía. Ahora la prueba la acredita
`POST /api/sesion/reautenticar` con un `id_token` del mismo sujeto y vive del
lado servidor; esta ruta **la consume** y no lee ninguna fecha del cuerpo.

⚠️ Dos aprobaciones son dos peticiones autenticadas · hito R5
------------------------------------------------------------
`POST /api/datos/retencion` pedía `aprobada_por` en el cuerpo y daba la política
por aprobada. Eso no es una segunda aprobación: es el primer administrador
escribiendo el nombre del segundo. Ahora esa ruta **propone** —deja una propuesta
pendiente— y `POST /api/gobierno/propuestas/{id}/aprobar` la aprueba desde otra
sesión, de otra persona. Aprobación, efecto y auditoría se confirman en una sola
transacción dentro del repositorio.

⚠️ La auditoría ya no es «best effort» · hito R5
------------------------------------------------------------
`_auditar()` capturaba el fallo y seguía, con el argumento de que *«la operación
YA está registrada»*. Eso es exactamente lo que `EQ-023` no admite: una operación
auditable que informa éxito sin auditoría. La constancia la escriben ahora los
repositorios **dentro de la transacción** de la operación; si falla, la operación
no ocurre. La función desapareció, y con ella la posibilidad de volver a usarla.

Lo que sigue sin decidir el sistema
--------------------------------------
- **Si el aviso sale.** `PuertoNotificacion`, que desde `D2` puede ser Resend o
  el adaptador que anota sin enviar, según lo que haya configurado. `EQ-024`: el
  canal no decide el trámite. Lo que sí se hace es **representar** su resultado
  —`aviso_enviado`— en vez de fingir un envío.
- **Quién es el primer investigador.** Ninguna ruta crea un administrador donde
  no hay ninguno: `POST /api/gobierno/roles` exige uno vigente. La primera
  asignación es una operación deliberada del equipo contra la base.


"""

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

if TYPE_CHECKING:  # pragma: no cover
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

#: `EQ-022` · el asunto del aviso al correo institucional. Sin datos dentro y sin
#: el nombre de nadie: un asunto se lee en la bandeja antes de abrir el correo.
_ASUNTO_SUPRESION = "Solicitud de eliminación de datos recibida"

#: El texto del aviso. `D2` lo fija aquí y no en el adaptador porque **es del
#: caso de uso**: qué se le cuenta a la persona sobre su trámite no lo decide el
#: transporte. Lo mínimo para entender el hecho y una remisión a la aplicación
#: autenticada; ni plazos copiados, ni identificadores, ni datos de la solicitud
#: —que ya están en la pantalla y cambian si hay extensión—.
_CUERPO_SUPRESION = (
    "Recibimos tu solicitud de eliminación de datos y quedó registrada.\n\n"
    "Puedes consultar su estado, sus plazos y cancelarla dentro del plazo "
    "entrando a DidaxIa con tu cuenta institucional, en «Mis datos».\n\n"
    "Si no fuiste tú, entra y cancélala."
)

#: Cómo se deriva la clave de idempotencia del aviso de supresión (`D2`).
#:
#: De `solicitud.secuencia`, que es el identificador que asignó PostgreSQL a la
#: fila **ya confirmada**, y nunca del correo: dos personas distintas producen
#: dos claves distintas porque son dos filas, no porque sean dos correos. Es
#: estable —un reintento del mismo trámite da la misma clave— y corta, muy por
#: debajo de los 256 caracteres que Resend admite.
_CLAVE_SUPRESION = "supresion-solicitada/{secuencia}"

#: Qué operación propone `POST /api/datos/retencion`. El nombre lo valida el
#: dominio (`OPERACIONES_CON_DOBLE_APROBACION`); aquí sólo se nombra.
_OPERACION_RETENCION = "retencion.fijar"


@dataclass(frozen=True)
class RepositoriosDeGobierno:
    """Los siete puertos de este recorrido, agrupados por composición.

    Mismo criterio que `rutas/consentimiento.py`: campos nombrados y tipados en
    vez de siete posiciones intercambiables.

    `propuestas` admite `None` **sólo** para no romper a quien componga sin la
    migración 12; sin él, las rutas de doble aprobación responden mantenimiento
    en vez de aprobar sin propuesta, que sería el defecto de vuelta.
    """

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
    """El trámite tal como lo ve su titular. Sin datos de nadie más."""
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
    """Lo que identifica una propuesta y permite comprobar qué se aprobó.

    `huella` viaja en las dos respuestas —al proponer y al aprobar— para que el
    segundo administrador pueda confirmar que aprueba lo mismo que se propuso sin
    tener que comparar el contenido campo a campo.
    """
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
        """La negativa si el ACTOR tiene su propio trámite abierto, o `None`.

        ⚠️ **No se aplica a las tres rutas del propio trámite.** Consultar la
        solicitud, cancelarla y ver la retención vigente son precisamente lo que
        `ESTADO-ACTUAL.md` §10.2 conserva durante la supresión: ponerles esta
        puerta habría dejado a alguien sin poder cancelar lo que pidió, que es el
        peor resultado posible de una corrección pensada para protegerlo.

        Sí se aplica a proponer retención, aprobar propuestas, gobernar roles y
        **leer** las propuestas, los roles y el inventario de otra persona: son
        acciones administrativas de producto, no derechos del titular.

        `GET /api/datos/retencion` queda fuera: es información sobre cuánto se
        conserva, y quien está en trámite tiene más motivo que nadie para
        consultarla.
        """
        return puerta.negativa(sujeto)


    def _es_investigador(sujeto: str) -> bool | None:
        """`True`/`False`, o `None` si no se puede saber (almacén caído).

        Tres valores y no dos: tratar «no lo sé» como `False` daría un 403 a
        alguien que sí tiene el permiso, y como `True` daría acceso a quien no.
        """
        try:
            return puede_revisar_evidencia(repos.roles.roles_de(sujeto))
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return None

    def _exigir_investigador(sujeto: str) -> JSONResponse | None:
        """`None` si puede seguir; si no, la respuesta ya hecha.

        ⚠️ Esta comprobación es la del **borde**, y no sustituye a la del
        repositorio: el rol se vuelve a exigir dentro de la transacción, donde un
        rol retirado un segundo antes ya no cuenta. Aquí existe para dar un 403
        con motivo en vez de un 409 genérico.
        """
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
        """`EQ-022` · abre el trámite. **No borra nada.**

        Exige las tres condiciones de la decisión: reautenticación reciente
        acreditada por el servidor, frase de confirmación validada **por el
        backend** y que no haya otro trámite abierto.

        ⚠️ **La reautenticación no llega en el cuerpo** (hito R3). Se consume la
        prueba que `POST /api/sesion/reautenticar` dejó en el almacén de sesiones
        tras verificar un `id_token` del mismo sujeto institucional. Si no hay
        prueba, o ya caducó, se responde 401 con el estado que el cliente
        necesita para mandar a la persona a Google — no un 400, porque la
        petición está bien formada y lo que falta es una credencial fresca.
        """
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
            # Cubre también el fallo de la auditoría: va en la misma transacción,
            # así que si no se pudo registrar, el trámite no quedó abierto y
            # decir «solicitada» sería mentira (`EQ-023`).
            return mantenimiento("no se pudo registrar la solicitud")

        # `EQ-022` · aviso al correo institucional. **Fuera** de la transacción y
        # sin poder deshacerla: `EQ-024` dice que el canal no decide el trámite.
        # Su resultado se representa, no se finge.
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
        """El trámite abierto y el historial de los cerrados."""
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
        """`EQ-022` · 24 horas para cancelar.

        Pasado el plazo devuelve 409 con el motivo: que la ventana se cierre
        **no ejecuta nada**, sólo retira la cancelación por parte del titular.

        La constancia va en la misma transacción que el `UPDATE` (hito R5): si la
        auditoría falla, el trámite sigue abierto y se responde mantenimiento.
        Decirle a alguien que canceló algo que sigue en curso sería el peor de
        los dos errores posibles.
        """
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
        """`EQ-022` · el plazo, representable y consultable.

        Hoy `sustentacion_en` es `null` y `limite` también: la fecha no existe y
        una inventada sería peor que ninguna. `limite` se calcula en **meses
        calendario** (`dominio/modelo/calendario.py`), no en bloques de 30 días.
        """
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
        """Qué alcanzaría una supresión de quien llama. Conteos, no contenidos.

        Es la simulación que el cierre V-B necesita: qué tablas, cuántas filas,
        cuáles llevan texto libre —seudonimizar no es anonimizar— y qué queda
        fuera del alcance de una cascada de hoy.

        Cada titular ve **el suyo**. Un investigador puede pedir el de otra
        persona con `?sujeto=`, y esa consulta **queda auditada dentro de la
        misma transacción** (`EQ-023`, hito R5): si la constancia no se puede
        escribir, no se devuelven los conteos.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        propio = datos["identificador_estable"]
        pedido = peticion.query_params.get("sujeto") or propio
        ajeno = pedido != propio

        if ajeno and (impedido := _exigir_investigador(propio)) is not None:
            return impedido
        # ⚠️ **Sólo el AJENO se bloquea, y antes de auditar o consultar.**
        #
        # El inventario propio es un derecho del titular: saber qué alcanzaría su
        # supresión es justo lo que necesita quien la pidió. El de otra persona es
        # una acción de investigación, y `inventariar()` la audita dentro de su
        # transacción — así que rechazarla después habría dejado la constancia de
        # una consulta que no debía ocurrir.
        if ajeno and (congelada := _congelada(propio)) is not None:
            return congelada

        try:
            resultado = repos.inventario.inventariar(pedido, actor=propio if ajeno else "")
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo construir el inventario")

        return JSONResponse(resultado.como_json())

    # ── la doble aprobación de EQ-023 ────────────────────────────────────────

    @router.post("/api/datos/retencion")
    async def proponer_retencion(peticion: Request) -> JSONResponse:
        """`EQ-023` · **propone** la política. No la fija.

        Es la primera de las dos peticiones autenticadas. Devuelve **201 con
        estado `pendiente`** y la huella del contenido; la política no cambia
        hasta que otro administrador apruebe esa propuesta por su identificador.

        ⚠️ **`aprobada_por` del cuerpo se ignora por completo** — no se lee, no se
        valida y no se menciona. Leerlo para rechazarlo habría dejado el nombre
        vivo en el código y la puerta entreabierta para el siguiente que lo
        creyera útil.
        """
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

        # El payload se normaliza aquí, antes de calcular la huella: si cada
        # cliente mandara la fecha con un formato distinto, dos propuestas del
        # mismo contenido tendrían huellas distintas.
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
        """Las propuestas que esperan a un segundo administrador.

        Es lo que el segundo necesita para poder aprobar: sin esta ruta tendría
        que enterarse del identificador por un canal fuera del sistema, y una
        aprobación que depende de un mensaje por otro medio no es auditable.
        """
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
        """`EQ-023` · la **segunda** petición autenticada, de otra persona.

        El aprobador sale de la sesión y de ningún otro sitio. El repositorio
        comprueba el rol, que no sea suya, que siga pendiente y que el contenido
        coincida con su huella; después aplica el efecto y audita, todo en una
        transacción.

        Aprobar dos veces devuelve **409 con el estado actual**: es un rechazo
        limpio y, a diferencia de un 409 seco, deja ver que la propuesta ya está
        aprobada, de modo que un reintento por corte de red no queda en duda.
        """
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
        """El 409 de una aprobación que no procede, con el estado si se puede leer.

        Añadir el estado no es decorativo: distingue «ya estaba aprobada» —donde
        el efecto ocurrió una vez y está bien— de «no puedes aprobar la tuya»,
        que exige a otra persona. Sin él las dos serían el mismo 409.
        """
        cuerpo = {"detalle": motivo}
        try:
            actual = propuestas.consultar(identificador)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            actual = None
        if actual is not None:
            cuerpo.update(_propuesta_como_json(actual))
            cuerpo["detalle"] = motivo
        return JSONResponse(cuerpo, status_code=409)

    # ── permisos · EQ-023 ────────────────────────────────────────────────────

    def _rol_del_cuerpo(cuerpo: dict) -> tuple[str, Rol | None, JSONResponse | None]:
        """`(sujeto, rol, negativa)`. Lo común a asignar y a revocar.

        El sujeto sobre el que se actúa **sí** viene del cuerpo —es a quién se le
        da o se le quita—, pero el **actor** nunca: ése sale de la sesión. Son
        dos cosas distintas y confundirlas es cómo alguien se atribuiría una
        decisión ajena.
        """
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
        """Reserva el gobierno de investigadores al núcleo del entorno.

        Un investigador delegado sigue pudiendo administrar docentes y sus
        facultades, pero no puede multiplicar administradores. La identidad
        propietaria sale del correo que Google verificó para la sesión; nunca
        de un campo enviado por el cliente.
        """
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
        """Impide retirar desde HTTP el núcleo declarado en el entorno."""
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
        """Los roles vigentes de quien llama. Sólo los suyos.

        Sin parámetro para preguntar por otro: eso sería una consulta de datos
        ajenos y tendría que auditarse. Quien administra ya ve el historial
        completo al asignar o revocar.
        """
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
        """`EQ-023` · otorga un rol. Sólo un investigador vigente, y no a sí mismo.

        Las tres reglas del encargo, y dónde vive cada una:

        - **sólo un investigador-administrador vigente** — `_exigir_investigador()`
          aquí para el motivo, y otra vez dentro de la transacción para que un rol
          retirado un segundo antes no se cuele;
        - **nadie se eleva a sí mismo** — aquí, comparando con el actor de la
          sesión. No es redundante con la anterior: alguien que ya tiene el rol
          pasaría esa comprobación y aun así no puede otorgárselo;
        - **no hay bootstrap remoto** — es consecuencia de la primera: sin ningún
          investigador vigente, ninguna sesión pasa, y la primera asignación la
          hace el equipo contra la base.

        El actor sale de la sesión. Un `otorgado_por` en el cuerpo se ignora.
        """
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
        """`EQ-023` · retira un rol, conservando autor y fecha.

        No borra la fila: le pone `revocado_por` y `revocado_en`. Una aprobación
        de hace un mes tiene que seguir explicándose, y si la asignación
        desapareciera quedaría hecha por alguien que —según la base— nunca pudo
        hacerla.

        Nadie se revoca a sí mismo, por el mismo motivo que nadie se eleva: un
        administrador que se retirara el rol podría dejar el sistema sin ninguno,
        y recuperarlo exigiría volver a la base.
        """
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


#: Se importa para dejar constancia de que el rol que estas rutas consultan es el
#: único de `EQ-023`; una prueba lo comprueba contra el enumerado.
_ROL_DE_INVESTIGADOR = Rol.INVESTIGADOR_ADMINISTRADOR
