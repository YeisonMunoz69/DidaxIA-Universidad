"""
consentimiento_db.py — Persistencia y consulta de consentimiento en PostgreSQL
====================================================================================

La implementación de `PuertoConsentimiento`
(`dominio/puertos/consentimiento.py`) contra `consentimiento_usuario`
(`07-consentimiento-usuario.sql`).

Qué cambió en la Fase 2 · sesión 3, y qué NO
--------------------------------------------------
**Cambió quién decide la base.** Hasta esta sesión el módulo exponía dos
funciones sueltas —`guardar_consentimiento()` y `consultar_consentimiento()`—
que resolvían la cadena de conexión contra una constante calculada **al
importar el módulo**:

    _CADENA_BD_DEFECTO = os.getenv("AGENTE_BD", "")

`rutas/sesion.py` las llamaba directamente, así que la autoridad sobre a qué
base se escribe dependía del orden de importación y ninguna ruta podía recibir
otra implementación. Ahora la cadena entra por el constructor, la composición
elige la implementación y la ruta recibe la dependencia.

**No cambió nada observable.** Mismo SQL, mismo `ON CONFLICT`, misma clave
(`identificador_sujeto` si lo hay, correo si no), mismo `dict` de retorno,
mismos estados, mismo comportamiento ante un fallo: se registra un aviso y se
devuelve `None`/nada, porque un almacén caído no puede tumbar la respuesta de
la ruta. La política de consentimiento —edad, representante, revocación— es de
la Fase 3 y esta sesión no la toca.


"""

from __future__ import annotations

import logging

from adaptadores.salientes.conexion import conectar

_LOG = logging.getLogger(__name__)


class AdaptadorConsentimientoPostgres:
    """`PuertoConsentimiento` contra la base. La cadena entra por el
    constructor: este módulo no lee `AGENTE_BD` ni al importarse ni después."""

    def __init__(self, cadena_de_conexion: str) -> None:
        self._cadena = cadena_de_conexion

    def guardar(
        self,
        identificador_sujeto: str,
        correo: str,
        decision: str,
        edad: int | None = None,
    ) -> None:
        """Guarda o actualiza el consentimiento en `consentimiento_usuario`."""
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
        except Exception as e:  # noqa: BLE001 — el borde no puede caer por el almacén
            _LOG.warning("No se pudo guardar consentimiento en BD: %s", e)

    def consultar(self, identificador_sujeto: str, correo: str = "") -> dict | None:
        """Consulta si ya existe un consentimiento en la base de datos."""
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
        except Exception as e:  # noqa: BLE001 — el borde no puede caer por el almacén
            _LOG.warning("No se pudo consultar consentimiento en BD: %s", e)
        return None
