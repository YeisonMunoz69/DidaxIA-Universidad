from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from adaptadores.salientes.recuperacion.indice import DIMENSION, Codificador
from dominio.puertos.corpus import Fragmento, Procedencia

if TYPE_CHECKING:
    from collections.abc import Iterator

_COLUMNAS = (
    "identificador, texto, nivel_apos, registro_duval, "
    "concepcion_asociada, nodo_grafo, obra, pagina, pagina_hasta, captura"
)


def _a_fragmento(fila: tuple[Any, ...]) -> Fragmento:
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

    def __init__(self, cadena_de_conexion: str, codificador: Codificador) -> None:
        self._cadena = cadena_de_conexion
        self._codificador = codificador

    @contextmanager
    def _conexion(self) -> Iterator[Any]:
        from adaptadores.salientes.conexion import conectar

        with conectar(self._cadena) as cnx:
            yield cnx

    def guardar(self, fragmentos: tuple[Fragmento, ...]) -> int:
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

    def similares(
        self,
        consulta: str,
        k: int,
        nodos: tuple[str, ...] | None = None,
    ) -> tuple[tuple[Fragmento, float], ...]:

        if not consulta.strip():
            return ()

        (vector,) = self._codificador.codificar((consulta,))
        literal = _a_literal(vector)

        sql = f"""
            SELECT {_COLUMNAS}, 1 - (representacion <=> %s::vector) AS similitud
              FROM fragmento
             WHERE representacion IS NOT NULL
        """
        parametros: list[Any] = [literal]

        if nodos is not None:

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
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"
