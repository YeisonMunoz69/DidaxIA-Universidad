from __future__ import annotations

import json
import os
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable
from uuid import uuid4

from dominio.modelo.consumo_ia import RegistradorConsumoIA, RegistroConsumoIA
from dominio.puertos.generacion import (
    ErrorDeGeneracion,
    PeticionDeGeneracion,
    RespuestaDeGeneracion,
)


PROVEEDOR = "deepseek"


_MODELO_POR_DEFECTO = "deepseek-chat"

_VARIABLE_MODELO = "AGENTE_LLM_MODELO"
_URL_POR_DEFECTO = "https://api.deepseek.com/chat/completions"
_TIEMPO_POR_DEFECTO_S = 60.0
_VARIABLE_TIEMPO = "AGENTE_LLM_TIEMPO_MAXIMO_S"


_VARIABLE_CLAVE = "DEEPSEEK_API_KEY"


@dataclass(frozen=True)
class ResultadoHTTP:

    estado: int
    cuerpo: bytes = b""
    fallo: str = ""

@runtime_checkable
class TransporteHTTP(Protocol):

    def enviar(self, cuerpo: bytes) -> ResultadoHTTP:
        ...

class _TransporteUrllib:

    def __init__(self, url: str, clave: str, tiempo_maximo_s: float) -> None:
        self._url = url
        self._clave = clave
        self._tiempo = tiempo_maximo_s

    def enviar(self, cuerpo: bytes) -> ResultadoHTTP:
        import urllib.error
        import urllib.request

        peticion = urllib.request.Request(
            self._url,
            data=cuerpo,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._clave}",
            },
        )
        try:
            from adaptadores.salientes.generacion.red import abrir_con_reintento_dns

            with abrir_con_reintento_dns(peticion, self._tiempo) as r:
                return ResultadoHTTP(estado=r.status, cuerpo=r.read())
        except urllib.error.HTTPError as e:

            return ResultadoHTTP(estado=e.code, cuerpo=e.read())
        except TimeoutError:
            return ResultadoHTTP(estado=0, fallo="tiempo agotado al esperar al proveedor")
        except urllib.error.URLError as e:
            return ResultadoHTTP(
                estado=0, fallo=f"no se pudo contactar al proveedor: {e.reason}"
            )

