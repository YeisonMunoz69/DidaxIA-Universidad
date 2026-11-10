"""
generacion.py — Puerto de generación de lenguaje (S9)
======================================================

Tercero de los siete puertos de `ADR-001` §6.2. Sus adaptadores previstos son
los proveedores comerciales y el modelo local, y `RI-01` y `RI-03` exigen que
cambiar de uno a otro **sea escribir un adaptador y cambiar configuración**.

Por qué el dominio no sabe qué modelo hay detrás
------------------------------------------------
`ADR-001` descartó el monolito por capas porque *«el dominio depende de la
infraestructura; falla la sustituibilidad del proveedor»*. Este puerto es donde
esa sustituibilidad se hace cierta o se pierde: si aquí asomara un nombre de
proveedor, un formato de mensaje o un parámetro propio de una API, el dominio
quedaría atado a ella.

Lo que el puerto NO decide, y es lo que lo mantiene estrecho
-----------------------------------------------------------
**No decide qué se pide.** El texto del prompt lo construye el filtro 7 a partir
de la estrategia que el arbitraje eligió. Aquí solo se envía.

**No decide si la respuesta vale.** `ADR-001` §6.3 pone la verificación
simbólica en el filtro 9 y el juez en el 10, los dos **después** de este puerto.
El principio rector de `ERS-01` §6.4 es explícito: *«ninguna decisión crítica se
delega al LLM generador principal»*.

**No reintenta.** Un reintento cambia la latencia del turno y `RNF-EFI-01` la
presupuesta por componente; decidirlo aquí lo escondería dentro de una llamada
que parece única. Es política del adaptador o del orquestador, con su traza.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class ErrorDeGeneracion(Exception):
    """El proveedor no devolvió una respuesta utilizable.

    Existe para que el dominio pueda distinguir *«el modelo falló»* de
    *«el modelo respondió algo malo»*, que se tratan distinto: lo primero admite
    respaldo a otro proveedor, lo segundo lo resuelve la verificación.

    El adaptador traduce a esta excepción lo que su biblioteca lance. Que el
    dominio vea un error de red de un proveedor concreto sería exactamente la
    dependencia que `ADR-001` §7.2 prohíbe.
    """


@dataclass(frozen=True)
class PeticionDeGeneracion:
    """Lo que se le pide al modelo en un turno.

    - `instruccion` — el prompt ya construido. El puerto no lo compone.
    - `temperatura` — 0.0 por defecto, y no es una preferencia de estilo: `T4`
      resolvió no ajustar el generador en la v1 y apoyarse en aprendizaje en
      contexto, de modo que la reproducibilidad del turno es lo que permite
      analizar después por qué respondió lo que respondió. `RF-ORQ-14` pide
      poder reconstruir cualquier turno.
    - `maximo_de_unidades` — techo de longitud. Lo impone el presupuesto de
      latencia de `RNF-EFI-01`, no la estética de la respuesta.
    """

    instruccion: str
    temperatura: float = 0.0
    maximo_de_unidades: int = 800
    mensajes: tuple[dict, ...] = ()

    def validar(self) -> list[str]:
        """Errores de la petición. Lista vacía significa que es admisible."""
        fallos = []
        if any(m.get("role") not in ("system", "user", "assistant") or not isinstance(m.get("content"), str) for m in self.mensajes):
            fallos.append("mensajes de generación inválidos")
        if not self.instruccion.strip():
            fallos.append("instrucción vacía: no hay nada que generar")
        if not 0.0 <= self.temperatura <= 2.0:
            fallos.append(f"temperatura fuera de rango: {self.temperatura}")
        if self.maximo_de_unidades < 1:
            fallos.append(
                f"máximo de unidades inválido: {self.maximo_de_unidades}"
            )
        return fallos


@dataclass(frozen=True)
class RespuestaDeGeneracion:
    """Lo que el modelo devolvió, **sin juzgar todavía**.

    `sin_verificar` no es una advertencia decorativa: es el estado real de este
    texto en este punto de la cadena. `ADR-008` exige que ninguna afirmación
    matemática se emita sin pasar por el motor simbólico, y eso ocurre dos
    filtros más adelante. Nombrarlo así evita que alguien tome esta respuesta
    por la respuesta del sistema.

    - `modelo` y `proveedor` se conservan **para la traza**, no para decidir
      nada. `RF-REG-04` pide latencia y procedencia desagregadas por componente,
      y sin saber qué modelo respondió no se puede atribuir un fallo.
    - `unidades_*` alimentan el mismo registro. Van como enteros y no como coste
      porque el precio cambia y el recuento no.
    - `estructura` es el objeto de `ADR-014`, si el adaptador consiguió uno.
      **Añadido el 2026-08-10 con `PM-B17`**, y es lo que faltaba para que la
      cadena sirviera de algo: sin él, el filtro 9 no recibía nada que verificar
      y **todo turno terminaba en degradación** aunque el modelo hubiera
      respondido bien. Medido contra DeepSeek antes de escribirlo.

      Es un diccionario liso con la forma que `dominio.modelo.respuesta`
      declara —`narracion`, `afirmaciones`, `nivel`—, **nunca la forma de un
      proveedor**: `ADR-014` §5.3 pone en el adaptador la diferencia entre
      pedirlo como salida estructurada nativa o extraerlo del texto, «y el
      filtro 9 recibe lo mismo en ambos casos». Aquí no asoma ningún nombre de
      API, que es lo que `ADR-001` §7.2 prohíbe.

      **`None` es un valor legítimo y frecuente**: significa que el adaptador no
      obtuvo estructura. `ADR-014` C3 dice qué hacer entonces —registrar y
      descender al nivel 1—, y quien lo hace es el filtro 9, no este puerto.
    """

    texto: str
    modelo: str = ""
    proveedor: str = ""
    unidades_de_entrada: int = 0
    unidades_de_salida: int = 0
    metadatos: dict = field(default_factory=dict)
    estructura: dict | None = None

    @property
    def sin_verificar(self) -> bool:
        """Siempre cierto en este punto de la cadena. Está para que se lea.

        Devuelve una constante a propósito. Si algún día dejara de serlo, sería
        porque alguien movió la verificación antes del generador, y entonces
        esta propiedad tendría que cambiar **y su prueba fallaría**, que es
        justo lo que se quiere que ocurra.
        """
        return True

    @property
    def vacia(self) -> bool:
        return not self.texto.strip()


@runtime_checkable
class PuertoGeneracion(Protocol):
    """Contrato de generación. El proveedor concreto es asunto del adaptador."""

    def generar(self, peticion: PeticionDeGeneracion) -> RespuestaDeGeneracion:
        """Genera una respuesta, o lanza `ErrorDeGeneracion` si no puede."""
        ...
