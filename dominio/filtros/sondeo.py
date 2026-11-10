"""
sondeo.py — Filtro 6.8 · ¿este turno plantea un ítem de dos niveles?
========================================================================

`RC-PED-06` pide que el tutor pregunte de vez en cuando con un ítem de dos
turnos. La regla de **cuándo** vive en `dominio/pedagogia/sondeo.py`, donde se
puede leer como tabla; este filtro la ejecuta dentro de la cadena.

Por qué la decisión se movió aquí · fase 4
---------------------------------------------
Estaba en el adaptador de entrada (`_con_sondeo`), **después** de la cadena, y
el comentario que la justificaba decía: *«el ítem no entra al prompt, no cambia
lo que el generador escribe y ningún filtro posterior lo consume»*. Las tres
cosas dejaron de ser ciertas cuando `diagnostico_two_tier` pasó a ser una
estrategia: si el turno va a plantear un ítem, la respuesta del tutor **no debe
además preguntar**, y eso lo tiene que saber el prompt.

Con la decisión después de la cadena, la regla de la política que produce
`DIAGNOSTICO_TWO_TIER` era inalcanzable: `ctx.hay_item_ofrecible` no lo ponía
nadie. Moverla aquí la hace alcanzable **y** deja una sola decisión: el
adaptador ya no decide, traduce lo que este filtro dejó.

Dónde va, y por qué ahí
--------------------------
Entre el diagnóstico (6.75) y la selección de estrategia (6.9). Después del
6.75 porque el nodo y el diagnóstico ya están fijados; antes del 6.9 porque su
resultado es una entrada de la política.

Lo que este filtro NO hace
-----------------------------
**No traduce el ítem al contrato.** Lo que el estudiante ve —enunciado y textos
de las razones, sin `es_correcta` ni concepción— lo arma
`adaptadores/entrantes/http/turno.py`, que es donde vive la traducción de
borde. Aquí el ítem viaja entero porque el dominio puede verlo entero.


"""

from __future__ import annotations

from dataclasses import replace

from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno
from dominio.pedagogia.intenciones import EMOCIONAL, familia_de
from dominio.pedagogia.sondeo import decidir
from dominio.pedagogia.configuracion_sondeos import NODOS_DIGITALES
from dominio.puertos.plantillas import PuertoPlantillas


class FiltroSondeo(Filtro):
    """Filtro 6.8 · fija si este turno lleva ítem de dos niveles.

    `plantillas` es opcional y por inyección, como los puertos de los filtros
    vecinos: sin banco de ítems no hay ninguno que plantear y el turno sigue
    exactamente como iba, con el motivo en la traza.
    """

    nombre = "ofrecimiento del ítem de dos niveles"
    ruta = "caliente"

    def __init__(self, plantillas: PuertoPlantillas | None = None, configuracion=None) -> None:
        self._plantillas = plantillas
        self._configuracion = configuracion

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        if self._plantillas is None or not ctx.nodo_activo:
            return ctx, {
                "procede": False,
                "motivo": (
                    "sin banco de ítems" if self._plantillas is None
                    else "el turno no tiene nodo activo"
                ),
            }

        habilitado, umbral = True, 2
        if self._configuracion is not None and ctx.nodo_activo in NODOS_DIGITALES:
            try:
                vigente = self._configuracion.consultar()
            except Exception:  # noqa: BLE001 — sin estado curricular no se ofrece nada
                return ctx, {"procede": False, "motivo": "configuración curricular no disponible"}
            habilitado = vigente.habilitado(ctx.nodo_activo)
            umbral = vigente.umbral_intentos

        ofrecimiento = decidir(
            _item_de(self._plantillas, ctx.nodo_activo),
            # La FAMILIA de `ADR-007`: la regla descarta lo afectivo, no una de
            # las diez clases del catálogo v1. Ver `familia_de`.
            intencion=familia_de(ctx.intencion) if ctx.intencion else "",
            trae_expresion=bool(ctx.expresiones),
            intentos_en_el_problema=ctx.señales.intentos_en_el_problema if ctx.señales else 0,
            estado=ctx.estado_de_sondeo,
            habilitado=habilitado,
            umbral_intentos=umbral,
        )
        meta = {"procede": ofrecimiento.procede, "motivo": ofrecimiento.motivo}
        if not ofrecimiento.procede:
            return ctx, meta
        meta["nodo"] = ofrecimiento.item.nodo
        return replace(ctx, item_ofrecido=ofrecimiento.item), meta


def _item_de(plantillas: PuertoPlantillas, nodo: str):
    """El ítem del nodo, o `None` si el banco no lo trae **o falla**.

    El puerto declara que sus lecturas nunca lanzan, pero quien compone el
    sistema puede haber inyectado otra cosa: un ítem que no se pudo consultar
    no puede tumbar un turno.
    """
    try:
        return plantillas.item_de(nodo)
    except Exception:  # noqa: BLE001
        return None


#: Se importa aquí para que el filtro pueda comparar sin volver a escribir la
#: constante. `EMOCIONAL` es la única familia que la regla de `sondeo.py`
#: descarta, y su nombre vive en `dominio/pedagogia/intenciones.py`.
__all__ = ["EMOCIONAL", "FiltroSondeo"]
