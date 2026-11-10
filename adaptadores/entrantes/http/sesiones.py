from __future__ import annotations

import secrets
import time
from datetime import UTC, datetime

from adaptadores.entrantes.http import aviso_legal
from dominio.modelo.supresion import reautenticacion_reciente


COOKIE = "agente_sesion"


TTL_SESION_SEGUNDOS = 7 * 24 * 60 * 60


_SONDEO_NUNCA_OFRECIDO = 99


class SesionSinIdentidad(RuntimeError):
    pass

def _estado_de_conversacion() -> dict:
    return {
        "conversacion": secrets.token_urlsafe(16),

        "intentos": 0,
        "insistencias": 0,
        "peticion_confirmada": False,

        "turnos_desde_el_sondeo": _SONDEO_NUNCA_OFRECIDO,
        "nodos_sondeados": [],

        "expresion_previa": "",

        "historial_reciente": [],
        "contexto_factual": {"total": 0, "turnos": []},
        "sesion_contexto_factual": "",

        "retomando_activo": "",
    }

class Sesiones:

    def __init__(self) -> None:
        self._por_token: dict[str, dict] = {}

    def abrir(
        self, rol: str = "estudiante", *,
        identificador_estable: str, correo: str, nombre: str = "",
    ) -> dict:

        if not (identificador_estable or "").strip() or not (correo or "").strip():
            raise SesionSinIdentidad(
                "una sesión exige sujeto estable y correo verificados por Google (EQ-020)"
            )
        token = secrets.token_urlsafe(32)
        datos = {

            "token": token,

            "sesion_autenticada": secrets.token_urlsafe(12),
            "rol": rol,

            "identificador_estable": identificador_estable,
            "correo": correo,
            "nombre": nombre,

            "consentimiento": "pendiente",

            "edad": aviso_legal.edad_por_defecto(),

            "reautenticada_en": None,

            "creada_en": time.time(),
            **_estado_de_conversacion(),
        }
        self._por_token[token] = datos
        return datos

    def nueva_conversacion(self, datos: dict) -> dict:
        for campo in (
            "ejercicio_activo", "ejercicio_en_pausa", "funciones_declaradas",
            "funcion_vigente", "estado_pedagogico", "estrategia_previa",
            "estado_operativo", "sondeos_ofrecidos", "sondeos_contestados",
            "item_pendiente", "sin_adaptacion",
        ):
            datos.pop(campo, None)
        datos.update(_estado_de_conversacion())
        return datos

    def publico(self, datos: dict) -> dict:
        publico = {
            k: datos[k] for k in ("rol", "consentimiento", "edad", "correo", "nombre")
        }
        publico["sesion"] = datos["conversacion"]
        publico["conversacion"] = datos["conversacion"]
        publico["puede_participar"] = aviso_legal.puede_participar(datos)

        publico["expira_en_segundos"] = self.expira_en(datos)
        return publico

    def expira_en(self, datos: dict) -> int:
        restante = TTL_SESION_SEGUNDOS - (time.time() - datos["creada_en"])
        return max(0, int(restante))

    def leer(self, token: str | None) -> dict | None:
        datos = self._por_token.get(token or "")
        if datos is None:
            return None
        if time.time() - datos["creada_en"] > TTL_SESION_SEGUNDOS:

            self._por_token.pop(token, None)
            return None
        return datos

    def cerrar(self, token: str | None) -> None:
        self._por_token.pop(token or "", None)

    def marcar_reautenticacion(self, datos: dict, *, momento: datetime | None = None) -> datetime:
        acreditada = momento or datetime.now(UTC)
        datos["reautenticada_en"] = acreditada
        return acreditada

    def prueba_de_reautenticacion(self, datos: dict) -> datetime | None:
        return datos.get("reautenticada_en")

    def reautenticacion_vigente(self, datos: dict) -> bool:
        acreditada = self.prueba_de_reautenticacion(datos)
        if acreditada is None:
            return False
        return reautenticacion_reciente(acreditada, datetime.now(UTC))

def sujeto_de(datos: dict) -> str:
    sujeto = (datos.get("identificador_estable") or "").strip()
    if not sujeto:
        raise SesionSinIdentidad(
            "esta sesión no tiene identidad verificada: no hay sujeto del que colgar datos"
        )
    return sujeto
