"""
arbitraje.py — Filtro 6 · cuánto se revela y qué se hace en este turno
========================================================================

`ADR-001` §6.3 sitúa el filtro 6 —*«arbitraje de intervención»*— en la **ruta
caliente**, entre la recuperación y la construcción del prompt. Y ese sitio no
es casual: el prompt necesita saber el nivel **antes** de pedirle nada al
modelo, porque `ADR-014` §5.1 dice que el nivel *«lo fijó el arbitraje antes de
generar; el generador lo recibe, no lo decide»*.

Qué hace, y sus dos mitades
-------------------------------
Fija `ctx.nivel_divulgacion` con la escala de `RF-GEN-05` (`dominio/arbitraje/
divulgacion.py`, `PM-B05`) **y** `ctx.nivel_intervencion` con la jerarquía de
`T6` (`dominio/arbitraje/intervencion.py`, `PM-B13`). Las dos preguntas —
cuánto se revela y qué se hace— comparten el mismo filtro porque comparten el
mismo sitio en la cadena y el mismo `Señales` de entrada, pero se deciden por
separado: `RF-ORQ-04` exige una sola intervención por turno, no que la
intervención determine la divulgación ni al revés.

Por qué el nivel no lo decide este filtro sino un módulo aparte
----------------------------------------------------------------
Porque `RF-REG-06` pide registrar *«el nivel de divulgación alcanzado e **las
intervenciones descartadas por el arbitraje**»*. Un filtro que devolviera un
entero no podría decir qué más pedía escalar. `decidir()` y
`decidir_intervencion()` devuelven la decisión entera —nivel, motivo,
descartadas y lo que no se pudo evaluar— y este filtro las vuelca a la traza
tal cual, cada una bajo su propia clave.

El piso conservador, y por qué no es un valor por defecto cualquiera
----------------------------------------------------------------------
Sin señales, el nivel de divulgación es **1** y el de intervención es **5**.
El 1 es el único nivel de divulgación que no afirma nada: `ADR-008` V2 lo
llama el modo seguro y `ADR-014` C4 lo confirma. El 5 es la autorregulación,
la única intervención de `T6` que no presupone ningún estado afectivo o
conceptual del estudiante — es la posición que la corrección `E-01` le dio a
propósito, la del catch-all que no le roba el turno a nada.
"""

from __future__ import annotations

from dataclasses import replace

from dominio.arbitraje.divulgacion import Señales, decidir
from dominio.arbitraje.intervencion import decidir_intervencion
from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno


class FiltroArbitraje(Filtro):
    """Filtro 6 de `ADR-001` §6.3, divulgación e intervención."""

    nombre = "arbitraje de intervención"
    ruta = "caliente"

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        # Sin señales se opera con las vacías, que dan el piso: es lo mismo que
        # decidiría con un estudiante que acaba de escribir por primera vez.
        # La diferencia se anota, porque «no hay datos» y «los datos dicen que
        # no» no son lo mismo y el registro tiene que distinguirlos.
        aportadas = ctx.señales is not None
        señales = ctx.señales or Señales()
        # `DEC-R3` · lo que el estudiante PIDIÓ entra aparte de lo que se
        # infiere de él. El filtro 2 ya lo clasificó; aquí sólo se lee.
        divulgacion = decidir(señales, peticion=ctx.intencion_detalle)
        intervencion = decidir_intervencion(señales)

        meta = {
            "divulgacion": {
                "nivel": divulgacion.nivel,
                "nombre": divulgacion.nombre,
                "motivo": divulgacion.motivo,
                "alcance": divulgacion.alcance,
                # `RF-REG-06` · el estrato de decisión pedagógica, entero.
                "descartadas": divulgacion.descartadas,
                "sin_evaluar": divulgacion.sin_evaluar,
                "no_escalan": divulgacion.no_escalan,
            },
            "intervencion": {
                "nivel": intervencion.nivel,
                "nombre": intervencion.nombre,
                "motivo": intervencion.motivo,
                "descartadas": intervencion.descartadas,
                "sin_evaluar": intervencion.sin_evaluar,
            },
            "señales_aportadas": aportadas,
        }
        return (
            replace(
                ctx,
                nivel_divulgacion=divulgacion.nivel,
                alcance_divulgacion=divulgacion.alcance,
                nivel_intervencion=intervencion.nivel,
            ),
            meta,
        )
