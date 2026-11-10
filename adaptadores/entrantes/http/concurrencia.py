"""
concurrencia.py — Un turno a la vez por conversación, y reintentos idempotentes
====================================================================================

🔴 **El defecto que este módulo cierra · paquete J.** `rutas/turno.py` lo
declaraba en un comentario y lo aceptaba:

    ⚠️ No lleva candado por sesión. Dos peticiones de la MISMA sesión en vuelo a
    la vez —justo el caso de un reintento sin esperar— pueden pisarse en
    `datos` (contadores, `historial_reciente`).

El razonamiento de entonces era que el coste es bajo —«una cuenta del arbitraje
de más»—. Con la fase 4 dejó de serlo: los contadores del problema gobiernan la
escala de `RF-GEN-05`, así que dos turnos que se pisan pueden **abrir el
desarrollo** de un ejercicio que el estudiante no ha intentado tres veces, o
perderle dos intentos que sí hizo. Y el estado ya no es un entero: es el
problema activo, sus expresiones vistas, sus episodios y su archivo. Dos
lecturas del mismo estado y dos escrituras encima dejan lo que escriba la
última.

Las dos piezas, y qué resuelve cada una
------------------------------------------
| Pieza | Qué impide |
|---|---|
| `CandadoPorConversacion` | que dos turnos de la **misma** conversación lean el mismo estado y se sobrescriban |
| `RegistroDeIdempotencia` | que un **reintento** del mismo turno lo cuente dos veces |

**No es un candado global**, y la distinción es el requisito: el candado es por
conversación, así que dos estudiantes —o dos pestañas con conversaciones
distintas— siguen atendiéndose en paralelo. Un candado de proceso convertiría
el servidor en secuencial y arruinaría `RNF-EFI-01`, que es justo lo que el
comentario original quería evitar cuando decidió no poner ninguno.

El contrato de idempotencia, explícito
-----------------------------------------
El cliente puede mandar `idempotencia` en el cuerpo (§3): una clave que
identifica **el turno**, no la petición. Con ella:

- **la misma clave y el mismo mensaje** devuelven la respuesta ya calculada,
  sin volver a atravesar la cadena ni volver a contar nada. Es lo que un
  reintento necesita: repetirlo no cuesta un intento más;
- **la misma clave con otro mensaje** se rechaza con `409`. No es un caso
  raro que convenga tolerar: significa que dos turnos distintos se están
  presentando como el mismo, y elegir uno en silencio dejaría al estudiante
  sin saber cuál se contó;
- **sin clave** todo funciona como antes. El campo es opcional y el cliente
  que no lo mande no pierde nada — sólo la protección.

Los dos almacenes son **de este proceso**, igual que las sesiones
(`aplicacion.py` lo declara: viven en memoria y un reinicio las borra). No es
una limitación nueva de este módulo: es la misma que ya gobierna el estado que
protege, y ponerlos en otro sitio sin mover las sesiones no protegería nada.

⚠️ El límite de esto, dicho entero · auditoría R2
----------------------------------------------------
**Lo que protege este módulo vale para UN proceso, y hoy hay exactamente uno.**
Comprobado en la revisión R2 sobre el despliegue vigente: `Dockerfile.backend`
arranca `uvicorn adaptadores.entrantes.http.aplicacion:app --host 0.0.0.0
--port 8000`, **sin `--workers`** —que por defecto es uno—, y ningún
`compose*.yaml` declara `replicas` ni `deploy`. Un proceso, un bucle de
eventos, un diccionario de candados: la serialización por conversación es real.

**El día que eso cambie, esta protección desaparece sin avisar.** Con varios
workers o varias réplicas, cada proceso tiene su propio diccionario y sus
propias sesiones: dos turnos de la misma conversación atendidos por procesos
distintos no se ven, el candado no serializa nada entre ellos y el registro de
idempotencia tampoco reconoce el reintento. Vuelve entero el defecto del
paquete J —contadores del problema pisados, y con ellos la escala de
`RF-GEN-05`—, sólo que sin la traza que lo hizo visible la primera vez.

Lo que haría falta entonces, y **no se implementa en R2** porque escalar no
está decidido: control transaccional sobre el estado de la conversación —que
exige que ese estado viva en PostgreSQL y no en memoria— o un candado
distribuido. Ninguna de las dos es un ajuste de este archivo: las sesiones
tendrían que mudarse primero, y eso es una decisión del equipo. Escalar el
servicio sin resolverlo antes es la forma silenciosa de reabrir el paquete J.


"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass

#: Cuántas respuestas se recuerdan para reintentos. Un reintento llega en
#: segundos, así que no hace falta memoria larga; el tope existe para que un
#: cliente que mande una clave nueva por turno no haga crecer el proceso.
MAXIMO_RECORDADAS = 256


class CandadoPorConversacion:
    """Un `asyncio.Lock` por conversación **y por bucle de eventos**.

    El diccionario se toca sólo desde el bucle de eventos —`obtener()` no hace
    `await`—, así que no necesita su propio candado: entre dos `await` no hay
    otro turno de nadie.

    ⚠️ **Por qué la clave incluye el bucle, y no es una precaución teórica.**
    Un `asyncio.Lock` reparte el turno despertando futuros, y un futuro
    pertenece al bucle donde se creó. Si un bucle toma el candado y otro lo
    espera, al soltarlo se intentaría despertar un futuro ajeno desde el hilo
    equivocado: el segundo bucle **no se entera nunca** y la petición se cuelga.

    En producción hay un solo bucle —`uvicorn`, un proceso, un `asyncio`—, así
    que la clave del bucle es siempre la misma y la serialización es la que se
    busca. En cualquier contexto con varios bucles, cada uno tiene su candado:
    se serializa menos, pero **no se cuelga nada**, que es la única forma
    aceptable de degradar aquí. Se descubrió montando la prueba de dos turnos
    concurrentes: `TestClient` abre un bucle por petición, y con un candado
    compartido la suite se quedaba parada.
    """

    def __init__(self) -> None:
        self._candados: dict[tuple[int, str], asyncio.Lock] = {}

    def obtener(self, conversacion: str) -> asyncio.Lock:
        clave = (self._bucle_actual(), conversacion)
        candado = self._candados.get(clave)
        if candado is None:
            candado = asyncio.Lock()
            self._candados[clave] = candado
        return candado

    @staticmethod
    def _bucle_actual() -> int:
        try:
            return id(asyncio.get_running_loop())
        except RuntimeError:
            # Fuera de un bucle no hay contención que arbitrar; se agrupa todo
            # bajo la misma clave en vez de fallar.
            return 0

    def olvidar(self, conversacion: str) -> None:
        """Retira los candados de una conversación terminada.

        No lo llama la ruta del turno: mientras la conversación viva, su
        candado tiene que ser el mismo objeto o dejaría de serializar nada.
        """
        for clave in [k for k in self._candados if k[1] == conversacion]:
            del self._candados[clave]


@dataclass(frozen=True)
class Recordada:
    """Una respuesta ya calculada, y de qué petición salió.

    `huella` es del **contenido del turno**, no de la petición HTTP entera: dos
    reintentos legítimos difieren en `momento` y en las cabeceras, y exigir que
    todo coincida haría que ningún reintento se reconociera como tal.
    """

    huella: str
    lineas: tuple[bytes, ...]


class RegistroDeIdempotencia:
    """Qué turno produjo qué, por `(conversación, clave)`.

    Acotado por `MAXIMO_RECORDADAS` en orden de llegada: lo más viejo se cae
    primero, que es lo correcto cuando lo que se protege son reintentos.
    """

    def __init__(self, maximo: int = MAXIMO_RECORDADAS) -> None:
        self._maximo = maximo
        self._recordadas: OrderedDict[tuple[str, str], Recordada] = OrderedDict()

    @staticmethod
    def huella_de(cuerpo: dict) -> str:
        """La huella del turno: lo que lo define, y nada más.

        `momento` queda fuera a propósito —cambia en cada reintento— y también
        cualquier campo que el cliente añada mañana sin que sea parte del
        turno. Se nombran los que son.
        """
        significativo = {
            "mensaje": cuerpo.get("mensaje") or "",
            "sesion": cuerpo.get("sesion") or "",
            "dos_niveles": cuerpo.get("dos_niveles"),
            "retomar_sesion": cuerpo.get("retomar_sesion") or "",
            "notacion": cuerpo.get("notacion") or "",
        }
        crudo = json.dumps(significativo, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(crudo.encode("utf-8")).hexdigest()

    def recordada(self, conversacion: str, clave: str) -> Recordada | None:
        return self._recordadas.get((conversacion, clave))

    def recordar(
        self, conversacion: str, clave: str, huella: str, lineas: tuple[bytes, ...]
    ) -> None:
        self._recordadas[(conversacion, clave)] = Recordada(huella=huella, lineas=lineas)
        self._recordadas.move_to_end((conversacion, clave))
        while len(self._recordadas) > self._maximo:
            self._recordadas.popitem(last=False)

    def olvidar_conversacion(self, conversacion: str) -> None:
        for llave in [k for k in self._recordadas if k[0] == conversacion]:
            del self._recordadas[llave]


def clave_de(cuerpo: dict) -> str:
    """La clave de idempotencia del cuerpo, si el cliente mandó una.

    Se recorta y se acota: es un identificador que viene de fuera, y uno de
    cien mil caracteres no es un identificador sino una forma de gastar
    memoria del servidor.
    """
    clave = str(cuerpo.get("idempotencia") or "").strip()
    return clave[:128]
