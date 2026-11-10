from __future__ import annotations

from datetime import datetime, timezone

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

ALMACEN_PERFIL = "perfil versionado (PM-B11): afectivo, conceptual y estratégico"
ALMACEN_REGISTRO = "registro del turno (DD-08): fila de registro_turno y su archivo JSON"
ALMACEN_HISTORIAL = "historial de conversación (PM-B37): el texto de sus turnos"


ALMACEN_CLASES = "matrícula en clases (DD-12)"


_ALCANZA_SIEMPRE = (
    "sesión en memoria (rol, consentimiento, contadores del arbitraje)",
    ALMACEN_CLASES,
)
_NO_ALCANZA_AUN = (

    "telemetría por afirmación (RF-REG-03 a RF-REG-08, sin construir)",
)


def consultar(datos_de_sesion: dict) -> dict:
    identidad_verificada = bool(datos_de_sesion.get("identificador_estable"))
    return {

        "sesion": datos_de_sesion.get("conversacion"),
        "rol": datos_de_sesion.get("rol"),
        "nombre": datos_de_sesion.get("nombre") or None,
        "correo": datos_de_sesion.get("correo") or None,
        "consentimiento": datos_de_sesion.get("consentimiento"),

        "edad": datos_de_sesion.get("edad"),
        "intentos": datos_de_sesion.get("intentos"),
        "insistencias": datos_de_sesion.get("insistencias"),
        "peticion_confirmada": datos_de_sesion.get("peticion_confirmada"),

        "via_de_supresion": {
            "disponible": identidad_verificada,
            "ruta": "/api/datos/supresion" if identidad_verificada else None,
            "motivo": (
                "el trámite de EQ-022 se abre en POST /api/datos/supresion tras "
                "reautenticarse con Google (POST /api/sesion/reautenticar); "
                "dispone de 24 horas para cancelarlo"
                if identidad_verificada
                else "esta sesión no tiene identidad verificada; sin ella no hay de "
                "qué colgar el trámite (DD-18)"
            ),
        },
    }

def exportar(datos_de_sesion: dict) -> dict:
    return {
        "exportado_en": datetime.now(UTC).isoformat(timespec="seconds"),
        "datos": consultar(datos_de_sesion),
    }

def plan_de_supresion(
    *,
    perfil_conectado: bool,
    registro_conectado: bool = False,
    historial_conectado: bool = False,
) -> dict:

    alcanza = list(_ALCANZA_SIEMPRE)
    no_alcanza = list(_NO_ALCANZA_AUN)
    if perfil_conectado:
        alcanza.append(ALMACEN_PERFIL)
    else:
        no_alcanza.insert(0, "perfil versionado (PM-B11 existe; AGENTE_BD no está configurada)")
    if registro_conectado:
        alcanza.append(ALMACEN_REGISTRO)
    else:
        no_alcanza.insert(
            0, "registro del turno (DD-08 existe; AGENTE_BD no está configurada)"
        )
    if historial_conectado:
        alcanza.append(ALMACEN_HISTORIAL)
    else:
        no_alcanza.insert(
            0, "historial de conversación (PM-B37 existe; AGENTE_BD no está configurada)"
        )
    return {"alcanza": alcanza, "no_alcanza": no_alcanza}

def suprimir(
    identificador_sujeto: str,
    adaptador_perfil,
    adaptador_registro=None,
    adaptador_historial=None,
) -> dict:

    recibo: dict[str, int | None] = {}
    if adaptador_perfil is not None:
        try:
            adaptador_perfil.suprimir_sujeto(identificador_sujeto)

            recibo[ALMACEN_PERFIL] = None
        except Exception:
            recibo[ALMACEN_PERFIL] = 0
    if adaptador_registro is not None:
        try:
            recibo[ALMACEN_REGISTRO] = adaptador_registro.suprimir_sujeto(identificador_sujeto)
        except Exception:
            recibo[ALMACEN_REGISTRO] = 0
    if adaptador_historial is not None:
        try:

            recibo[ALMACEN_HISTORIAL] = adaptador_historial.suprimir_sujeto(identificador_sujeto)
        except Exception:
            recibo[ALMACEN_HISTORIAL] = 0
    return recibo
