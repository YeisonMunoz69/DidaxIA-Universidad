from __future__ import annotations

from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno
from dominio.puertos.factores import PuertoFactores
from dominio.puertos.registro import (
    RELACION_OBSERVABLE,
    EntradaDeTurno,
    MaterialRegistrado,
    PuertoRegistro,
    RegistroDeTurno,
    TrazaRegistrada,
)


class FiltroRegistro(Filtro):

    nombre = "registro del turno completo"
    ruta = "fría"

    def __init__(
        self, puerto: PuertoRegistro, puerto_entradas: PuertoRegistro | None = None,
        puerto_factores: PuertoFactores | None = None,
    ) -> None:

        self._puerto = puerto
        self._puerto_entradas = puerto_entradas
        self._puerto_factores = puerto_factores

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        trazas = tuple(
            TrazaRegistrada(
                filtro=t.filtro, latencia_ms=t.latencia_ms, ruta=t.ruta, metadatos=t.metadatos
            )
            for t in ctx.trazas
        )
        registro = RegistroDeTurno(

            turno=ctx.identificador_turno or ctx.identificador_sesion,
            identificador_sesion=ctx.identificador_sesion,

            identificador_sujeto=ctx.identificador_sujeto or ctx.identificador_sesion,
            nivel_divulgacion=ctx.nivel_divulgacion,
            trazas=trazas,

            contexto_de_uso=ctx.contexto_de_uso,
        )

        fallos = registro.validar()
        if fallos:
            raise ValueError(f"registro del turno no admisible: {'; '.join(fallos)}")

        entradas = self._entradas_del_turno(ctx, registro.identificador_sujeto)
        for entrada in entradas:
            fallos = entrada.validar()
            if fallos:
                raise ValueError(
                    f"entrada de turno no admisible ({entrada.autor}): {'; '.join(fallos)}"
                )

        self._puerto.registrar_turno_completo(registro)
        if self._puerto_entradas is not None:
            for entrada in entradas:
                self._puerto_entradas.registrar_turno(entrada)

        factores_guardados = self._puerto_factores.registrar(ctx) if self._puerto_factores is not None else False

        meta = {
            "trazas_registradas": len(trazas),
            "lectura_conductual_guardada": factores_guardados,
            "latencia_total_ms": registro.latencia_total_ms,

            "voces_registradas": len(entradas) if self._puerto_entradas is not None else 0,
        }
        return ctx, meta

    def _entradas_del_turno(self, ctx: ContextoTurno, sujeto: str) -> list[EntradaDeTurno]:
        comun = {
            "turno": ctx.identificador_turno or ctx.identificador_sesion,
            "identificador_sesion": ctx.identificador_sesion,
            "identificador_sujeto": sujeto,
            "momento": ctx.momento,

            "consentimiento_evento": ctx.consentimiento_evento,

            "contexto_de_uso": ctx.contexto_de_uso,
        }
        entradas = []
        if ctx.texto_estudiante.strip():
            entradas.append(
                EntradaDeTurno(**comun, autor="estudiante", contenido=ctx.texto_estudiante)
            )
        if ctx.respuesta.strip():
            entradas.append(
                EntradaDeTurno(
                    **comun,
                    autor="sistema",
                    contenido=ctx.respuesta,

                    bloques=ctx.bloques_emitidos,
                    citas=ctx.citas_emitidas,
                    nivel=ctx.nivel_emitido,
                    procedencia_origen=ctx.procedencia_origen,
                    procedencia_referencia=ctx.procedencia_referencia,

                    material=_material_del_turno(ctx),
                    conceptos=ctx.conceptos_emitidos,
                )
            )
        elif ctx.degradacion.strip():
            entradas.append(
                EntradaDeTurno(
                    **comun, autor="sistema", contenido=ctx.degradacion, degradado=True
                )
            )
        return entradas

def _material_del_turno(ctx: ContextoTurno) -> tuple[MaterialRegistrado, ...]:
    recuperacion = ctx.recuperacion
    if recuperacion is None or not recuperacion.utilizable:
        return ()

    similitudes = recuperacion.similitudes
    material: list[MaterialRegistrado] = []
    vistos: set[str] = set()

    for posicion, fragmento in enumerate(recuperacion.fragmentos):

        if fragmento.identificador in vistos:
            continue
        vistos.add(fragmento.identificador)
        material.append(
            MaterialRegistrado(
                fragmento=fragmento.identificador,
                obra=fragmento.procedencia.obra,
                orden=len(material),
                relacion=RELACION_OBSERVABLE,

                similitud=(
                    float(similitudes[posicion]) if posicion < len(similitudes) else None
                ),
            )
        )
    return tuple(material)
