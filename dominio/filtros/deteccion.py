"""
deteccion.py — Filtro 3 · extracción de indicadores en ruta caliente (`PM-B10`)
====================================================================================

`ADR-001` §6.3 reserva el filtro 3 desde el primer día; hasta esta sesión la
lista de filtros de todos los orquestadores construidos simplemente no lo
traía. `ADR-003` §6.5 S1 lo sitúa en **ruta caliente** —igual que `PS-Anx`,
`FAH` y `autoeficacia`, los tres sub-componentes de nivel 1 que produce—, con
presupuesto `RNF-EFI-01` (≤300 ms) para todo el componente.

Por qué cabe en el presupuesto sin medirlo aparte
--------------------------------------------------------
Este filtro no hace ningún `I/O`. `dominio/deteccion/patrones.py` es
coincidencia de expresiones regulares precompiladas sobre una cadena de unos
pocos cientos de caracteres, y `dominio/modelo/estudiante.py` es aritmética.
No hay llamada a un puerto, ni a la base, ni al proveedor de generación —esas
son las operaciones que de verdad amenazan `RNF-EFI-01`, y ninguna vive aquí.
Persistir el resultado (`PM-B11`) es asunto de quien reciba
`ctx.perfil_actualizado` después del turno, no de este filtro.

`R-19` exige su propio diseño experimental para medir el presupuesto **del
sistema completo**, y esa medición no es la de este módulo: lo que aquí se
deja es la instrumentación —`TrazaFiltro.latencia_ms`, como en todo filtro
(`dominio/filtros/base.py`)— y una prueba de que el propio filtro, aislado,
corre en microsegundos. No se inventa una cifra del presupuesto completo.

Qué produce, y a quién se lo entrega
-----------------------------------------
Tres cosas, y las dos primeras son las que `dominio/arbitraje/divulgacion.py` y
`dominio/arbitraje/intervencion.py` llevan declarando `None` desde `PM-B05`:

- `ctx.señales` —`ansiedad_alta`, `miedo_a_pedir_ayuda_alto`, `autoeficacia_baja`
  y `ciclo_negativo`, ya no `None` sino derivados de la evidencia real—, para
  que el filtro 6 (`PM-B13`) arbitre con datos y no con el piso conservador.
  `intentos_en_el_problema`, `insistencias` y `peticion_confirmada` **no los toca
  este filtro**: siguen viniendo del adaptador de entrada, que es quien
  conoce la sesión, y este filtro los conserva tal como llegaron.
- `ctx.perfil_actualizado` — el `EstadoAfectivo` con la observación de este
  turno ya aplicada (`ADR-003` N2), listo para que `PM-B11` lo persista.
  `EstadoConceptual` y `EstadoEstrategico` **no los actualiza este filtro**:
  viajan sin tocar desde `ctx.perfil_previo`, porque sus eventos vienen de
  otro lado —`PM-B08` para R-C, un registro explícito de episodio para
  R-E—, no del texto libre de un turno cualquiera.
- `meta["entradas_de_auditoria"]` — cada `RegistroAfectivo` que
  `EstadoAfectivo.actualizar()` construyó, **ya en forma de diccionario JSON-
  segura** —no la instancia del `dataclass`—: esta traza acaba, sin tocarla,
  dentro de `TrazaFiltro.metadatos` y de ahí, si el filtro 12 está enganchado
  (`PM-B20`), directo a `json.dumps()` en `archivo.py`. Guardar la instancia
  habría roto esa serialización la primera vez que los dos filtros corrieran
  juntos. Quien persiste el perfil de verdad —`adaptadores/entrantes/http/
  turno.py`, `PM-B10`/`PM-B11` enganchados el 2026-08-12— reconstruye
  `RegistroAfectivo` desde este diccionario antes de llamar a
  `adaptador_perfil.registrar_afectivo()`.

🔴 Fase 4 · quién decide y quién se audita, que ya no son el mismo
-----------------------------------------------------------------------
La política F.6 de la fase 4 separa dos cosas que estaban fundidas:

| Estado | Para qué | De dónde sale |
|---|---|---|
| **el de la conversación** | **decidir** este turno | `ctx.estado_conversacion`, que el borde mantiene en la sesión |
| **el versionado** | **auditar** después | `ctx.perfil_previo`, que `AdaptadorTurno` reconstruye de PostgreSQL |

Hasta la fase 4 este filtro decidía con el segundo, y la consecuencia era
concreta: con `λ=0,85` y umbral `0,6`, **una conversación nueva heredaba la
puntuación de todas las anteriores** y podía arrancar con la intervención
puesta sin que el estudiante hubiera escrito nada. La política lo prohíbe
mientras el OE4 no calibre ese uso.

La fórmula se aplica **dos veces sobre bases distintas**, y no es duplicación:
son dos preguntas. Sobre el estado de la conversación sale lo que decide; sobre
el perfil versionado sale lo que se persiste y se audita. Las entradas de
auditoría son las del segundo, para que el registro longitudinal siga siendo
longitudinal.

Los dos productores que faltaban
-----------------------------------
`ansiedad_explicita` y `ciclo_negativo` llegaban **siempre en `None`**, así que
los niveles 4 y 2 de `T6` eran inalcanzables: los 43 turnos del banco congelado
salían con el nivel 5. Ahora:

- **`ansiedad_explicita`** sale de `intencion.carga_emocional_expresada`, que
  el filtro 2 produce de una manifestación textual directa en ESTE turno. Se
  llama así —expresada— y no «ansiedad detectada» porque lo único observable es
  que lo escribió.
- **`ciclo_negativo`** sale de los episodios del problema activo
  (`dominio/pedagogia/problema.py`), que el borde acumula turno a turno con
  cinco hechos señalables. `EstadoEstrategico.registrar()` existía desde
  `PM-B10` y **no lo llamaba nadie**.

El umbral que convierte `obs_t` en `alto`
-----------------------------------------------
`ADR-003` no fija un valor de `θᵢ` —lo declara pendiente de calibración en el
OE4, igual que `λ`—. `UMBRAL_ALTO_POR_DEFECTO` sigue esa misma convención: un
punto de partida sin respaldo empírico propio, configurable, y **no** el
resultado de una medición que esta sesión no hizo.
"""

