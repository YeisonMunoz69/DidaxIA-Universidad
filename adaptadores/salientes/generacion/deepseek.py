"""
deepseek.py — Adaptador del puerto de generación contra DeepSeek
================================================================

Primer adaptador real del puerto `dominio.puertos.generacion` (S9, tercero de
los siete puertos de `ADR-001` §6.2). El proveedor concreto lo dejó abierto
`ADR-005`, que se cerró *por criterio de ingeniería* y fija en su §6 los cuatro
criterios de elección —soporte del español, región declarable, costo acotable,
alternativa local—. DeepSeek es uno de los tres adaptadores que el prototipo ya
traía (`06-Guia-de-Reutilizacion.md` §3.1: `deepseek`, `gemini`, `ollama`, ♻️),
y escribir uno de ellos es lo que hace cierta la propiedad verificable de
`ADR-001` §6.2 y la condición **C6** de `ADR-005`: *sustituir de proveedor es
escribir un adaptador y cambiar configuración, sin tocar el dominio*.

Por qué en `urllib` y no en el SDK del proveedor
------------------------------------------------
La API de DeepSeek es HTTPS con cuerpo JSON. Traerla con el SDK de un proveedor
—`openai`, que DeepSeek documenta por compatibilidad— añadiría una dependencia
pesada y, peor, una que la regla **N1** prohíbe en el dominio: si mañana se
colara un import de esa biblioteca hacia dentro, la frontera de `ADR-001` §7.2 se
rompería en silencio. Aquí la petición se ve entera, igual que el SQL de
`indice_postgres.py` está a la vista: lo que se lee es lo que se envía.

Lo que este adaptador hace y lo que no
--------------------------------------
**Traduce los errores del proveedor a `ErrorDeGeneracion`.** El dominio nunca ve
una excepción de la red ni un código de estado de una API concreta; eso es
justo la dependencia que `ADR-001` §7.2 prohíbe. Los modos de fallo que
`ADR-005` **C4** exige tratar explícitamente —límite de tasa, tiempo agotado,
respuesta malformada— tienen cada uno su rama, y ninguno degrada en silencio.

**Rellena `modelo`, `proveedor` y `unidades_*`** porque `RF-REG-04` pide latencia
y procedencia desagregadas por componente: sin saber qué modelo respondió no se
puede atribuir un fallo.

**No reintenta.** El puerto lo dice y aquí se respeta: un reintento cambia la
latencia que `RNF-EFI-01` presupuesta, y esconderlo dentro de esta llamada lo
volvería invisible. Es política del orquestador, con su traza. Un 429 se traduce
y se propaga; quién reintenta y cuándo se decide fuera.

**No compone el prompt ni juzga la respuesta.** El texto lo construye el filtro
7; la respuesta llega marcada `sin_verificar` y la verificación es dos filtros
más adelante (`ADR-008`).
"""

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

#: Nombre con el que este adaptador se identifica en la traza (`RF-REG-04`). Es
#: el proveedor, no el modelo: el modelo concreto lo devuelve la respuesta y
#: puede cambiar sin cambiar de adaptador.
PROVEEDOR = "deepseek"

#: Valores por defecto. Todos se pueden sobrescribir por constructor —para las
#: pruebas y para el despliegue— o por variable de entorno.
#:
#: `PM-B42`, 2026-08-18 · `_MODELO_POR_DEFECTO` es un **respaldo declarado**, no
#: el valor fijo. Antes lo era, y cambiar de modelo exigía editar Python y
#: reconstruir la imagen. Ahora manda `AGENTE_LLM_MODELO` del entorno.
_MODELO_POR_DEFECTO = "deepseek-chat"
#: De dónde sale el modelo. Ver `env-ejemplo.txt`, que trae el valor acordado.
_VARIABLE_MODELO = "AGENTE_LLM_MODELO"
_URL_POR_DEFECTO = "https://api.deepseek.com/chat/completions"
_TIEMPO_POR_DEFECTO_S = 60.0
_VARIABLE_TIEMPO = "AGENTE_LLM_TIEMPO_MAXIMO_S"

