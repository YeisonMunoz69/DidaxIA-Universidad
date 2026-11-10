from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dominio.puertos.registro import RegistroDeTurno

if TYPE_CHECKING:
    from collections.abc import Iterator

class AdaptadorRegistroArchivo:

    def __init__(self, cadena_de_conexion: str, directorio: Path) -> None:
        self._cadena = cadena_de_conexion
        self._directorio = directorio
        self._directorio.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _conexion(self) -> Iterator[Any]:
        from adaptadores.salientes.conexion import conectar

        with conectar(self._cadena) as cnx:
            yield cnx

    def registrar_turno_completo(self, registro: RegistroDeTurno) -> None:
        ruta = self._directorio / f"{registro.turno}.json"
        ruta.write_text(
            json.dumps(_a_json(registro), ensure_ascii=False, indent=2), encoding="utf-8"
        )

        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                INSERT INTO registro_turno (
                    turno, identificador_sesion, identificador_sujeto,
                    ruta_archivo, nivel_divulgacion, latencia_total_ms,
                    contexto_de_uso
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (turno) DO UPDATE SET
                    identificador_sujeto = EXCLUDED.identificador_sujeto,
                    ruta_archivo         = EXCLUDED.ruta_archivo,
                    nivel_divulgacion    = EXCLUDED.nivel_divulgacion,
                    latencia_total_ms    = EXCLUDED.latencia_total_ms,
                    contexto_de_uso      = EXCLUDED.contexto_de_uso,
                    creado_en            = now()
                """,
                (
                    registro.turno,
                    registro.identificador_sesion,

                    registro.identificador_sujeto,
                    str(ruta),
                    registro.nivel_divulgacion,
                    registro.latencia_total_ms,

                    str(registro.contexto_de_uso),
                ),
            )
            cnx.commit()

    _CLAVES_DE_BORRADO = ("identificador_sujeto", "identificador_sesion")

    def _borrar_donde(self, columna: str, valor: str) -> int:
        if columna not in self._CLAVES_DE_BORRADO:
            raise ValueError(f"columna de borrado no permitida: «{columna}»")
        rutas = []
        try:
            with self._conexion() as cnx, cnx.cursor() as cur:
                cur.execute(
                    f"SELECT ruta_archivo FROM registro_turno WHERE {columna} = %s",
                    (valor,),
                )
                rutas = [Path(fila[0]) for fila in cur.fetchall()]
                cur.execute(
                    f"DELETE FROM registro_turno WHERE {columna} = %s",
                    (valor,),
                )
                cnx.commit()
        except Exception:
            pass
        for ruta in rutas:
            ruta.unlink(missing_ok=True)
        return len(rutas)

    def suprimir_sujeto(self, identificador_sujeto: str) -> int:
        return self._borrar_donde("identificador_sujeto", identificador_sujeto)

    def suprimir_sesion(self, identificador_sesion: str) -> int:
        return self._borrar_donde("identificador_sesion", identificador_sesion)

def _a_json(registro: RegistroDeTurno) -> dict:
    return {
        "turno": registro.turno,
        "identificador_sesion": registro.identificador_sesion,

        "identificador_sujeto": registro.identificador_sujeto,
        "nivel_divulgacion": registro.nivel_divulgacion,

        "contexto_de_uso": str(registro.contexto_de_uso),
        "latencia_total_ms": registro.latencia_total_ms,
        "trazas": [
            {
                "filtro": t.filtro,
                "latencia_ms": t.latencia_ms,
                "ruta": t.ruta,
                "metadatos": t.metadatos,
            }
            for t in registro.trazas
        ],
    }