from __future__ import annotations

from dataclasses import replace

from dominio.arbitraje.divulgacion import Señales
from dominio.deteccion.patrones import VERSION_BANCO, extraer
from dominio.filtros.base import Filtro
from dominio.modelo.contexto_de_uso import ContextoDeUso, PoliticaDelTurno
from dominio.modelo.estudiante import EstadoAfectivo, PerfilEstudiante
from dominio.modelo.turno import ContextoTurno
from dominio.pedagogia.conversacion import EstadoDeConversacion

#: `ADR-003` N1/§9.1: sin respaldo empírico propio, configurable, calibrable
#: en el OE4 — la misma postura que el umbral 0,70 de `ADR-006` U4.
UMBRAL_ALTO_POR_DEFECTO = 0.6


class FiltroDeteccion(Filtro):
    """Filtro 3 de `ADR-001` §6.3: PS-Anx, FAH y autoeficacia, ruta caliente."""

    nombre = "extracción de indicadores conductuales"
    ruta = "caliente"

    def __init__(self, umbral_alto: float = UMBRAL_ALTO_POR_DEFECTO) -> None:
        self._umbral = umbral_alto

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        politica = PoliticaDelTurno(ContextoDeUso(ctx.contexto_de_uso))
        if not politica.extrae_indicadores_conductuales:
            # `EQ-031` · no basta con evitar que el perfil se ESCRIBA. Si se
            # ejecutara el resto del filtro, la inferencia quedaría en tres
            # sitios: el estado afectivo de la conversación, las señales que
            # arbitran la respuesta y `TrazaFiltro.metadatos`, que el filtro 12
            # conserva en el archivo forense. Una consulta profesional no
            # produce ninguno de ellos.
            #
            # Se conserva el estado del problema —intentos, insistencias y
            # continuidad matemática— porque no es un expediente personal y
            # permite usar el mismo Tutor. Sólo se neutraliza el componente
            # afectivo, incluso si la sesión venía de una versión anterior que
            # alcanzó a acumularlo antes de esta corrección.
            conversacion = ctx.estado_conversacion or EstadoDeConversacion()
            señales_previas = ctx.señales or Señales()
            return (
                replace(
                    ctx,
                    señales=replace(
                        señales_previas,
                        ansiedad_alta=None,
                        miedo_a_pedir_ayuda_alto=None,
                        ciclo_negativo=None,
                        autoeficacia_baja=None,
                        ansiedad_explicita=None,
                    ),
                    perfil_actualizado=None,
                    estado_conversacion=replace(
                        conversacion,
                        afectivo=EstadoAfectivo(),
                    ),
                ),
                {
                    "omitido": True,
                    "motivo": "consulta_profesional_sin_evaluacion",
                },
            )

        previo = ctx.perfil_previo or PerfilEstudiante()
        conversacion = ctx.estado_conversacion or EstadoDeConversacion()
        observaciones = extraer(ctx.texto_estudiante)

        # ── El estado que DECIDE: el de esta conversación ──────────────────
        #
        # Se aplica la misma fórmula de `ADR-003` N2 sobre la base de la
        # conversación. Un turno neutral **también** pasa por aquí, y por eso
        # decae: la política F.8 lo exige y la fórmula ya lo daba —lo que
        # faltaba era llamarla siempre, no sólo cuando hay coincidencia.
        de_la_conversacion = conversacion.afectivo
        for subcomponente in ("PS-Anx", "FAH", "autoeficacia"):
            de_la_conversacion, _ = de_la_conversacion.actualizar(
                subcomponente,
                observaciones.get(subcomponente, 0.0),
                turno=ctx.identificador_turno or ctx.identificador_sesion,
                señal="estado de la conversación activa",
            )

        # ── El estado que se AUDITA: el perfil versionado ──────────────────
        afectivo = previo.afectivo
        entradas_de_auditoria = []
        for subcomponente in ("PS-Anx", "FAH", "autoeficacia"):
            obs_t = observaciones.get(subcomponente, 0.0)
            señal = (
                "patrón léxico coincidente" if subcomponente in observaciones
                else "sin coincidencia este turno"
            )
            afectivo, entrada = afectivo.actualizar(
                subcomponente, obs_t, turno=ctx.identificador_sesion, señal=señal
            )
            # Diccionario, no la instancia — ver «Qué produce» en el docstring
            # del módulo: esto viaja dentro de `TrazaFiltro.metadatos`, que el
            # filtro 12 serializa tal cual con `json.dumps()`.
            entradas_de_auditoria.append({
                "turno": entrada.turno,
                "subcomponente": entrada.subcomponente,
                "senal": entrada.senal,
                "regla_aplicada": entrada.regla_aplicada,
                "valor_previo": entrada.valor_previo,
                "valor_nuevo": entrada.valor_nuevo,
                "lambda_aplicado": entrada.lambda_aplicado,
                "certeza": entrada.certeza,
                "alcance": entrada.alcance,
            })

        perfil_actualizado = replace(previo, afectivo=afectivo)

        # 🔴 Las señales salen del estado de la CONVERSACIÓN, no del perfil.
        señales_previas = ctx.señales or Señales()
        señales = replace(
            señales_previas,
            ansiedad_alta=_alta(de_la_conversacion, "PS-Anx", self._umbral),
            miedo_a_pedir_ayuda_alto=_alta(de_la_conversacion, "FAH", self._umbral),
            autoeficacia_baja=_alta(de_la_conversacion, "autoeficacia", self._umbral),
            # El productor que faltaba: episodios reales del problema activo.
            ciclo_negativo=conversacion.problema.ciclo_negativo,
            # Y el otro: una manifestación textual directa en ESTE turno.
            ansiedad_explicita=(
                ctx.intencion_detalle.carga_emocional_expresada
                if ctx.intencion_detalle is not None
                else None
            ),
        )

        meta = {
            "observaciones": observaciones,
            "version_detector": VERSION_BANCO,
            "umbral_alto": self._umbral,
            # Lo que decide, y lo que se audita, por separado y con su nombre.
            "valores_de_la_conversacion": dict(de_la_conversacion.valores),
            "valores_del_perfil_versionado": dict(afectivo.valores),
            "decide_con": "conversacion_activa",
            "episodios_del_problema": len(conversacion.problema.episodios.episodios),
            "ciclo_negativo": conversacion.problema.ciclo_negativo,
            "entradas_de_auditoria": entradas_de_auditoria,
        }
        return (
            replace(
                ctx,
                señales=señales,
                perfil_actualizado=perfil_actualizado,
                estado_conversacion=conversacion.con_afectivo(de_la_conversacion),
            ),
            meta,
        )


def _alta(afectivo: EstadoAfectivo, subcomponente: str, umbral: float) -> bool:
    """Si el sub-componente supera el umbral en el estado que decide."""
    return (afectivo.valor(subcomponente) or 0.0) >= umbral
