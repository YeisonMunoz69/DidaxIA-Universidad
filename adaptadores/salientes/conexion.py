"""
conexion.py — El plazo de espera de toda conexión a la base · `T-01`, `A4.bis`
================================================================================

Una definición, un sitio. `COMO-TRABAJAMOS.md` §4.bis lo dice sobre los
recuentos y vale igual aquí: *«dos implementaciones de la misma cuenta acaban
discrepando siempre»*. El plazo repetido en veintisiete llamadas sería
veintisiete plazos en cuanto alguien tocara uno.

Por qué hace falta un plazo explícito
----------------------------------------
**El de libpq por defecto es indefinido.** Los tres adaptadores de producción
—`registro/archivo.py`, `registro/postgres.py`,
`recuperacion/indice_postgres.py`— llamaban a `psycopg.connect(cadena)` a
secas, y las pruebas de integración también.

Con una base que **rechaza** la conexión eso no se nota: la excepción es
inmediata. Se nota con una que **acepta TCP y no responde** —un contenedor
pausado, un cortafuegos que descarta, un puerto sin publicar—: entonces la
conexión no lanza, **espera**. Y no hay excepción que suprimir, así que ni el
`contextlib.suppress` de la ruta fría ni el `logging.exception` que `A4` puso
en su lugar dicen nada. `A4` arregla que un fallo sea silencioso; esto arregla
que un fallo sea **indistinguible de un cuelgue**, que es peor.

Se descubrió el 2026-08-18 porque la suite se quedó diez minutos colgada con
`AGENTE_BD` apuntando a un puerto sin publicar. El síntoma era de pruebas; la
causa no.

⚠️ Lo que esto NO arregla, y hay que decirlo
-----------------------------------------------
`AdaptadorTurno.manejar()` se invoca **sin `await` y sin hilo aparte** desde un
manejador `async` (`rutas/turno.py`), así que una conexión que espera **bloquea
el bucle de eventos**: todas las peticiones de todos los usuarios, incluida
`/api/salud`, que es justo la que alguien miraría para saber qué pasa. Esto
convierte esa espera en **acotada** —cinco segundos— en vez de indefinida, que
es una degradación tolerable y no una avería.

Moverlo a un hilo cambia el comportamiento del turno y toca el streaming, así
que **no entra en este bloque**: está reservado como `PM-B38`
(`DECISIONES-PENDIENTES.md` § `N-01`).
"""

from __future__ import annotations

from typing import Any

#: `T-01` del acta del 2026-08-18. Cinco segundos: holgado para la red interna
#: de Docker —donde una conexión sana tarda milisegundos— y corto para que una
#: base inalcanzable no se confunda con una lenta.
PLAZO_DE_CONEXION_S = 5


def conectar(cadena: str) -> Any:
    """Una conexión a la base, con el plazo de `T-01` puesto.

    `psycopg` se importa **dentro** y no en la cabecera, igual que hacían los
    tres adaptadores que ahora llaman aquí: quien no vaya a hablar con la base
    no debería tropezar con su dependencia.
    """
    import psycopg  # noqa: PLC0415

    return psycopg.connect(cadena, connect_timeout=PLAZO_DE_CONEXION_S)