class AdaptadorDeepSeek:

    def __init__(
        self,
        clave: str | None = None,
        *,
        modelo: str = "",
        url: str = _URL_POR_DEFECTO,
        tiempo_maximo_s: float | None = None,
        transporte: TransporteHTTP | None = None,
        registrador_consumo: RegistradorConsumoIA | None = None,
    ) -> None:

        self._modelo = modelo or os.environ.get(_VARIABLE_MODELO, "") or _MODELO_POR_DEFECTO
        self._registrador_consumo = registrador_consumo
        if transporte is not None:
            self._transporte: TransporteHTTP = transporte
            return
        clave = clave if clave is not None else os.environ.get(_VARIABLE_CLAVE, "")
        if not clave:
            raise ErrorDeGeneracion(
                f"falta la clave de API: defina {_VARIABLE_CLAVE} en el entorno. "
                f"La clave no se escribe en un archivo del repositorio."
            )
        if tiempo_maximo_s is None:
            crudo = os.environ.get(_VARIABLE_TIEMPO, "").strip()
            try:
                tiempo_maximo_s = float(crudo) if crudo else _TIEMPO_POR_DEFECTO_S
            except ValueError as exc:
                raise ErrorDeGeneracion(
                    f"{_VARIABLE_TIEMPO} debe ser un número positivo de segundos"
                ) from exc
        if tiempo_maximo_s <= 0:
            raise ErrorDeGeneracion(
                f"{_VARIABLE_TIEMPO} debe ser un número positivo de segundos"
            )
        limite_total = os.environ.get("AGENTE_LLM_LIMITE_TOTAL_S", "")
        if limite_total != "":
            from adaptadores.salientes.generacion.transporte_acotado import (
                TransporteAcotado,
            )

            self._transporte = TransporteAcotado(url, clave, float(limite_total))
        else:
            self._transporte = _TransporteUrllib(url, clave, tiempo_maximo_s)

    def generar(self, peticion: PeticionDeGeneracion) -> RespuestaDeGeneracion:
        fallos = peticion.validar()
        if fallos:
            raise ErrorDeGeneracion("petición inadmisible: " + "; ".join(fallos))

        llamada = uuid4()
        instante = datetime.now(UTC)
        try:
            respuesta = self._generar_valida(peticion)
        except ErrorDeGeneracion:
            self._anotar_consumo(
                RegistroConsumoIA(
                    llamada=llamada,
                    instante_utc=instante,
                    proveedor=PROVEEDOR,
                    modelo_solicitado=self._modelo,
                    estado="fallida",
                )
            )
            raise
        uso = respuesta.metadatos.get("uso_proveedor") or {}
        medido = uso.get("prompt_tokens") is not None and uso.get("completion_tokens") is not None
        self._anotar_consumo(
            RegistroConsumoIA(
                llamada=llamada,
                instante_utc=instante,
                proveedor=PROVEEDOR,
                modelo_solicitado=self._modelo,
                modelo_respondido=respuesta.modelo,
                respuesta_proveedor=str(respuesta.metadatos.get("id") or ""),
                estado="completada" if medido else "sin_medicion",
                entrada_cache_hit=uso.get("prompt_cache_hit_tokens"),
                entrada_cache_miss=uso.get("prompt_cache_miss_tokens"),
                entrada_total=uso.get("prompt_tokens"),
                salida=uso.get("completion_tokens"),
                total=uso.get("total_tokens"),
            )
        )
        return respuesta

    def _anotar_consumo(self, registro: RegistroConsumoIA) -> None:
        if self._registrador_consumo is None:
            return
        try:
            self._registrador_consumo.registrar(registro)
        except Exception:
            warnings.warn(
                "no se pudo registrar el consumo de IA; la respuesta no se reintentará",
                RuntimeWarning,
                stacklevel=2,
            )

    def _generar_valida(self, peticion: PeticionDeGeneracion) -> RespuestaDeGeneracion:
        cuerpo = json.dumps(
            {
                "model": self._modelo,
                "messages": list(peticion.mensajes) if peticion.mensajes else [{"role": "user", "content": peticion.instruccion}],
                "temperature": peticion.temperatura,
                "max_tokens": peticion.maximo_de_unidades,
                "stream": False,

                "thinking": {"type": "disabled"},

                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")

        resultado = self._transporte.enviar(cuerpo)

        if resultado.fallo:

            raise ErrorDeGeneracion(resultado.fallo)
        if resultado.estado == 429:
            raise ErrorDeGeneracion(
                "límite de tasa del proveedor (HTTP 429). Reintentar es política "
                "del orquestador, no de este puerto: un reintento aquí escondería "
                "latencia que RNF-EFI-01 presupuesta."
            )
        if resultado.estado != 200:
            raise ErrorDeGeneracion(
                f"el proveedor respondió HTTP {resultado.estado}: "
                f"{_detalle(resultado.cuerpo)}"
            )

        try:
            datos = json.loads(resultado.cuerpo)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ErrorDeGeneracion(
                f"respuesta malformada del proveedor: {e}"
            ) from e

        try:
            texto = datos["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ErrorDeGeneracion(
                f"la respuesta del proveedor no trae el texto esperado: {e}"
            ) from e

        razon_de_parada = _finish_reason(datos)
        if not (texto or "").strip() and razon_de_parada == "length":
            raise ErrorDeGeneracion(
                "el proveedor agotó el máximo de salida antes de entregar el JSON"
            )

        uso_crudo = datos.get("usage")
        uso = uso_crudo if isinstance(uso_crudo, dict) else {}
        return RespuestaDeGeneracion(
            texto=texto or "",

            estructura=_estructura(texto or ""),

            modelo=datos.get("model") or self._modelo,
            proveedor=PROVEEDOR,
            unidades_de_entrada=_entero_opcional(uso.get("prompt_tokens")) or 0,
            unidades_de_salida=_entero_opcional(uso.get("completion_tokens")) or 0,
            metadatos={
                "finish_reason": razon_de_parada,
                "id": datos.get("id", ""),
                "uso_proveedor": {
                    "prompt_tokens": _entero_opcional(uso.get("prompt_tokens")),
                    "prompt_cache_hit_tokens": _entero_opcional(
                        uso.get("prompt_cache_hit_tokens")
                    ),
                    "prompt_cache_miss_tokens": _entero_opcional(
                        uso.get("prompt_cache_miss_tokens")
                    ),
                    "completion_tokens": _entero_opcional(uso.get("completion_tokens")),
                    "total_tokens": _entero_opcional(uso.get("total_tokens")),
                },
            },
        )

def _entero_opcional(valor: object) -> int | None:
    if valor is None or isinstance(valor, bool):
        return None
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return None
    return numero if numero >= 0 else None

def _estructura(texto: str) -> dict | None:
    crudo = texto.strip()
    if not crudo:
        return None

    if crudo.startswith("```"):
        crudo = crudo.split("\n", 1)[-1] if "\n" in crudo else ""
        if crudo.rstrip().endswith("```"):
            crudo = crudo.rstrip()[:-3]
        crudo = crudo.strip()

    for candidato in (crudo, _primer_objeto(crudo)):
        if not candidato:
            continue
        try:
            datos = json.loads(candidato)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(datos, dict):
            return datos
    return None

def _primer_objeto(texto: str) -> str:
    inicio = texto.find("{")
    if inicio < 0:
        return ""
    profundidad, en_cadena, escapado = 0, False, False
    for i in range(inicio, len(texto)):
        c = texto[i]
        if escapado:
            escapado = False
            continue
        if c == "\\":
            escapado = True
        elif c == '"':
            en_cadena = not en_cadena
        elif not en_cadena:
            if c == "{":
                profundidad += 1
            elif c == "}":
                profundidad -= 1
                if profundidad == 0:
                    return texto[inicio : i + 1]
    return ""

def _detalle(cuerpo: bytes) -> str:
    try:
        datos = json.loads(cuerpo)
        mensaje = (datos.get("error") or {}).get("message")
        if mensaje:
            return str(mensaje)[:200]
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
        pass
    return cuerpo.decode("utf-8", "replace")[:200]

def _finish_reason(datos: dict) -> str:
    try:
        return datos["choices"][0].get("finish_reason", "") or ""
    except (KeyError, IndexError, TypeError):
        return ""
