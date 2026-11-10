"""
comun.py — Lo que varias familias de rutas necesitan (`PM-B27`)
========================================================================

Tres piezas, y ninguna es «utilidades»: cada una tiene una razón de existir
que se explica sola.

**Una sola definición de cada guarda.** `requerir_rol()` y
`requerir_lista_manual()` los consumen tres familias distintas —clases,
supervisión, rol docente—. Que cada módulo tuviera su copia es exactamente
cómo dos comprobaciones de permiso empiezan a discrepar sin que nadie lo note,
y `PM-B27` repartió las rutas justo después de que la sesión anterior
unificara estos ayudantes: deshacerlo al repartir habría sido una pena.


"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.docentes import RegistroDeDocentes
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones

#: Lo que devuelve una ruta protegida cuando el almacén no responde (`EQ-024`).
#: 503 y no 500: no es un fallo de la petición, es que el servicio no puede
#: atenderla ahora — y quien la reciba debe reintentar, no corregir nada.
#:
#: `Retry-After` va en segundos y es deliberadamente corto: `EQ-024` pide
#: reintento controlado, no un cliente golpeando la base caída.
CODIGO_MANTENIMIENTO = 503
REINTENTAR_EN_SEGUNDOS = 30


async def json_del_cuerpo(peticion: Request) -> dict:
    """El cuerpo, o un diccionario vacío. Un cuerpo ilegible no revienta la ruta."""
    try:
        datos = await peticion.json()
    except Exception:  # noqa: BLE001
        return {}
    return datos if isinstance(datos, dict) else {}


def mantenimiento(detalle: str = "") -> JSONResponse:
    """`EQ-024` · el almacén no responde, y se dice.

    Nunca se devuelve identidad inexistente, consentimiento pendiente ni un éxito
    simulado: las tres cosas serían afirmar algo que no se sabe. El estado
    calculado equivalente es `mantenimiento` (`dominio/modelo/acceso.py`), y esta
    respuesta es su forma HTTP.

    El detalle nunca nombra la base, el anfitrión ni la cadena de conexión: un
    503 se le enseña a cualquiera.
    """
    return JSONResponse(
        {
            "detalle": detalle or "el servicio no está disponible en este momento",
            "estado": "mantenimiento",
        },
        status_code=CODIGO_MANTENIMIENTO,
        headers={"Retry-After": str(REINTENTAR_EN_SEGUNDOS)},
    )


def requerir_sesion(sesiones: Sesiones, peticion: Request) -> tuple[dict | None, JSONResponse | None]:
    """La sesión autenticada de esta petición, o la respuesta que la niega.

    Devuelve `(datos, None)` o `(None, respuesta)`. Dos valores y no una
    excepción porque las rutas de este árbol ya devuelven respuestas construidas
    —`requerir_rol()` lo hace desde `PM-B27`— y mezclar los dos estilos obligaría
    a leer cada ruta para saber cuál usa.

    Desde el hito B1 **no existe sesión sin identidad**, así que esto es la
    frontera del anonimato: una ruta protegida que llame aquí no puede recibir
    una sesión anónima ni aunque alguien encuentre otra vía de crearla.
    """
    datos = sesiones.leer(peticion.cookies.get(COOKIE))
    if datos is None:
        return None, JSONResponse(
            {"detalle": "sin sesión", "estado": "sin_sesion"}, status_code=401
        )
    if not datos.get("identificador_estable"):
        # No puede ocurrir con `Sesiones.abrir()` actual, y por eso se comprueba:
        # si algún día ocurriera, sería porque alguien reintrodujo el anonimato,
        # y esta rama lo convierte en un 401 en vez de en un acceso.
        return None, JSONResponse(
            {"detalle": "sesión sin identidad verificada", "estado": "sin_sesion"},
            status_code=401,
        )
    return datos, None


def requerir_rol(sesiones: Sesiones, peticion: Request, rol: str) -> JSONResponse | None:
    """`None` si puede seguir; si no, la respuesta que hay que devolver ya hecha.

    `RP-17`: la separación por rol se decide **aquí**, en el servidor — no
    basta con que el frontend no muestre el botón, porque las herramientas del
    navegador siguen pudiendo llamar a la ruta directamente.
    """
    datos = sesiones.leer(peticion.cookies.get(COOKIE))
    if datos is None:
        return JSONResponse({"detalle": "sin sesión"}, status_code=401)
    if datos["rol"] != rol:
        return JSONResponse({"detalle": f"esta ruta es de «{rol}»"}, status_code=403)
    return None


def requerir_lista_manual(
    sesiones: Sesiones, registro_docentes: RegistroDeDocentes, peticion: Request
) -> JSONResponse | None:
    """Quién puede resolver una solicitud de rol docente: **solo quien ya
    está en la lista a mano** — `docentes.py` lo explica.

    NO es `requerir_rol(sesiones, peticion, "docente")`: una cuenta que
    llegó a `docente` por la cola de aprobación no hereda permiso para
    resolver la cola de otros. Son dos preguntas distintas —«qué rol tiene
    esta sesión» frente a «este correo está en la lista a mano»— y esta
    ruta necesita la segunda, no la primera.
    """
    datos = sesiones.leer(peticion.cookies.get(COOKIE))
    if datos is None:
        return JSONResponse({"detalle": "sin sesión"}, status_code=401)
    correo = datos.get("correo") or ""
    if not registro_docentes.es_de_la_lista_manual(correo):
        return JSONResponse(
            {"detalle": "solo quien está en la lista a mano puede resolver solicitudes"},
            status_code=403,
        )
    return None
