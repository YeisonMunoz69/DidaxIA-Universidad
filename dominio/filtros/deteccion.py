from __future__ import annotations

from dataclasses import replace

from dominio.arbitraje.divulgacion import Señales
from dominio.deteccion.patrones import VERSION_BANCO, extraer
from dominio.filtros.base import Filtro
from dominio.modelo.contexto_de_uso import ContextoDeUso, PoliticaDelTurno
from dominio.modelo.estudiante import EstadoAfectivo, PerfilEstudiante
from dominio.modelo.turno import ContextoTurno
from dominio.pedagogia.conversacion import EstadoDeConversacion


UMBRAL_ALTO_POR_DEFECTO = 0.6


class FiltroDeteccion(Filtro):

    nombre = "extracción de indicadores conductuales"
    ruta = "caliente"

    def __init__(self, umbral_alto: float = UMBRAL_ALTO_POR_DEFECTO) -> None:
        self._umbral = umbral_alto

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        politica = PoliticaDelTurno(ContextoDeUso(ctx.contexto_de_uso))
        if not politica.extrae_indicadores_conductuales:

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

        de_la_conversacion = conversacion.afectivo
        for subcomponente in ("PS-Anx", "FAH", "autoeficacia"):
            de_la_conversacion, _ = de_la_conversacion.actualizar(
                subcomponente,
                observaciones.get(subcomponente, 0.0),
                turno=ctx.identificador_turno or ctx.identificador_sesion,
                señal="estado de la conversación activa",
            )

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

        señales_previas = ctx.señales or Señales()
        señales = replace(
            señales_previas,
            ansiedad_alta=_alta(de_la_conversacion, "PS-Anx", self._umbral),
            miedo_a_pedir_ayuda_alto=_alta(de_la_conversacion, "FAH", self._umbral),
            autoeficacia_baja=_alta(de_la_conversacion, "autoeficacia", self._umbral),

            ciclo_negativo=conversacion.problema.ciclo_negativo,

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
    return (afectivo.valor(subcomponente) or 0.0) >= umbral
