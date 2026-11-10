"""
decision_conjunta_db.py — Una conexión, una transacción, todos los actos (`D1B`)
=================================================================================

`PuertoDecisionConjunta` contra la migración 11. **No añade ninguna tabla**: usa
`persona`, `consentimiento_version`, `consentimiento_evento` y
`asentimiento_evento`, que ya existen desde la sesión 2.

Por qué NO se compone de los adaptadores que ya había
---------------------------------------------------------------
`AdaptadorEventosDeConsentimientoPostgres.registrar()` y
`AdaptadorAsentimientoPostgres.registrar()` hacen, cada uno, exactamente el acto
que les toca. Llamarlos uno detrás del otro habría sido la implementación corta
—y habría sido incorrecta—: cada uno abre **su** conexión y **su** transacción,
así que entre las dos cabe un fallo, un reinicio o una caída de red.

Lo que quedaría entonces es una persona menor de edad con el consentimiento del
titular registrado y **sin** su asentimiento, sin que ninguna fila diga que
faltó algo. Nadie escribió nunca ese estado y el sistema lo presentaría como
real. `EQ-024` lo prohíbe con todas las letras y `D0` §10.10 lo repite: los
actos se guardan **atómicamente**.

Por eso este adaptador baja un nivel: abre una conexión, abre una transacción y
usa las operaciones sobre cursor de `base_postgres.py` —las mismas que los otros
dos usan por dentro— sin pasar por sus fronteras.

Todo se resuelve bajo el MISMO cerrojo
-------------------------------------------------
El orden no es una preferencia:

1. `FOR UPDATE` sobre la fila de `persona`. No protege esa fila —aquí no se
   cambia—: es el cerrojo por titular que serializa dos decisiones simultáneas
   del mismo sujeto **y también la apertura de un trámite de supresión**, que lo
   toma igual (ver el paso 2).
2. **¿hay una supresión abierta?** Si la hay, cero actos. `EQ-022` admite
   consultar y cancelar durante el trámite, no tratar datos nuevos, y un
   consentimiento —otorgado o rechazado— es una fila nueva sobre datos de
   alguien que acaba de pedir que se borren.
3. **edad y categoría**, de la fila ya bloqueada. Sin edad no hay régimen de
   `EQ-016` que aplicar y no se escribe nada.
4. **qué alcances hacen falta**, que sale de la categoría y de nada más.
5. **la versión requerida de cada uno**, y su huella, con `FOR SHARE` sobre la
   fila de la versión para que nadie publique una posterior mientras dura esto.
6. **la política de redecisión sobre el PAR completo**, antes de insertar
   ninguno. Es la diferencia entre revertir y no haber escrito.
7. **los INSERT**, en el orden de `ORDEN_DE_LOS_ACTOS`.

El paso 2 va donde va porque `AdaptadorSolicitudesDeSupresionPostgres.abrir()`
bloquea **la misma fila** con el mismo `FOR UPDATE`. Eso serializa las dos
operaciones y deja exactamente dos historias posibles: o la decisión toma el
cerrojo primero, confirma, y el trámite se abre después sobre un consentimiento
que ya existía —válido, ocurrió antes—; o el trámite toma el cerrojo primero,
confirma, y la decisión entra, lo ve y escribe cero. Una lectura fuera de la
transacción habría dejado la ventana entre comprobar y escribir.

⚠️ El paso 5 **no** consulta las tablas de transiciones individuales, y es la
corrección de `D1B` bis. Aquellas responden «¿puede este acto seguir al anterior
cuando alguien mueve esta dimensión sola?», que es la pregunta de la revocación
y no la de aquí: en una decisión conjunta, el acto de la dimensión que ya estaba
otorgada es la **reafirmación** que acompaña al cambio de la otra, no un doble
clic. La regla vive en `dominio/modelo/redecision.py`, con nombre propio y sin
tocar `TRANSICIONES` ni `TRANSICIONES_ASENTIMIENTO`, de las que sigue dependiendo
la revocación.

Leer la edad fuera del cerrojo habría abierto la ventana en la que alguien
cumple 18 entre la comprobación y el INSERT; leer la versión fuera, la ventana
en la que se publica una sucesora y el acto queda escrito sobre el texto viejo.

Qué pasa si el segundo INSERT falla
--------------------------------------------
La transacción entera se revierte y **no queda ninguna fila en ninguna de las
dos tablas**. No hay compensación que escribir porque no hay nada que compensar:
es la garantía de PostgreSQL, no una que este archivo implemente.
`pruebas/integracion/test_decision_conjunta_postgres.py` lo comprueba inyectando
un disparador que hace fallar el `INSERT` del asentimiento y contando cero filas
en las dos tablas.

Qué pasa con dos decisiones simultáneas
------------------------------------------------
La segunda espera en el `FOR UPDATE`. Cuando entra, `ultimo_acto()` ya ve lo que
la primera confirmó: el par entero refleja exactamente la decisión que se pide,
así que `exigir_redecision()` levanta `DecisionYaVigente`. Una gana, la otra
recibe un rechazo con motivo, y queda **un** juego de actos.

Esto sigue valiendo cuando se parte de un estado mixto —una dimensión revocada—,
que es justo donde la política nueva abre una puerta: abrirla no abre además la
de escribir dos juegos, porque quien gana deja el par al día.

Lo que este adaptador no hace
--------------------------------------
- no toca `representante_evidencia` ni `representante_revision`;
- no admite `revocado`: el tipo `Decision` sólo tiene dos valores;
- **no cancela, modifica ni abre** ninguna solicitud de supresión: sólo mira si
  hay una abierta. Cancelar un trámite en silencio sería la peor forma de
  «resolver» el conflicto —dejaría a alguien creyendo que pidió el borrado—;
- no lee el entorno, no importa FastAPI y no registra nada de lo que recibe.


"""

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

