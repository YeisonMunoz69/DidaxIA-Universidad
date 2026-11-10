from __future__ import annotations

from adaptadores.salientes.registro.base_postgres import RepositorioPostgres


SIN_CORPUS = ""


class VersionDelCorpusPostgres(RepositorioPostgres):

    def actual(self) -> str:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute("SELECT count(*), max(cargado_en) FROM fragmento")
            fila = cur.fetchone()
        if fila is None:
            return SIN_CORPUS
        cantidad, mas_reciente = fila
        if not cantidad or mas_reciente is None:
            return SIN_CORPUS
        from datetime import UTC

        marca = mas_reciente.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        return f"{int(cantidad)}@{marca}"