#: La clave se lee del entorno y **nunca de un archivo del repositorio**: un
#: secreto versionado sobrevive en todos los clones aunque se borre del árbol,
#: que es el mismo argumento por el que `test_indice_postgres.py` compone la
#: contraseña de la base desde el entorno.
_VARIABLE_CLAVE = "DEEPSEEK_API_KEY"


@dataclass(frozen=True)
class ResultadoHTTP:
    """Lo que un transporte devuelve, ya neutralizado.

    `estado` es el código HTTP; **0 significa que no hubo respuesta** —tiempo
    agotado o fallo de conexión— y entonces `fallo` dice cuál. Que el transporte
    traduzca aquí la excepción de su biblioteca, y no el adaptador, es la regla
    **N2**: el tipo del borde —una `URLError`, una `TimeoutError`— no cruza hacia
    el adaptador ni, menos aún, hacia el dominio.
    """

    estado: int
    cuerpo: bytes = b""
    fallo: str = ""


@runtime_checkable
class TransporteHTTP(Protocol):
    """Lo que el adaptador necesita de la capa de red, y nada más.

    Existe para que el adaptador se pueda probar sin red: sus pruebas de unidad
    inyectan un transporte que devuelve el `ResultadoHTTP` que la prueba fije, y
    así los modos de fallo de `ADR-005` C4 se comprueban sin depender de que el
    proveedor tenga a bien fallar. Es la misma separación por la que
    `IndicePostgres` recibe un `Codificador` en vez de traérselo dentro.
    """

    def enviar(self, cuerpo: bytes) -> ResultadoHTTP:
        """POST del cuerpo JSON al proveedor. No lanza: reporta en el resultado."""
        ...


class _TransporteUrllib:
    """Transporte real sobre la biblioteca estándar. Sin dependencias nuevas."""

    def __init__(self, url: str, clave: str, tiempo_maximo_s: float) -> None:
        self._url = url
        self._clave = clave
        self._tiempo = tiempo_maximo_s

    def enviar(self, cuerpo: bytes) -> ResultadoHTTP:
        # Se importa aquí y no arriba por la misma razón que `indice_postgres`
        # importa `psycopg` dentro del método: el módulo se puede leer e
        # inspeccionar sin nada instalado, aunque en este caso `urllib` es de la
        # biblioteca estándar y siempre está.
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
            # El proveedor respondió con un estado de error (429, 401, 400, 5xx).
            # Su cuerpo suele traer el motivo y se conserva para la traza; la
            # interpretación —qué estado es cuál— la hace el adaptador.
            return ResultadoHTTP(estado=e.code, cuerpo=e.read())
        except TimeoutError:
            return ResultadoHTTP(estado=0, fallo="tiempo agotado al esperar al proveedor")
        except urllib.error.URLError as e:
            return ResultadoHTTP(
                estado=0, fallo=f"no se pudo contactar al proveedor: {e.reason}"
            )


