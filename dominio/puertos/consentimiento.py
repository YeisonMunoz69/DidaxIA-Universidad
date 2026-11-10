"""
consentimiento.py — Contrato de lectura y escritura del consentimiento
============================================================================

El puerto que comparten el adaptador de PostgreSQL
(`adaptadores/salientes/registro/consentimiento_db.py`) y el degradado que
ocupa su lugar cuando no hay base
(`adaptadores/salientes/registro/consentimiento_degradado.py`).

⚠️ Esta sesión NO decide la política de consentimiento
--------------------------------------------------------------
`EQ-016` y la Fase 3 se ocupan de quién debe consentir, de la edad mínima, del
representante de un menor, de la revocación y de si una sesión anónima puede
persistir. **Nada de eso se resuelve aquí.** Este puerto describe el acceso al
almacén tal y como ya existía: dos operaciones, las mismas formas de entrada y
de retorno, los mismos estados.

En particular se conserva, sin tocarlo:

- que `decision` es la cadena que el borde ya validó (`otorgado`/`rechazado`);
- que la clave de escritura es `identificador_sujeto` si lo hay y el correo si
  no —lo que `ON CONFLICT` de `07-consentimiento-usuario.sql` necesita—;
- que `consultar()` devuelve un `dict` con `decision` y `edad`, o `None`
  cuando no hay fila, no hay base o el almacén falla.

Cambiar cualquiera de esas tres cosas es una decisión de la Fase 3, no una
consolidación de contrato.

Por qué un puerto y no dos funciones de módulo
------------------------------------------------------
Hasta la Fase 2 · sesión 3 el acceso eran dos funciones que resolvían la
cadena de conexión desde `AGENTE_BD` **capturada al importar el módulo**:
`_CADENA_BD_DEFECTO = os.getenv("AGENTE_BD", "")`. La ruta de sesión las
llamaba directamente. Eso hacía que la autoridad sobre a qué base se escribe
dependiera del orden de importación y no de la composición, y que la ruta no
tuviera forma de recibir otra implementación. Ahora la composición decide y la
ruta recibe la dependencia.


"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PuertoConsentimiento(Protocol):
    """Las dos operaciones que `rutas/sesion.py` consume, y nada más."""

    def guardar(
        self,
        identificador_sujeto: str,
        correo: str,
        decision: str,
        edad: int | None = None,
    ) -> None:
        """Guarda o actualiza la decisión del titular.

        Sin `identificador_sujeto` **ni** correo no hay titular del que colgar
        la fila y no se escribe nada. No devuelve nada ni levanta: un fallo del
        almacén no puede tumbar la respuesta de la ruta, que es el
        comportamiento que ya tenía.
        """
        ...

    def consultar(self, identificador_sujeto: str, correo: str = "") -> dict | None:
        """`{"decision": ..., "edad": ...}` de la fila más reciente, o `None`.

        `None` cubre tres situaciones distintas a propósito —no hay titular, no
        hay fila, el almacén no responde—: quien llama trata las tres igual, y
        distinguirlas cambiaría el estado que ve el cliente.
        """
        ...
