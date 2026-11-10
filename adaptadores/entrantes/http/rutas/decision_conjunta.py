from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import (
    json_del_cuerpo,
    mantenimiento,
    requerir_sesion,
)
from adaptadores.entrantes.http.rutas.consentimiento_comun import (
    recibo_de,
    responder_con_estado,
)
from dominio.modelo.decision_conjunta import Decision, decision_desde
from dominio.puertos.almacen import (
    AlmacenNoConfigurado,
    AlmacenNoDisponible,
    EscrituraRechazada,
    PerfilSinEdad,
)
from dominio.puertos.decision_conjunta import (
    DecisionYaVigente,
    RevocacionRequerida,
    SupresionEnCurso,
    VersionesFaltantes,
)

if TYPE_CHECKING:
    from fastapi import APIRouter

    from adaptadores.entrantes.http.rutas.consentimiento_comun import Repositorios
from adaptadores.entrantes.http.sesiones import Sesiones
from adaptadores.salientes.notificacion.plantillas import decision_registrada


CAMINO = "/api/consentimiento/decision-conjunta"


RUTAS_DE_REVOCACION = (
    "/api/consentimiento/titular/revocar",
    "/api/consentimiento/asentimiento/revocar",
)


RUTA_DEL_TRAMITE = "/api/datos/supresion"


CLAVES_ADMITIDAS = frozenset({"decision"})


_ASUNTO_DECISION = "Tu autorización quedó registrada"


_CUERPO_DECISION = (
    "Registramos tu decisión sobre el tratamiento de tus datos en DidaxIa.\n\n"
    "Puedes ver la constancia completa —qué versión aceptaste y cuándo— "
    "entrando con tu cuenta institucional.\n\n"
    "Si no fuiste tú, entra y retira la autorización desde «Mis datos»."
)


_CLAVE_DECISION = "decision-conjunta/{secuencia}"
_URL_MIS_DATOS = "https://app.didaxia.pro/mis-datos"


def registrar_en(router: APIRouter, sesiones: Sesiones, repos: Repositorios) -> None:
    @router.post(CAMINO)
    async def decidir(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        cuerpo = await json_del_cuerpo(peticion)

        sobrantes = sorted(set(cuerpo) - CLAVES_ADMITIDAS)
        if sobrantes:
            return JSONResponse(
                {
                    "detalle": (
                        "el cuerpo de esta decisión sólo admite «decision»; el "
                        "servidor resuelve edad, versión, alcance, huella y "
                        f"comprobante. Sobra: {sobrantes}"
                    ),
                    "estado": "cuerpo_no_admitido",
                },
                status_code=400,
            )
        decision = decision_desde(cuerpo.get("decision"))
        if decision is None:
            return JSONResponse({"detalle": "decisión no admitida"}, status_code=400)

        sujeto = datos["identificador_estable"]
        try:
            actos = repos.decision_conjunta.registrar_decision(sujeto, decision)
        except VersionesFaltantes as error:

            return JSONResponse(
                {
                    "detalle": str(error),
                    "estado": "sin_version",
                    "alcances_faltantes": [a.value for a in error.alcances],
                },
                status_code=409,
            )
        except PerfilSinEdad as error:

            return JSONResponse(
                {"detalle": str(error), "estado": "perfil_incompleto"},
                status_code=409,
            )
        except SupresionEnCurso as error:

            return JSONResponse(
                {
                    "detalle": str(error),
                    "estado": "eliminacion_solicitada",
                    "usar": RUTA_DEL_TRAMITE,
                },
                status_code=409,
            )
        except DecisionYaVigente as error:

            return JSONResponse(
                {"detalle": str(error), "estado": "decision_ya_vigente"},
                status_code=409,
            )
        except RevocacionRequerida as error:

            return JSONResponse(
                {
                    "detalle": str(error),
                    "estado": "usar_revocacion",
                    "rutas_de_revocacion": list(RUTAS_DE_REVOCACION),
                },
                status_code=409,
            )
        except EscrituraRechazada as error:

            return JSONResponse({"detalle": str(error)}, status_code=409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo registrar la decisión")

        aviso = False
        if actos.decision is Decision.OTORGADO:
            aviso = repos.notificacion.avisar(
                datos["correo"],
                _ASUNTO_DECISION,
                _CUERPO_DECISION,
                clave_idempotencia=_CLAVE_DECISION.format(
                    secuencia=actos.titular.secuencia
                ),
                html=decision_registrada(
                    destinatario=str(datos.get("nombre") or ""),
                    url_accion=_URL_MIS_DATOS,
                ),
            )

        return responder_con_estado(
            repos,
            sujeto,
            {
                "recibos": [recibo_de(acto, acto.alcance) for acto in actos.actos],
                "aviso_enviado": aviso,
            },
        )
