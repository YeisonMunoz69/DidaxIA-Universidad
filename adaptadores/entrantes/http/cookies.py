"""
cookies.py — Los atributos de la cookie de sesión, en un solo sitio (`B1`)
===========================================================================

Hasta el hito B1 los cinco `set_cookie()` de `rutas/sesion.py` repetían sus
atributos a mano. Cinco copias de una decisión de seguridad son cinco decisiones
en cuanto alguien corrige una: la sexta ruta que se añadiera olvidaría `httponly`
y nadie lo notaría hasta que un guion de la página leyera la cookie.

`Secure` depende del entorno, y por qué
--------------------------------------------------
`Secure` le dice al navegador que no mande la cookie por HTTP en claro. En
producción es obligatorio. En el desarrollo local del equipo —`http://localhost`,
sin TLS— una cookie `Secure` **no se envía nunca**, así que ponerla siempre
rompería el inicio de sesión en el único entorno donde hoy se prueba a mano.

Se decide con `AGENTE_ENTORNO`, que es la variable que el proyecto ya usa para
distinguir entornos (`compose.produccion.yaml` publica `produccion`; la barrera
de pruebas de la Fase 2 exige `pruebas`). No se inventa una variable nueva ni se
adivina por el esquema de la petición: un proxy inverso mal configurado haría que
esa deducción diera `http` y desactivara la protección justo donde hace falta.

⚠️ **El valor por defecto es el seguro.** Un entorno que no se declara se trata
como productivo: si alguien despliega sin definir `AGENTE_ENTORNO`, la cookie
sale `Secure`. Equivocarse hacia «no funciona en local» cuesta un mensaje;
equivocarse hacia «viaja en claro» cuesta la sesión de una persona.

`SameSite=Lax` y no `Strict`
------------------------------------
`Lax` deja que la cookie viaje cuando alguien **navega** al sitio desde fuera
—volver desde la pantalla de Google, abrir un enlace del correo institucional—,
y la retiene en peticiones de terceros. `Strict` la retendría también al volver
de Google, y el recorrido de `EQ-020` se quedaría a medias sin explicación.


"""

from __future__ import annotations

import os
from typing import Any

#: La variable que el proyecto ya usa para distinguir entornos. No se inventa
#: otra: `compose.produccion.yaml` publica `produccion` y la barrera de pruebas
#: de la Fase 2 · sesión 2A exige `pruebas`.
VARIABLE_ENTORNO = "AGENTE_ENTORNO"

#: Los entornos donde la cookie puede viajar sin `Secure`, porque no hay TLS y
#: exigirlo impediría iniciar sesión. Lista cerrada: cualquier otro valor —y la
#: ausencia de valor— se trata como productivo.
ENTORNOS_SIN_TLS = frozenset(
    {"desarrollo", "local", "pruebas", "demostracion", "produccion-local"}
)

#: Cuánto vive la cookie en el navegador. Los siete días de `EQ-020`, los mismos
#: que `sesiones.TTL_SESION_SEGUNDOS`: si el navegador la conservara más, la
#: persona vería una sesión que el servidor ya retiró.
DURACION_SEGUNDOS = 7 * 24 * 60 * 60


def entorno_sin_tls(entorno: str | None = None) -> bool:
    """Si este entorno sirve sin TLS y por tanto no puede exigir `Secure`.

    Se lee en cada llamada y no al importar, para que una prueba pueda ejercitar
    los dos caminos sin recargar el módulo — la misma disciplina que
    `aviso_legal.modo_piloto()`.
    """
    valor = (os.environ.get(VARIABLE_ENTORNO, "") if entorno is None else entorno)
    return valor.strip().lower() in ENTORNOS_SIN_TLS


def atributos(entorno: str | None = None) -> dict[str, Any]:
    """Los atributos con los que se escribe y se borra la cookie de sesión.

    `httponly` no es configurable y no debe serlo: es la mitad del motivo de usar
    cookie y no `localStorage`, y `EQ-020` no admite que el testigo de sesión
    quede al alcance de un guion de la página.
    """
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": not entorno_sin_tls(entorno),
        "path": "/",
    }


def atributos_de_borrado(entorno: str | None = None) -> dict[str, Any]:
    """Los mismos atributos, sin `max_age`, para `delete_cookie()`.

    Tienen que coincidir con los de escritura: un navegador no borra una cookie
    si el `path`, el `samesite` o el `secure` no son los que tenía. Cerrar sesión
    dejando la cookie viva es exactamente el fallo que `EQ-024` no admite.
    """
    return atributos(entorno)
