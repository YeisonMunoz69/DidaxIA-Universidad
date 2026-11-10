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

if TYPE_CHECKING:
    from collections.abc import Iterator

class AdaptadorPerfilPostgres:

    def __init__(self, cadena_de_conexion: str) -> None:
        self._cadena = cadena_de_conexion

    @contextmanager
    def _conexion(self) -> Iterator[Any]:
        from adaptadores.salientes.conexion import conectar

        with conectar(self._cadena) as cnx:
            yield cnx

    def registrar_afectivo(
        self, identificador_sujeto: str, registro: EntradaAfectiva
    ) -> None:

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

    def suprimir_sujeto(self, identificador_sujeto: str) -> None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            for tabla in ("perfil_afectivo", "perfil_conceptual", "perfil_estrategico"):
                try:
                    with cnx.transaction():
                        cur.execute(
                            f"DELETE FROM {tabla} WHERE identificador_sujeto = %s",
                            (identificador_sujeto,),
                        )
                except Exception:
                    pass
            cnx.commit()

    def reconstruir_perfil(self, identificador_sujeto: str) -> PerfilEstudiante:
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

            estrategico=EstadoEstrategico(ventana=ventana),
        )
