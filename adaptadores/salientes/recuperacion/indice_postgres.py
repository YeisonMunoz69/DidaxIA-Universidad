"""
indice_postgres.py — El índice sobre PostgreSQL con extensión vectorial
========================================================================

Implementa el contrato `Indice` contra el almacén que `ADR-010` adoptó, con el
controlador y el estilo que `DD-19` fijó: **`psycopg` 3 y SQL escrito aquí, sin
mapeador objeto-relacional**.

El SQL está a la vista a propósito. `ADR-004` no eligió este motor por comodidad
sino por mecanismos —exclusión sobre rangos, cascada declarada en la clave
foránea, cifrado de columna—, y un mapeador los esconde o los duplica en la
aplicación. Aquí lo que se lee es lo que la base ejecuta.

Cómo se mide la similitud, que es donde es fácil equivocarse
-------------------------------------------------------------
`ADR-006` fija el umbral en **coseno ≥0,70**. El operador `<=>` de la extensión
devuelve **distancia** coseno, no similitud, de modo que la similitud es
`1 - distancia`. Confundirlas invierte el orden y hace que el umbral descarte
justo lo que debía conservar, sin que nada falle.

La clase de operadores del índice —`vector_cosine_ops`— tiene que ser la misma
que la del operador de la consulta. Si no coinciden, PostgreSQL **no usa el
índice** y responde igual pero recorriendo la tabla entera: más lento y
silencioso. Por eso las dos cosas van declaradas juntas, aquí y en el esquema.

Lo que este adaptador NO hace
-----------------------------
**No codifica.** Recibe un `Codificador` y lo usa. El motivo está en el contrato:
el modelo real arrastra media biblioteca de aprendizaje automático, y meterla
aquí obligaría a instalarla para probar una consulta SQL.

**No decide el umbral.** Devuelve todo lo que encuentra con su similitud; quien
aplica `ADR-006` es el recuperador jerárquico. Aquí solo se ordena y se recorta
a `k`.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from adaptadores.salientes.recuperacion.indice import DIMENSION, Codificador
from dominio.puertos.corpus import Fragmento, Procedencia

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator

#: Columnas que reconstruyen un `Fragmento` completo. Se listan una sola vez
#: porque dos consultas que seleccionan «lo mismo» escrito dos veces divergen en
#: cuanto alguien añade un campo.
_COLUMNAS = (
    "identificador, texto, nivel_apos, registro_duval, "
    "concepcion_asociada, nodo_grafo, obra, pagina, pagina_hasta, captura"
)


def _a_fragmento(fila: tuple[Any, ...]) -> Fragmento:
    """Traduce una fila a un tipo del dominio.

    La traducción ocurre **aquí y no en el dominio**: es la regla N2 que
    `pruebas/arquitectura/` vigila —los tipos del borde no son los del núcleo—.
    """
    return Fragmento(
        identificador=fila[0],
        texto=fila[1],
        nivel_apos=fila[2],
        registro_duval=fila[3],
        concepcion_asociada=fila[4],
        nodo_grafo=fila[5],
        procedencia=Procedencia(
            obra=fila[6], pagina=fila[7], pagina_hasta=fila[8], captura=fila[9]
        ),
    )


class IndicePostgres:
    """Índice de fragmentos sobre PostgreSQL. Cumple `Indice`."""

    def __init__(self, cadena_de_conexion: str, codificador: Codificador) -> None:
        self._cadena = cadena_de_conexion
        self._codificador = codificador

    # -- conexión ---------------------------------------------------------

    @contextmanager
    def _conexion(self) -> Iterator[Any]:
        # Se importa aquí y no arriba para que el módulo se pueda leer e
        # inspeccionar sin tener el controlador instalado. Quien no vaya a
        # hablar con la base no debería tropezar con su dependencia.
        #
        # `A4.bis` · el plazo de espera vive en `salientes/conexion.py`, una
        # sola vez, y el import de `psycopg` sigue siendo perezoso allí.
        from adaptadores.salientes.conexion import conectar  # noqa: PLC0415

        with conectar(self._cadena) as cnx:
            yield cnx

    # -- escritura --------------------------------------------------------

    def guardar(self, fragmentos: tuple[Fragmento, ...]) -> int:
        """Inserta o actualiza fragmentos con su representación. Devuelve cuántos.

        Es `INSERT ... ON CONFLICT DO UPDATE` y conviene decir por qué, porque el
        proyecto tiene registrado un caso donde sobrescribir era el defecto:
        `profile_store.py` del artefacto sobrescribía el perfil del estudiante, y
        `ADR-004` C1 exige para ese dato **versionado sin sobrescritura**.

        Un fragmento del corpus no es ese caso. Es contenido, no historial: si se
        corrige una fórmula, la versión anterior era incorrecta y no hay ningún
        requisito que pida conservarla. La trazabilidad de un fragmento vive en
        su procedencia y en el historial del repositorio, que sí guarda el
        cambio.
        """
        if not fragmentos:
            return 0

        representaciones = self._codificador.codificar(
            tuple(f.texto for f in fragmentos)
        )
        if len(representaciones) != len(fragmentos):
            raise ValueError(
                f"el codificador devolvió {len(representaciones)} representaciones "
                f"para {len(fragmentos)} fragmentos"
            )
        for f, r in zip(fragmentos, representaciones, strict=True):
            if len(r) != DIMENSION:
                # Se comprueba antes de mandar para que el error nombre la causa.
                # Dejarlo a la base daría un fallo de tipo que no dice qué
                # devolvió el codificador ni para qué fragmento.
                raise ValueError(
                    f"{f.identificador}: el codificador devolvió {len(r)} "
                    f"dimensiones y el esquema declara {DIMENSION}"
                )

        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO fragmento (
                    identificador, texto, nivel_apos, registro_duval,
                    concepcion_asociada, nodo_grafo,
                    obra, pagina, pagina_hasta, captura, representacion
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (identificador) DO UPDATE SET
                    texto               = EXCLUDED.texto,
                    nivel_apos          = EXCLUDED.nivel_apos,
                    registro_duval      = EXCLUDED.registro_duval,
                    concepcion_asociada = EXCLUDED.concepcion_asociada,
                    nodo_grafo          = EXCLUDED.nodo_grafo,
                    obra                = EXCLUDED.obra,
                    pagina              = EXCLUDED.pagina,
                    pagina_hasta        = EXCLUDED.pagina_hasta,
                    captura             = EXCLUDED.captura,
                    representacion      = EXCLUDED.representacion
                """,
                [
                    (
                        f.identificador, f.texto, f.nivel_apos, f.registro_duval,
                        f.concepcion_asociada, f.nodo_grafo,
                        f.procedencia.obra, f.procedencia.pagina,
                        f.procedencia.pagina_hasta, f.procedencia.captura,
                        _a_literal(r),
                    )
                    for f, r in zip(fragmentos, representaciones, strict=True)
                ],
            )
            cnx.commit()
        return len(fragmentos)

    # -- lectura · el contrato `Indice` -----------------------------------

    def similares(
        self,
        consulta: str,
        k: int,
        nodos: tuple[str, ...] | None = None,
    ) -> tuple[tuple[Fragmento, float], ...]:
        """Los `k` más parecidos, con su similitud, de mayor a menor."""
        if not consulta.strip():
            return ()

        (vector,) = self._codificador.codificar((consulta,))
        literal = _a_literal(vector)

        # `1 - (representacion <=> %s)` convierte distancia en similitud. El
        # ORDER BY va sobre el operador y no sobre la resta: PostgreSQL solo usa
        # el índice HNSW si ordena por la expresión de distancia tal cual.
        sql = f"""
            SELECT {_COLUMNAS}, 1 - (representacion <=> %s::vector) AS similitud
              FROM fragmento
             WHERE representacion IS NOT NULL
        """
        parametros: list[Any] = [literal]

        if nodos is not None:
            # Recuperación filtrada por nodo activo · `RF-RAG-09`.
            # Una tupla vacía significa «ningún nodo», no «todos»: devolver todo
            # ante un alcance vacío convertiría el filtro en su contrario.
            if not nodos:
                return ()
            sql += " AND nodo_grafo = ANY(%s)"
            parametros.append(list(nodos))

        sql += " ORDER BY representacion <=> %s::vector LIMIT %s"
        parametros += [literal, k]

        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(sql, parametros)
            filas = cur.fetchall()

        return tuple((_a_fragmento(f), float(f[-1])) for f in filas)


def _a_literal(vector: tuple[float, ...]) -> str:
    """El formato de texto que la extensión acepta: `[1,2,3]`.

    Se escribe a mano en lugar de registrar el tipo con `pgvector.psycopg`
    porque es una línea y evita una dependencia más para el único sitio donde
    hace falta. Si algún día se necesita el tipo nativo —por rendimiento al
    insertar en volumen—, ese es el momento de traerla y no antes.
    """
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"
