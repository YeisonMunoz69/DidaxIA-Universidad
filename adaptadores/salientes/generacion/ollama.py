from __future__ import annotations

import json
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


PROVEEDOR = "ollama"


_MODELO_POR_DEFECTO = "llama3.1"
_URL_POR_DEFECTO = "http://localhost:11434/api/chat"
_TIEMPO_POR_DEFECTO_S = 60.0


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

    def __init__(self, url: str, tiempo_maximo_s: float) -> None:
        self._url = url
        self._tiempo = tiempo_maximo_s

    def enviar(self, cuerpo: bytes) -> ResultadoHTTP:
        import urllib.error
        import urllib.request

        peticion = urllib.request.Request(
            self._url,
            data=cuerpo,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(peticion, timeout=self._tiempo) as r:
                return ResultadoHTTP(estado=r.status, cuerpo=r.read())
        except urllib.error.HTTPError as e:
            return ResultadoHTTP(estado=e.code, cuerpo=e.read())
        except TimeoutError:
            return ResultadoHTTP(estado=0, fallo="tiempo agotado al esperar al modelo local")
        except urllib.error.URLError as e:

            return ResultadoHTTP(
                estado=0,
                fallo=f"no se pudo contactar a Ollama en {self._url}: {e.reason}. "
                f"¿Está levantado (`ollama serve`)?",
            )

class AdaptadorOllama:

    def __init__(
        self,
        *,
        modelo: str = _MODELO_POR_DEFECTO,
        url: str = _URL_POR_DEFECTO,
        tiempo_maximo_s: float = _TIEMPO_POR_DEFECTO_S,
        transporte: TransporteHTTP | None = None,
        registrador_consumo: RegistradorConsumoIA | None = None,
    ) -> None:

        self._modelo = modelo
        self._registrador_consumo = registrador_consumo
        self._transporte: TransporteHTTP = transporte or _TransporteUrllib(
            url, tiempo_maximo_s
        )

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
                    local=True,
                    estado="fallida",
                )
            )
            raise
        uso = respuesta.metadatos.get("uso_proveedor") or {}
        medido = uso.get("prompt_eval_count") is not None and uso.get("eval_count") is not None
        self._anotar_consumo(
            RegistroConsumoIA(
                llamada=llamada,
                instante_utc=instante,
                proveedor=PROVEEDOR,
                modelo_solicitado=self._modelo,
                modelo_respondido=respuesta.modelo,
                local=True,
                estado="completada" if medido else "sin_medicion",
                entrada_total=uso.get("prompt_eval_count"),
                salida=uso.get("eval_count"),
                total=(
                    uso["prompt_eval_count"] + uso["eval_count"]
                    if medido
                    else None
                ),
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
                "no se pudo registrar el consumo local de IA; la llamada no se reintentará",
                RuntimeWarning,
                stacklevel=2,
            )

    def _generar_valida(self, peticion: PeticionDeGeneracion) -> RespuestaDeGeneracion:
        cuerpo = json.dumps(
            {
                "model": self._modelo,
                "messages": [{"role": "user", "content": peticion.instruccion}],
                "options": {
                    "temperature": peticion.temperatura,
                    "num_predict": peticion.maximo_de_unidades,
                },
                "stream": False,
            }
        ).encode("utf-8")

        resultado = self._transporte.enviar(cuerpo)

        if resultado.fallo:
            raise ErrorDeGeneracion(resultado.fallo)
        if resultado.estado != 200:
            raise ErrorDeGeneracion(
                f"Ollama respondió HTTP {resultado.estado}: {_detalle(resultado.cuerpo)}"
            )

        try:
            datos = json.loads(resultado.cuerpo)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ErrorDeGeneracion(f"respuesta malformada de Ollama: {e}") from e

        try:
            texto = datos["message"]["content"]
        except (KeyError, TypeError) as e:
            raise ErrorDeGeneracion(
                f"la respuesta de Ollama no trae el texto esperado: {e}"
            ) from e

        return RespuestaDeGeneracion(
            texto=texto or "",
            modelo=datos.get("model") or self._modelo,
            proveedor=PROVEEDOR,

            unidades_de_entrada=_entero_opcional(datos.get("prompt_eval_count")) or 0,
            unidades_de_salida=_entero_opcional(datos.get("eval_count")) or 0,
            metadatos={
                "done_reason": datos.get("done_reason", ""),
                "uso_proveedor": {
                    "prompt_eval_count": _entero_opcional(datos.get("prompt_eval_count")),
                    "eval_count": _entero_opcional(datos.get("eval_count")),
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

def _detalle(cuerpo: bytes) -> str:
    try:
        datos = json.loads(cuerpo)
        error = datos.get("error")
        if error:
            return str(error)[:200]
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
        pass
    return cuerpo.decode("utf-8", "replace")[:200]
