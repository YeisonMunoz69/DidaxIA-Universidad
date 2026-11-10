from __future__ import annotations

import logging

from adaptadores.salientes.conexion import conectar

_LOG = logging.getLogger(__name__)


class AdaptadorConsentimientoPostgres:

    def __init__(self, cadena_de_conexion: str) -> None:
        self._cadena = cadena_de_conexion

    def guardar(
        self,
        identificador_sujeto: str,
        correo: str,
        decision: str,
        edad: int | None = None,
    ) -> None:

        if not identificador_sujeto and not correo:
            return
        if not self._cadena:
            return
        try:
            with conectar(self._cadena) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO consentimiento_usuario (identificador_sujeto, correo, decision, edad, momento)
                    VALUES (%s, %s, %s, %s, now())
                    ON CONFLICT (identificador_sujeto) DO UPDATE
                    SET decision = EXCLUDED.decision,
                        correo = COALESCE(EXCLUDED.correo, consentimiento_usuario.correo),
                        edad = COALESCE(EXCLUDED.edad, consentimiento_usuario.edad),
                        momento = EXCLUDED.momento
                    """,
                    (identificador_sujeto or correo, correo, decision, edad),
                )
        except Exception as e:
            _LOG.warning("No se pudo guardar consentimiento en BD: %s", e)

    def consultar(self, identificador_sujeto: str, correo: str = "") -> dict | None:
        if not identificador_sujeto and not correo:
            return None
        if not self._cadena:
            return None
        try:
            with conectar(self._cadena) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT decision, edad
                    FROM consentimiento_usuario
                    WHERE identificador_sujeto = %s OR (correo = %s AND correo != '')
                    ORDER BY momento DESC
                    LIMIT 1
                    """,
                    (identificador_sujeto, correo),
                )
                fila = cur.fetchone()
                if fila:
                    return {"decision": fila[0], "edad": fila[1]}
        except Exception as e:
            _LOG.warning("No se pudo consultar consentimiento en BD: %s", e)
        return None
