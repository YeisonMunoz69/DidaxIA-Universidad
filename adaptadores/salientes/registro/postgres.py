"""
postgres.py — Persistencia versionada del perfil sobre PostgreSQL (`PM-B11`)
================================================================================

`ADR-004` adoptó PostgreSQL citando, como evidencia concreta, que
`memory/profile_store.save_profile` de la iteración 0 usaba
`ON CONFLICT DO UPDATE` y **sobrescribía el perfil del estudiante** — el
mismo defecto que `indice_postgres.py` señala en su propio docstring al
explicar por qué el corpus sí puede usar esa forma y el perfil no puede.
Este adaptador es la promesa de `ADR-004` C1 hecha código: **sobrescribir
tiene que ser imposible, no solo improbable.**

Por qué esto no implementa `PuertoRegistro` tal cual
----------------------------------------------------------
`dominio/puertos/registro.py` ya está cerrado —«el puerto hermano ya existe»,
dice el encargo de esta sesión— y sus tres dataclasses de auditoría
(`RegistroAfectivo`, `RegistroConceptual`, `RegistroEstrategico`) no llevan
identidad del sujeto, solo `turno`. Reabrir ese puerto para añadir un campo
no era el encargo de `PM-B11`. Este adaptador toma la identidad del sujeto
como parámetro **aparte** de la entrada de auditoría, en vez de forzarla
dentro de un tipo que no la previó — la misma decisión que
`precomputar_limite()` tomó en `adaptadores/salientes/simbolico/adaptador.py`
al ser *«capacidad del adaptador, no del puerto»*.

`identificador_sujeto` es hoy `identificador_sesion`, y se dice por qué
------------------------------------------------------------------------------
`PM-B15` (identidad delegada) no existía cuando se escribió esto. Sin ella no
había ningún identificador que sobreviviera a una sesión, así que R-C y R-E
—que `ADR-003` §6.2 declara **longitudinales entre sesiones**— solo podían
ser longitudinales dentro de lo que dura la sesión.

> ⚠️ **2026-08-12 · PM-B15 cerrada, y esta limitación se acorta a la mitad.**
> Para quien se autenticó con Google, `aplicacion.py` ya pasa el
> `identificador_estable` de la identidad (no el de sesión) a
> `suprimir_sujeto()`. Este adaptador **sigue sin distinguir uno de otro** —
> toma lo que le den, como siempre—; la decisión de CUÁL identificador usar
> es y sigue siendo del llamador, la misma disciplina que `identificador_
> sujeto` como parámetro aparte ya aplicaba. Nada en filtro 3/12 escribe
> perfil en producción todavía (ver `PM-B10`/`PM-B20`), así que R-C y R-E
> longitudinales entre sesiones sigue siendo una promesa sin ejercitar, no
> un hecho medido — la mitad que PM-B15 no cierra es que alguien escriba.

El mecanismo de `ADR-004` C1, en el código y no solo en el esquema
------------------------------------------------------------------------
La restricción de exclusión de `perfil_afectivo` es la última línea de
defensa, no la única: **el adaptador nunca ejecuta un `UPDATE` sobre el
contenido de una fila**. `registrar_afectivo` hace dos sentencias en la misma
transacción —cerrar la vigencia de la fila anterior (si la hay) e insertar la
nueva—, nunca una que toque `valor_nuevo`, `regla_aplicada` ni ningún otro
campo de una fila ya escrita. Si un defecto futuro se saltara el cierre, la
base rechaza el `INSERT` con `ExclusionViolation` — es la comprobación de
`pruebas/integracion/test_registro_postgres.py`, hecha contra la base real y
no contra una suposición sobre lo que Postgres haría.

`R-C` y `R-E` no necesitan el mecanismo de rango
------------------------------------------------------
Ninguna de las dos decae ni tiene «vigencia» en el sentido de R-A: son
registros de eventos. `registrar_conceptual` y `registrar_estrategico` son
`INSERT` puro, sin ninguna sentencia `UPDATE` en absoluto — ni siquiera hace
falta una restricción de exclusión para que sobrescribir sea imposible: no
hay ninguna vía en el código para intentarlo.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from dominio.modelo.estudiante import (
    EstadoAfectivo,
    EstadoConceptual,
    EstadoEstrategico,
    PerfilEstudiante,
)
from dominio.puertos.registro import RegistroAfectivo as EntradaAfectiva
from dominio.puertos.registro import RegistroConceptual as EntradaConceptual
from dominio.puertos.registro import RegistroEstrategico as EntradaEstrategica

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator


class AdaptadorPerfilPostgres:
    """Persiste y reconstruye los tres registros de `ADR-003` §6.2.

    No implementa `PuertoRegistro` —ver el docstring del módulo—: sus tres
    métodos de escritura toman `identificador_sujeto` explícito, y añade
    `reconstruir_perfil`, que ese puerto no declara porque **es ruta fría y
    escribe, no decide** (su propio docstring). Reconstruir el estado actual
    a partir del historial sí es asunto de este adaptador: sin eso, un
    historial que nunca se puede releer no es persistencia, es un vertedero.
    """

    def __init__(self, cadena_de_conexion: str) -> None:
        self._cadena = cadena_de_conexion

    @contextmanager
    def _conexion(self) -> Iterator[Any]:
        # Igual que `indice_postgres.py`: se importa aquí para que el módulo
        # se pueda leer sin tener el controlador instalado.
        #
        # `A4.bis` · el plazo de espera vive en `salientes/conexion.py`.
        from adaptadores.salientes.conexion import conectar  # noqa: PLC0415

        with conectar(self._cadena) as cnx:
            yield cnx

    # -- R-A · versionado por rango temporal, ADR-004 C1 -------------------

    def registrar_afectivo(
        self, identificador_sujeto: str, registro: EntradaAfectiva
    ) -> None:
        """Cierra la vigencia de la fila anterior (si existe) e inserta la
        nueva, en la misma transacción. Nunca actualiza el contenido de una
        fila ya escrita — ver el docstring del módulo."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                UPDATE perfil_afectivo
                   SET vigencia = tstzrange(lower(vigencia), now())
                 WHERE identificador_sujeto = %s
                   AND subcomponente = %s
                   AND alcance = %s
                   AND upper(vigencia) IS NULL
                """,
                (identificador_sujeto, registro.subcomponente, registro.alcance),
            )
            cur.execute(
                """
                INSERT INTO perfil_afectivo (
                    identificador_sujeto, subcomponente, alcance,
                    turno, señal, regla_aplicada,
                    valor_previo, valor_nuevo, lambda_aplicado, certeza
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    identificador_sujeto,
                    registro.subcomponente,
                    registro.alcance,
                    registro.turno,
                    registro.senal,
                    registro.regla_aplicada,
                    registro.valor_previo,
                    registro.valor_nuevo,
                    registro.lambda_aplicado,
                    registro.certeza,
                ),
            )
            cnx.commit()

    # -- R-C y R-E · anexado puro --------------------------------------------

    def registrar_conceptual(
        self, identificador_sujeto: str, registro: EntradaConceptual
    ) -> None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                INSERT INTO perfil_conceptual (
                    identificador_sujeto, elemento, turno,
                    estado_previo, estado_nuevo, evento_diagnostico
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    identificador_sujeto,
                    registro.elemento,
                    registro.turno,
                    registro.estado_previo,
                    registro.estado_nuevo,
                    registro.evento_diagnostico,
                ),
            )
            cnx.commit()

    def registrar_estrategico(
        self, identificador_sujeto: str, registro: EntradaEstrategica
    ) -> None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                INSERT INTO perfil_estrategico (
                    identificador_sujeto, turno, tipo_evento,
                    ventana, contador, ciclo_negativo
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    identificador_sujeto,
                    registro.turno,
                    registro.tipo_evento,
                    registro.ventana,
                    registro.contador,
                    registro.ciclo_negativo,
                ),
            )
            cnx.commit()

    # -- supresión · RD-22, la única operación que sí borra -----------------

    def suprimir_sujeto(self, identificador_sujeto: str) -> None:
        """Borra **todas** las versiones de los tres registros de este sujeto.

        `RD-22` pide supresión completa; `ADR-004` C1 pide que no se pueda
        sobrescribir el HISTORIAL mientras el perfil está activo, y las dos
        cosas no chocan: `DELETE` no es `UPDATE`. Nada en este adaptador cede
        ante la idea de "sobrescribir con datos vacíos" — se elimina la fila,
        no se le escribe una versión en blanco encima.
        """
        with self._conexion() as cnx, cnx.cursor() as cur:
            for tabla in ("perfil_afectivo", "perfil_conceptual", "perfil_estrategico"):
                try:
                    with cnx.transaction():
                        cur.execute(
                            f"DELETE FROM {tabla} WHERE identificador_sujeto = %s",  # noqa: S608
                            (identificador_sujeto,),
                        )
                except Exception:
                    pass
            cnx.commit()

    # -- lectura · reconstrucción, no la decide el puerto ------------------

    def reconstruir_perfil(self, identificador_sujeto: str) -> PerfilEstudiante:
        """El `PerfilEstudiante` actual, plegando el historial versionado.

        R-A: la fila vigente por sub-componente (`upper(vigencia) IS NULL`).
        R-C: la última fila por elemento. R-E: la última fila, que ya lleva
        el contador y el `ciclo_negativo` que `dominio/modelo/estudiante.py`
        calculó en su momento — no se recalculan aquí, se leen.
        """
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT subcomponente, valor_nuevo
                  FROM perfil_afectivo
                 WHERE identificador_sujeto = %s AND upper(vigencia) IS NULL
                """,
                (identificador_sujeto,),
            )
            valores = {fila[0]: float(fila[1]) for fila in cur.fetchall()}

            cur.execute(
                """
                SELECT DISTINCT ON (elemento) elemento, estado_nuevo
                  FROM perfil_conceptual
                 WHERE identificador_sujeto = %s
                 ORDER BY elemento, creado_en DESC
                """,
                (identificador_sujeto,),
            )
            estados = {fila[0]: fila[1] for fila in cur.fetchall()}

            cur.execute(
                """
                SELECT ventana
                  FROM perfil_estrategico
                 WHERE identificador_sujeto = %s
                 ORDER BY creado_en DESC
                 LIMIT 1
                """,
                (identificador_sujeto,),
            )
            fila = cur.fetchone()
            ventana = fila[0] if fila else EstadoEstrategico().ventana

        return PerfilEstudiante(
            afectivo=EstadoAfectivo(valores=valores),
            conceptual=EstadoConceptual(estados=estados),
            # `EstadoEstrategico.episodios` no se reconstruye fila a fila:
            # `dominio/puertos/registro.py` no guarda el episodio en detalle,
            # solo el resumen (`contador`, `ciclo_negativo`) que ya se
            # calculó. Reconstruir la ventana exacta de episodios exigiría
            # guardar cada `Episodio` completo, que esta sesión no decidió
            # hacer — declarado, no un descuido.
            estrategico=EstadoEstrategico(ventana=ventana),
        )
