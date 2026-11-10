"""
conversacion.py — El estado temporal que toma las decisiones del turno
==========================================================================

La política F de la fase 4 dice, en su punto 6: *«el estado que toma decisiones
es de la conversación activa. Las observaciones longitudinales persistidas
quedan disponibles para auditoría, pero no deben arrastrar automáticamente una
intervención a una conversación nueva mientras OE4 no calibre ese uso»*.

Hasta aquí no era así. El filtro 3 partía de `ctx.perfil_previo`, que
`AdaptadorTurno` reconstruye de PostgreSQL, de modo que **una conversación
nueva heredaba la puntuación afectiva de todas las anteriores**. Con `λ=0,85` y
umbral `0,6`, un estudiante que hubiera escrito varias veces «no puedo con
esto» arrancaba su siguiente conversación con la intervención puesta, sin haber
escrito nada todavía.

Este módulo es el estado que sí decide: **de la conversación, temporal y
corregible**. El perfil versionado sigue existiendo y sigue escribiéndose
—gateado—, pero para auditar, no para intervenir.

Qué NO es este estado
------------------------
No es personalidad, capacidad, salud mental, diagnóstico clínico ni un rasgo
estable. Son **acciones observables acumuladas dentro de una conversación**, con
la fórmula de `ADR-003` N2 y sus valores v1 sin recalibrar: `λ = 0,85`, umbral
alto `0,6`, línea base medida 7/8/7. La política F.5 prohíbe recalibrarlos con
conversaciones sintéticas, y esta entrega no los toca.

Los tres nombres, y por qué se dicen así hacia fuera
-------------------------------------------------------
Internamente los sub-componentes siguen llamándose `PS-Anx`, `FAH` y
`autoeficacia`, porque es como `ADR-003` los define y renombrarlos rompería la
trazabilidad del perfil versionado. Hacia el estudiante y en la documentación
funcional se habla de **carga emocional expresada** y **señal textual
temporal** — política E de la fase—, y ninguno de los tres nombres internos
cruza jamás a una respuesta: la frase visible se elige por estrategia, no por
señal (`dominio/pedagogia/estrategias.py`).


"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from dominio.modelo.estudiante import EstadoAfectivo
from dominio.pedagogia.problema import EstadoDelProblema


@dataclass(frozen=True)
class EstadoDeConversacion:
    """Lo que esta conversación —y sólo ésta— sabe del estudiante.

    Viaja de fuera de la cadena, igual que `Señales`: lo mantiene el borde,
    que es quien conoce la sesión. `None` en `ContextoTurno` significa que
    nadie lo aportó, y entonces la cadena opera con uno en blanco — el mismo
    piso conservador que el resto del sistema.
    """

    #: El estado afectivo **de esta conversación**. Empieza en blanco en cada
    #: una, y eso es la política F.6, no una limitación.
    afectivo: EstadoAfectivo = field(default_factory=EstadoAfectivo)
    #: El ejercicio activo y sus contadores.
    problema: EstadoDelProblema = field(default_factory=EstadoDelProblema)
    #: La preferencia de que el estilo no se adapte a sus expresiones (F.9).
    #: No se apaga sola: retirarla es un acto del estudiante.
    sin_adaptacion: bool = False
    #: La estrategia del turno anterior, para saber si hay cambio que anunciar.
    estrategia_previa: str = ""

    def como_dict(self) -> dict:
        return {
            "afectivo": dict(self.afectivo.valores),
            "problema": self.problema.como_dict(),
            "sin_adaptacion": self.sin_adaptacion,
            "estrategia_previa": self.estrategia_previa,
        }

    @classmethod
    def desde_dict(cls, crudo: dict | None) -> EstadoDeConversacion:
        """Reconstruye el estado desde el almacén de sesiones.

        Tolera un diccionario incompleto o ausente: una sesión abierta antes de
        que este campo existiera no puede tumbar el turno, y el estado en
        blanco es el mismo piso con el que empieza una conversación nueva.
        """
        if not isinstance(crudo, dict):
            return cls()
        afectivo = crudo.get("afectivo")
        return cls(
            afectivo=EstadoAfectivo(
                valores={k: float(v) for k, v in afectivo.items()}
                if isinstance(afectivo, dict)
                else {}
            ),
            problema=EstadoDelProblema.desde_dict(crudo.get("problema") or {}),
            sin_adaptacion=bool(crudo.get("sin_adaptacion", False)),
            estrategia_previa=str(crudo.get("estrategia_previa", "")),
        )

    def con_afectivo(self, afectivo: EstadoAfectivo) -> EstadoDeConversacion:
        return replace(self, afectivo=afectivo)

    def con_problema(self, problema: EstadoDelProblema) -> EstadoDeConversacion:
        return replace(self, problema=problema)

    def con_inferencia_corregida(self) -> EstadoDeConversacion:
        """El estado tras una corrección del estudiante · paquete F.

        🔴 **`corrige_inferencia` se clasificaba, se registraba y no cambiaba
        nada.** El estudiante escribía *«no, no estoy bloqueado»* o *«no es
        eso, me malinterpretas»* y el turno siguiente se decidía con la misma
        inferencia que acababa de negarle. `RP-20` obliga a comunicar las
        inferencias como probabilísticas; una que el titular niega y el sistema
        conserva no es probabilística, es una etiqueta.

        Qué se invalida, exactamente
        -------------------------------
        **La inferencia conductual acumulada de esta conversación**, que es lo
        que el estudiante puede negar: los valores de `PS-Anx`, `FAH` y
        autoeficacia que el filtro 3 fue sumando turno a turno, y con ellos el
        nivel de intervención de `T6` y sus modificadores. Vuelven al piso —el
        mismo con el que empieza una conversación nueva—, no a un valor
        inventado.

        Qué NO se toca, y es la otra mitad de la decisión
        ---------------------------------------------------
        **Nada de lo que el estudiante no ha negado.** Sus intentos, sus
        insistencias, las expresiones que escribió, el ejercicio activo, los
        episodios de su trabajo y el archivo de problemas siguen exactamente
        igual. Negar *«estoy bloqueado»* no es negar haber intentado dos veces,
        y borrar el trabajo al corregir una inferencia castigaría al estudiante
        por corregirla.

        Tampoco se toca la preferencia de no adaptación: retirarla es un acto
        propio y distinto, con su propia orden.
        """
        return replace(self, afectivo=EstadoAfectivo())