class AdaptadorDeepSeek:
    """Implementa `dominio.puertos.generacion.PuertoGeneracion` contra DeepSeek."""

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
        """Construye el adaptador.

        `transporte` se inyecta en las pruebas; en producción se deja en `None`
        y se arma el de `urllib` con la clave del entorno. Si no hay clave y no
        hay transporte inyectado, se falla **al construir** y no al primer turno:
        un secreto ausente es un error de configuración del despliegue, no algo
        que deba descubrirse a mitad de una sesión de un estudiante.
        """
        # `PM-B42` · el del constructor manda —lo usan las pruebas—, luego el
        # entorno, y el respaldo solo si no hay ninguno de los dos.
        #
        # ⚠️ Lo que el proveedor RESPONDE sigue mandando para el registro de
        # `RF-REG-04`: ver `modelo=datos.get("model") or self._modelo` más
        # abajo. Un alias puede resolverse a una versión concreta, y para la
        # traza vale la que contestó, no la que se pidió.
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
            from adaptadores.salientes.generacion.transporte_acotado import (  # noqa: PLC0415
                TransporteAcotado,
            )

            self._transporte = TransporteAcotado(url, clave, float(limite_total))
        else:
            self._transporte = _TransporteUrllib(url, clave, tiempo_maximo_s)

    def generar(self, peticion: PeticionDeGeneracion) -> RespuestaDeGeneracion:
        # El puerto define `validar`; usarlo aquí evita gastar una llamada de red
        # —y presupuesto de costo, `ADR-005` C5— en una petición que el propio
        # dominio declara inadmisible. El fallo llega como error del dominio, no
        # como un 400 propio de la API del proveedor.
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
        except Exception:  # noqa: BLE001 — una caída contable no repite ni bloquea la llamada
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
                # V4 habilita el razonamiento interno por defecto. En este
                # producto el filtro 7 ya entrega la decisión pedagógica y el
                # contrato JSON exacto: gastar el techo en razonamiento deja
                # `content` vacío (medido con 4096/4096 tokens en producción
                # local). Se pide por tanto el modo no pensante, que es además
                # el modo compatible con temperatura reproducible.
                "thinking": {"type": "disabled"},
                # `ADR-014` §5.3: «cuando el proveedor ofrece salida estructurada
                # nativa, se usa». DeepSeek la ofrece, y usarla es lo que evita
                # que el objeto llegue envuelto en un cercado de código o con una
                # frase de cortesía delante. Sigue habiendo respaldo por si el
                # proveedor lo ignora — ver `_estructura()`.
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")

        resultado = self._transporte.enviar(cuerpo)

        # -- modos de fallo, cada uno explícito · ADR-005 C4 ------------------
        # «Nunca degradación silenciosa»: todo lo que no sea una respuesta 200
        # bien formada se convierte en ErrorDeGeneracion con su causa nombrada.
        if resultado.fallo:
            # Tiempo agotado o fallo de conexión. El transporte ya lo redactó.
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
            # `ADR-014` §5.3 · la diferencia entre pedirlo nativo y extraerlo del
            # texto queda contenida AQUÍ, y el filtro 9 recibe lo mismo en ambos
            # casos. `None` cuando no se pudo: C3 dice qué hacer entonces y lo
            # hace el filtro, no este adaptador.
            estructura=_estructura(texto or ""),
            # `model` de la respuesta y no el pedido: el proveedor puede resolver
            # un alias a una versión concreta, y para la traza vale la que respondió.
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
    """El objeto de `ADR-014` que venga en el texto, o `None`.

    Con `response_format` nativo el texto **es** el objeto y basta el primer
    intento. El respaldo existe porque un proveedor puede ignorar el ajuste, y
    porque `ADR-005` pide poder cambiar de proveedor sin tocar el dominio: el
    día que se use uno sin salida estructurada, esto es lo único que cambia.

    Se recorta un cercado de código si lo trae —```json … ```— y, si no, se
    busca el primer objeto equilibrado del texto. Nada de esto interpreta el
    contenido: **validar es del dominio**, y lo hace `RespuestaGenerada.
    desde_objeto()`. Aquí solo se pasa de texto a diccionario.

    Devolver `None` no es tragarse un fallo: es informar de que no hubo
    estructura, y `ADR-014` C3 obliga a que quien lo reciba descienda al nivel 1
    dejando traza. Lanzar aquí perdería la generación entera, incluido el texto
    que sí sirve para poder mirar qué respondió el modelo.
    """
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
    """El primer `{...}` equilibrado, ignorando las llaves dentro de cadenas.

    Contar llaves a secas fallaría con la referencia `{{a1}}` de la propia
    narración, que es justo lo que este contrato hace que aparezca en todas las
    respuestas.
    """
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
    """Un motivo corto extraído del cuerpo de error, para la traza.

    La forma de error de DeepSeek —compartida con las API compatibles— es
    `{"error": {"message": ...}}`. Si no se puede interpretar, se devuelve el
    cuerpo crudo recortado: más vale un texto feo que un mensaje vacío que mande
    a adivinar.
    """
    try:
        datos = json.loads(cuerpo)
        mensaje = (datos.get("error") or {}).get("message")
        if mensaje:
            return str(mensaje)[:200]
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
        pass
    return cuerpo.decode("utf-8", "replace")[:200]


def _finish_reason(datos: dict) -> str:
    """Por qué se detuvo la generación. `stop` normal; `length` techo alcanzado."""
    try:
        return datos["choices"][0].get("finish_reason", "") or ""
    except (KeyError, IndexError, TypeError):
        return ""
