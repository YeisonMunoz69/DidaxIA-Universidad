"""
auditoria_sql.py — La escritura de auditoría que comparte transacción (`EQ-023`)
=================================================================================

Una sola redacción del `INSERT` en `auditoria_operacion`, pensada para llamarse
**con un cursor ajeno**, dentro de la transacción de la operación que audita.

Por qué esto y no `PuertoAuditoria.registrar()`
---------------------------------------------------------
Aquel método abre su propia conexión, y ahí está el defecto que el cierre V-B
devolvió. Con dos conexiones, la operación y su constancia se confirman por
separado: si la segunda falla, la primera ya está escrita y `_auditar()` —que
capturaba el error y seguía— informaba éxito. `EQ-023` dice lo contrario:

    «Una operación auditable no puede informar éxito sin auditoría. Abrir o
    cancelar una supresión, consultar conversaciones ajenas y cambiar permisos
    deben persistir operación y auditoría en una misma transacción, o no
    ocurrir.»

`anotar()` recibe el cursor de quien la llama. No abre nada, no captura nada y
no decide nada: si el `INSERT` falla, la excepción sube y la transacción del
llamador se deshace entera. Ésa es toda la garantía, y por eso el módulo es
corto.

`PuertoAuditoria` **sigue existiendo** y sigue teniendo sentido: es el contrato
que el dominio conoce y el que se usa para *consultar* lo registrado. Lo que ya
no se usa es su `registrar()` como forma de auditar una operación que acaba de
ocurrir en otra conexión.

⚠️ Qué NO entra en `detalle`
--------------------------------------
Identificadores y conteos. Nunca texto de conversaciones, correos, nombres ni
frases que la persona escribió. La auditoría se conserva más tiempo que lo que
audita: copiar aquí lo que una supresión tendría que borrar lo dejaría vivo en la
tabla que más sobrevive. Quien llame a `anotar()` es responsable de eso, y hay
pruebas que lo comprueban sobre las operaciones concretas.

⚠️ El orden importa cuando se audita una LECTURA
------------------------------------------------------------
Para una escritura da igual: las dos van en la misma transacción y se deshacen
juntas. Para una lectura hay que anotar **antes** del `SELECT`, de modo que un
fallo de auditoría impida devolver lo leído. Al revés, la conversación ya habría
salido y el registro faltaría.


"""

from __future__ import annotations

import json
from typing import Any

#: El `INSERT`, en un solo sitio. `RETURNING` porque quien audita una operación
#: suele querer devolver su secuencia y su momento en el recibo.
_SQL = """
INSERT INTO auditoria_operacion
    (operacion, actor, sujeto_afectado, detalle, exige_doble_aprobacion, aprobada_por)
VALUES (%s, %s, %s, %s::jsonb, %s, %s)
RETURNING id, momento
"""


def anotar(
    cur: Any,
    operacion: str,
    *,
    actor: str,
    sujeto_afectado: str | None = None,
    detalle: dict | None = None,
    aprobada_por: str | None = None,
) -> tuple[int, Any]:
    """Deja constancia usando el cursor —y la transacción— de quien llama.

    Devuelve `(id, momento)`. No captura ninguna excepción a propósito: que el
    fallo suba **es** el mecanismo por el que la operación auditada no se
    confirma. Un `try` aquí reintroduciría exactamente el `_auditar()`
    best-effort que este módulo sustituye.

    `actor` y `aprobada_por` son claves foráneas a `persona`, así que un sujeto
    que no exista levanta una violación de integridad — y la operación tampoco se
    confirma, que es lo correcto: no se audita a nombre de alguien que el sistema
    no conoce.

    ⚠️ **`exige_doble_aprobacion` se deriva y no se recibe.** La columna existe
    en `auditoria_operacion` y su CHECK ya obliga a que implique `aprobada_por`;
    aceptarla como parámetro sólo habría permitido llamadas que se contradijeran
    —`exige=True` sin aprobador, o un aprobador sin exigencia— y una de las dos
    tendría que ganar en silencio. Si alguien aprobó, la operación lo requería:
    eso es lo que la derivación dice, y no admite discrepancia.
    """
    cur.execute(
        _SQL,
        (
            operacion,
            actor,
            sujeto_afectado,
            json.dumps(detalle or {}),
            aprobada_por is not None,
            aprobada_por,
        ),
    )
    return cur.fetchone()