#: Qué tabla de eventos recibe el acto de cada alcance. Un diccionario cerrado y
#: de este árbol: los nombres que llegan a `insertar_acto()` salen de aquí y
#: nunca de la petición.
_TABLA_DE = {
    Alcance.TITULAR: "consentimiento_evento",
    Alcance.ASENTIMIENTO: "asentimiento_evento",
}


class AdaptadorDecisionConjuntaPostgres(RepositorioPostgres):
    """`PuertoDecisionConjunta` sobre las tablas de la migración 11."""

    def registrar_decision(
        self, sujeto_google: str, decision: Decision
    ) -> ActosDeLaDecision:
        """Ver el puerto. Una conexión, una transacción, todo o nada."""
        # `Decision(...)` antes de conectar: un valor que no es una decisión no
        # tiene por qué costar una conexión ni un cerrojo.
        decision = Decision(decision)
        with self._escritura() as cnx, cnx.cursor() as cur:
            # Cerrojo y comprobación del trámite, en ese orden y sin hueco.
            # `exigir_persona_activa()` es la MISMA operación que usan el perfil,
            # la evidencia y las clases: una redacción, cinco escrituras.
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

    # ── qué hace falta ──────────────────────────────────────────────────

    def _alcances_para(self, categoria: CategoriaDeEdad) -> tuple[Alcance, ...]:
        """Los alcances que esta decisión tiene que registrar, en su orden.

        La regla entera de `EQ-016` en una línea: un adulto produce el acto del
        titular; un menor produce ése **y** el de su propio asentimiento. La
        autorización del representante no está aquí — es una dimensión
        independiente, con su evidencia y su revisión, y `D1B` no la funde con
        el botón.
        """
        if categoria is CategoriaDeEdad.MENOR:
            return ORDEN_DE_LOS_ACTOS
        return (Alcance.TITULAR,)

    def _versiones_requeridas(
        self, cur: Any, alcances: tuple[Alcance, ...]
    ) -> dict[Alcance, tuple[str, str]]:
        """`{alcance: (codigo, huella)}` de lo que rige ahora, o el rechazo.

        Se resuelven **todas** antes de comprobar ninguna transición y mucho
        antes de insertar: si falta el texto de cualquiera de los alcances
        necesarios, no se escribe ningún evento, y el motivo dice cuáles faltan
        en vez de nombrar sólo el primero que se encontró.
        """
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
        # `exigir_version_requerida()` retiene cada fila con `FOR SHARE` y da el
        # motivo preciso —futura, vencida, desplazada— en vez de dejar que salte
        # el disparador con una violación que no se puede mostrar.
        resueltas: dict[Alcance, tuple[str, str]] = {}
        for alcance, codigo in codigos.items():
            exigir_version_requerida(cur, codigo, alcance.value)
            resueltas[alcance] = (codigo, huella_de_version(cur, codigo))
        return resueltas

    # ── que el PAR pueda escribirse, antes de escribir nada ─────────────

    def _exigir_redecision(
        self,
        cur: Any,
        sujeto: str,
        decision: Decision,
        alcances: tuple[Alcance, ...],
        categoria: CategoriaDeEdad,
        versiones: dict[Alcance, tuple[str, str]],
    ) -> None:
        """Una sola comprobación, sobre el par completo, antes de insertar.

        ⚠️ **Aquí había una comprobación por dimensión y ése era el defecto.**
        Cada mitad tenía razón por separado —el asentimiento revocado podía
        volver a otorgarse; el titular otorgado no podía repetirse— y juntas se
        contradecían, así que una persona que revocaba una sola dimensión se
        quedaba sin forma de volver a decidir. La política del par vive en
        `dominio/modelo/redecision.py` y no toca las tablas individuales.

        Se lee todo con la fila de la persona ya bloqueada, de modo que entre
        leer el estado y escribir el acto no cabe otra decisión.
        """
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
        """El estado vigente de una dimensión, tal como la política lo consume.

        Sin actos previos se declara `pendiente` y no `no_requerido`: quien llega
        aquí ya sabe que esa dimensión le corresponde —los alcances salieron de
        la categoría derivada de la fila bloqueada— y `no_requerido` describiría
        a otra persona.

        La categoría de edad sólo viaja en el titular. `EQ-021` obliga a volver a
        pedir autorización a quien cumple 18, y esa puerta se conserva; el
        asentimiento no la necesita porque quien deja de ser menor deja de tener
        esa dimensión, y eso ya lo decidió `_alcances_para()`.
        """
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

    # ── la escritura ────────────────────────────────────────────────────

    def _insertar(
        self,
        cur: Any,
        sujeto: str,
        decision: Decision,
        alcance: Alcance,
        version: tuple[str, str],
    ) -> ActoRegistrado:
        """Un acto, con su comprobante calculado aquí dentro.

        El comprobante entra en la fila y sale en el recibo, y se calcula sobre
        el código y la huella que se acaban de leer **bajo el mismo cerrojo**:
        así el recibo prueba el paquete que la fila referencia y no otro que
        hubiera podido publicarse mientras tanto.
        """
        codigo, huella = version
        comprobante = comprobante_de(sujeto, codigo, huella, decision.value)
        # La tabla del titular devuelve además la `categoria_edad` que derivó su
        # disparador; aquí no se usa —ya se decidió con la fila bloqueada— y por
        # eso se toman las dos primeras columnas y no se desempaqueta la fila.
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
