from __future__ import annotations

import hashlib

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.autorizacion_sql import exigir_investigador_administrador
from adaptadores.salientes.registro.base_postgres import RepositorioPostgres


class AuditorDeInformesPostgres(RepositorioPostgres):
    def registrar(self, datos: dict, documento: bytes) -> None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, datos["actor"])
            anotar(
                cur,
                datos["operacion"],
                actor=datos["actor"],
                detalle={
                    "tipo": datos["tipo"],
                    "codigo": datos["codigo"],
                    "periodo": datos["periodo"],
                    "filtros": datos["filtros"],
                    "formato": "pdf",
                    "bytes": len(documento),
                    "sha256": hashlib.sha256(documento).hexdigest(),
                    "version_plantilla": datos.get("version_plantilla", ""),
                    "resultado": "exitoso",
                    "incluye_anexo_personal": False,
                },
            )
            cnx.commit()
