"""
inventario_de_datos.py — Qué habría que borrar, sin borrar nada (hito B3)
==========================================================================

`EQ-022` y la deuda de la Fase 2 · sesión 1 apuntan al mismo hueco:

    «Consentimiento, cola de revisión, solicitud docente y clases creadas no
    forman una cascada completa por titular. Borrar una conversación elimina el
    historial, pero no llama al borrado hermano del registro forense.»

Este puerto responde **qué alcanzaría** una supresión, por titular, en cada
autoridad donde ese titular tiene datos. Es un inventario, no una ejecución.

Por qué el inventario va antes que la cascada
---------------------------------------------------------
Porque la cascada no se puede escribir sin saber qué toca, y porque el cierre
V-B necesita exactamente esta lista para decidir. Sin ella, la conversación sería
«borramos lo del usuario» y nadie podría comprobar si eso incluye el registro
forense en volumen, la matrícula de una clase o la cola de supervisión.

⚠️ Qué NO puede devolver
--------------------------------
**Ni un dato personal.** Devuelve nombres de tabla, conteos y si la fila es texto
libre —lo que V-B tiene que distinguir— y nunca correos, nombres ni el contenido
de una conversación. Un inventario que imprimiera lo que va a borrar sería una
exportación disfrazada, y se le enseña a quien depura.

**Ni una promesa de que se pueda anonimizar.** `Autoridad.texto_libre` marca lo
que contiene texto escrito por personas: cambiar su sujeto técnico lo
**seudonimiza**, no lo anonimiza, porque el texto puede llevar dentro nombres y
correos. La distinción es la que V-B tiene que resolver y por eso el inventario
la señala en vez de esconderla.


"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class Autoridad:
    """Un sitio donde un titular tiene datos, y qué clase de datos son.

    `nombre` es la tabla, el volumen o el servicio. `filas` es cuántas le
    corresponden a **ese** titular. `texto_libre` marca si contiene texto escrito
    por personas, que es lo que hace la diferencia entre seudonimizar y anonimizar.

    `alcanzable` dice si la supresión puede llegar hasta ahí hoy. `False` no es un
    fallo: es la deuda que la Fase 2 dejó anotada, y declararla es el punto de
    este inventario.
    """

    nombre: str
    filas: int
    texto_libre: bool = False
    alcanzable: bool = True
    nota: str = ""


@dataclass(frozen=True, slots=True)
class InventarioPorTitular:
    """Lo que una supresión alcanzaría para un titular. Sin un dato suyo dentro.

    `sujeto_google` es la clave técnica y sí viaja: sin ella el inventario no se
    puede atribuir, y es un identificador opaco, no un dato personal legible.
    """

    sujeto_google: str
    autoridades: tuple[Autoridad, ...] = field(default_factory=tuple)

    @property
    def filas_totales(self) -> int:
        return sum(a.filas for a in self.autoridades)

    @property
    def con_texto_libre(self) -> tuple[Autoridad, ...]:
        """Lo que V-B tiene que mirar una por una.

        Cambiar el sujeto de estas filas las seudonimiza; declararlas anónimas
        exigiría saber que su texto no contiene identificadores, y eso no se sabe.
        """
        return tuple(a for a in self.autoridades if a.texto_libre and a.filas)

    @property
    def fuera_de_alcance(self) -> tuple[Autoridad, ...]:
        """Lo que una cascada de hoy **no** alcanzaría, con filas."""
        return tuple(a for a in self.autoridades if not a.alcanzable and a.filas)

    def como_json(self) -> dict:
        """La forma que el panel de V-B consumirá. Conteos, nunca contenidos."""
        return {
            "sujeto_google": self.sujeto_google,
            "filas_totales": self.filas_totales,
            "autoridades": [
                {
                    "nombre": a.nombre,
                    "filas": a.filas,
                    "texto_libre": a.texto_libre,
                    "alcanzable": a.alcanzable,
                    "nota": a.nota,
                }
                for a in self.autoridades
            ],
        }


@runtime_checkable
class PuertoInventarioDeDatos(Protocol):
    """La única operación: contar, sin tocar."""

    def inventariar(self, sujeto_google: str) -> InventarioPorTitular:
        """Qué alcanzaría una supresión de ese titular.

        **Sólo lee.** No abre transacción de escritura, no bloquea filas y no
        deja rastro salvo el que la auditoría registre por su cuenta.

        Devuelve un inventario con **todas** las autoridades, incluidas las que
        tienen cero filas: saber que una tabla no le corresponde es un dato, y
        omitirla haría imposible distinguir «no tiene» de «no se miró».
        """
        ...
