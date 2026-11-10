"""
ollama.py — Adaptador del puerto de generación contra un modelo local
==========================================================================

Segundo adaptador de `dominio.puertos.generacion` (S9). `ADR-005` §2 fija la
condición **C3**: *«debe existir alternativa local configurable, para
escenarios institucionales con restricción de envío de datos a servicios
externos»*. `deepseek.py` cerró `PM-B04` sin ella —quedó anotado como
pendiente en `1.Estado-Actual-Yeison.md`— y este adaptador es lo que la
cierra: el mismo puerto, contra [Ollama](https://ollama.com) en `localhost`,
sin que un solo byte de la conversación salga de la máquina.

Por qué demuestra **C6** mejor que el primer adaptador
-----------------------------------------------------------
`ADR-005` C6 dice que sustituir de proveedor es *«escribir un adaptador y
cambiar configuración, sin tocar el dominio»*. Con un solo adaptador esa
afirmación no se puede comprobar — podría ser cierta por casualidad. Con dos
—uno contra un servicio comercial con clave, otro contra un proceso local sin
ella— la propiedad se ejerce: ningún filtro, ningún puerto, ninguna línea de
`dominio/` cambia entre uno y otro. Es la misma consecuencia verificable que
`ADR-001` §6.2 exige.

Por qué no comparte el transporte de `deepseek.py`
--------------------------------------------------------
Se pudo importar `TransporteHTTP` y `ResultadoHTTP` desde `deepseek.py` en vez
de declarar los suyos. Se descarta: acoplaría dos adaptadores del mismo
puerto entre sí sin necesidad —cada uno ya depende únicamente del puerto, que
es la frontera que importa—, y tocar `deepseek.py` para extraer algo
compartido es un refactor que esta sesión no pidió. La duplicación aquí es de
quince líneas, no de política: **N1**, la traducción de errores y los cuatro
modos de fallo de C4 son los mismos, y volver a escribirlos dos veces es
barato comparado con acoplar dos adaptadores por conveniencia.

Lo que este adaptador hace y lo que no
--------------------------------------
**No requiere clave.** Es justamente la propiedad que C3 pide: el modelo
corre en el mismo servidor y no hay secreto que gestionar ni que pueda
filtrarse.

**Traduce los mismos modos de fallo que C4 exige**, adaptados a lo que un
proceso local puede fallar: que Ollama no esté levantado (conexión rehusada),
tiempo agotado, o una respuesta que no trae el campo esperado. No hay límite
de tasa que traducir —no hay tercero cobrando por petición—, así que esa rama
de `deepseek.py` no tiene equivalente aquí y no se inventa uno.

**No compone el prompt ni juzga la respuesta**, por el mismo motivo que
`deepseek.py`: eso es del filtro 7 y de los filtros 9 y 10, dos y tres pasos
más adelante en la cadena.
"""

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

#: Nombre con el que este adaptador se identifica en la traza (`RF-REG-04`).
PROVEEDOR = "ollama"

#: Valores por defecto, todos sobrescribibles por constructor. `localhost` no
#: es una preferencia: es la condición C3, que exige que nada salga de la
#: máquina.
_MODELO_POR_DEFECTO = "llama3.1"
_URL_POR_DEFECTO = "http://localhost:11434/api/chat"
_TIEMPO_POR_DEFECTO_S = 60.0


@dataclass(frozen=True)
class ResultadoHTTP:
    """Lo que un transporte devuelve, ya neutralizado. Ver `deepseek.py`."""

    estado: int
    cuerpo: bytes = b""
    fallo: str = ""


@runtime_checkable
class TransporteHTTP(Protocol):
    """Lo que el adaptador necesita de la capa de red, y nada más.

    Existe por la misma razón que en `deepseek.py`: probar los modos de fallo
    sin depender de que Ollama esté instalado en la máquina que ejecuta la
    suite.
    """

    def enviar(self, cuerpo: bytes) -> ResultadoHTTP:
        """POST del cuerpo JSON al servidor local. No lanza: reporta en el resultado."""
        ...


class _TransporteUrllib:
    """Transporte real sobre la biblioteca estándar. Sin dependencias nuevas."""

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
            # El caso más común aquí no es un proveedor caído en internet:
            # es que Ollama no está levantado en esta máquina. Se nombra así
            # porque es lo primero que alguien debe comprobar.
            return ResultadoHTTP(
                estado=0,
                fallo=f"no se pudo contactar a Ollama en {self._url}: {e.reason}. "
                f"¿Está levantado (`ollama serve`)?",
            )


class AdaptadorOllama:
    """Implementa `dominio.puertos.generacion.PuertoGeneracion` contra Ollama local."""

    def __init__(
        self,
        *,
        modelo: str = _MODELO_POR_DEFECTO,
        url: str = _URL_POR_DEFECTO,
        tiempo_maximo_s: float = _TIEMPO_POR_DEFECTO_S,
        transporte: TransporteHTTP | None = None,
        registrador_consumo: RegistradorConsumoIA | None = None,
    ) -> None:
        """A diferencia de `AdaptadorDeepSeek`, no hay clave que validar al
        construir: la condición C3 es precisamente que este adaptador **no
        dependa de un secreto**. Sin transporte inyectado se arma el de
        `urllib` contra `url`."""
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
        except Exception:  # noqa: BLE001 — no repite ni bloquea una llamada ya consumida
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

        # -- modos de fallo, cada uno explícito · ADR-005 C4 ------------------
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
            # Ollama cuenta en tokens de evaluación, no en «prompt/completion
            # tokens»: son los nombres que su API usa para lo mismo que
            # RF-REG-04 pide por componente.
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
