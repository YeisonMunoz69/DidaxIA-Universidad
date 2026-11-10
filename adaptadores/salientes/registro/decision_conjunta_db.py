from __future__ import annotations

from typing import Any

from adaptadores.salientes.registro.base_postgres import (
    RepositorioPostgres,
    exigir_categoria_de_edad,
    exigir_persona_activa,
    exigir_version_requerida,
    huella_de_version,
    insertar_acto,
    ultimo_acto,
    version_requerida_de,
)
from dominio.modelo.comprobante import comprobante_de
from dominio.modelo.consentimiento import Alcance, EstadoConsentimiento
from dominio.modelo.decision_conjunta import (
    ORDEN_DE_LOS_ACTOS,
    ActoRegistrado,
    ActosDeLaDecision,
    Decision,
)
from dominio.modelo.identidad import CategoriaDeEdad
from dominio.modelo.menores import EstadoAsentimiento
from dominio.modelo.redecision import DimensionDecidible, exigir_redecision
from dominio.puertos.decision_conjunta import VersionesFaltantes


_TABLA_DE = {
    Alcance.TITULAR: "consentimiento_evento",
    Alcance.ASENTIMIENTO: "asentimiento_evento",
}


class AdaptadorDecisionConjuntaPostgres(RepositorioPostgres):

    def registrar_decision(
        self, sujeto_google: str, decision: Decision
    ) -> ActosDeLaDecision:

        decision = Decision(decision)
        with self._escritura() as cnx, cnx.cursor() as cur:

            categoria = exigir_categoria_de_edad(
                exigir_persona_activa(cur, sujeto_google)
            )
            alcances = self._alcances_para(categoria)
            versiones = self._versiones_requeridas(cur, alcances)
            self._exigir_redecision(cur, sujeto_google, decision, alcances, categoria, versiones)
            actos = tuple(
                self._insertar(cur, sujeto_google, decision, alcance, versiones[alcance])
                for alcance in alcances
            )
        return ActosDeLaDecision(sujeto_google=sujeto_google, actos=actos)

    def _alcances_para(self, categoria: CategoriaDeEdad) -> tuple[Alcance, ...]:
        if categoria is CategoriaDeEdad.MENOR:
            return ORDEN_DE_LOS_ACTOS
        return (Alcance.TITULAR,)

    def _versiones_requeridas(
        self, cur: Any, alcances: tuple[Alcance, ...]
    ) -> dict[Alcance, tuple[str, str]]:

        codigos: dict[Alcance, str] = {}
        faltan: list[Alcance] = []
        for alcance in alcances:
            codigo = version_requerida_de(cur, alcance.value)
            if codigo is None:
                faltan.append(alcance)
            else:
                codigos[alcance] = codigo
        if faltan:
            raise VersionesFaltantes(tuple(faltan))

        resueltas: dict[Alcance, tuple[str, str]] = {}
        for alcance, codigo in codigos.items():
            exigir_version_requerida(cur, codigo, alcance.value)
            resueltas[alcance] = (codigo, huella_de_version(cur, codigo))
        return resueltas

    def _exigir_redecision(
        self,
        cur: Any,
        sujeto: str,
        decision: Decision,
        alcances: tuple[Alcance, ...],
        categoria: CategoriaDeEdad,
        versiones: dict[Alcance, tuple[str, str]],
    ) -> None:

        exigir_redecision(
            tuple(
                self._dimension(cur, sujeto, alcance, versiones[alcance][0], categoria)
                for alcance in alcances
            ),
            decision,
        )

    def _dimension(
        self,
        cur: Any,
        sujeto: str,
        alcance: Alcance,
        requerida: str,
        categoria: CategoriaDeEdad,
    ) -> DimensionDecidible:

        if alcance is Alcance.TITULAR:
            fila = ultimo_acto(
                cur, _TABLA_DE[alcance], sujeto, ("estado", "version", "categoria_edad")
            )
            return DimensionDecidible(
                alcance=alcance,
                estado=fila[0] if fila else EstadoConsentimiento.PENDIENTE.value,
                version=fila[1] if fila else None,
                version_requerida=requerida,
                categoria_del_acto=CategoriaDeEdad(fila[2]) if fila else None,
                categoria_actual=categoria,
            )
        fila = ultimo_acto(cur, _TABLA_DE[alcance], sujeto, ("estado", "version"))
        return DimensionDecidible(
            alcance=alcance,
            estado=fila[0] if fila else EstadoAsentimiento.PENDIENTE.value,
            version=fila[1] if fila else None,
            version_requerida=requerida,
        )

    def _insertar(
        self,
        cur: Any,
        sujeto: str,
        decision: Decision,
        alcance: Alcance,
        version: tuple[str, str],
    ) -> ActoRegistrado:

        codigo, huella = version
        comprobante = comprobante_de(sujeto, codigo, huella, decision.value)

        fila = insertar_acto(
            cur,
            _TABLA_DE[alcance],
            sujeto=sujeto,
            version=codigo,
            estado=decision.value,
            comprobante=comprobante,
        )
        secuencia, momento = fila[0], fila[1]
        return ActoRegistrado(
            alcance=alcance,
            version=codigo,
            decision=decision,
            comprobante=comprobante,
            momento=momento,
            secuencia=secuencia,
        )
