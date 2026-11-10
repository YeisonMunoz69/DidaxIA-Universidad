"""
puerta_de_supresion.py — Una sola puerta para todo el producto (`EQ-022`)
==========================================================================

`ESTADO-ACTUAL.md` §10.2 y la tabla de estados aprobada dicen lo mismo: mientras
haya un trámite de supresión abierto, la cuenta **consulta y cancela**, no usa el
producto ni aporta datos nuevos. `f95fa28` lo aplicó a
`POST /api/consentimiento/decision-conjunta`; esto lo cierra en el resto.

Qué es y qué no es
------------------------
Es **un objeto que se compone y se pasa** a las familias de rutas que lo
necesitan, construido sobre el `PuertoEstadoVigente` que ya existía. No es:

- **un middleware con una lista de rutas en texto** — una ruta nueva quedaría
  sin cubrir en silencio, que es exactamente cómo apareció este hallazgo;
- **estado global** — dos pruebas en el mismo proceso se pisarían;
- **una conexión propia a PostgreSQL** — ya hay un puerto que responde esto, y
  una segunda consulta sería una segunda redacción de la misma regla;
- **una copia del SQL por router** — la consulta vive en `base_postgres.py`.

Para qué sirve, si la persistencia ya comprueba
----------------------------------------------------------
Las dos capas cubren cosas distintas y las dos hacen falta:

| | la puerta HTTP | `exigir_sin_supresion()` en la transacción |
|---|---|---|
| **cuándo** | antes de leer el cuerpo o el archivo | con la fila bloqueada |
| **cubre** | acciones sin escritura personal —turno, rol, supervisión— | la carrera con una supresión que se abre a mitad |
| **con adaptadores en memoria** | sí | no los hay |
| **si falla** | 409 uniforme | rechazo del almacén, cero filas |

La puerta responde **antes de leer el cuerpo**, y eso importa en la carga de
evidencia: sin ella, un PDF de diez megas se transfiere, se valida y se reserva
en almacenamiento privado para acabar rechazado — y esa reserva hay que
compensarla. Lo que no se recibe no hay que compensarlo.

Lo que la puerta NO decide
-----------------------------------
Quién es quien llama y qué rol tiene. Eso es de `requerir_sesion()` y
`requerir_rol()`, y va **antes**: la supresión de una cuenta no es motivo para
saltarse la autenticación, y un 409 a quien no ha iniciado sesión revelaría que
esa cuenta existe. El orden es identidad → rol → supresión → producto.


"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import mantenimiento
from dominio.puertos.almacen import AlmacenNoConfigurado, AlmacenNoDisponible

if TYPE_CHECKING:  # pragma: no cover
    from dominio.puertos.estado_vigente import PuertoEstadoVigente

#: Dónde se consulta y se cancela el trámite. Se nombra en cada rechazo: un «no
#: puedes» a secas deja a quien lo lee sin saber qué sí puede, y aquí lo que
#: puede es consultarlo y cancelarlo dentro del plazo.
RUTA_DEL_TRAMITE = "/api/datos/supresion"

#: El estado que publica la respuesta. Estable y explícito, para que el cliente
#: lo distinga de los demás `409` sin comparar mensajes de texto.
ESTADO = "eliminacion_solicitada"


def respuesta_de_supresion(detalle: str = "") -> JSONResponse:
    """El `409` uniforme de toda operación suspendida por el trámite.

    Una función y no un literal repetido en cada router: nueve familias
    devolviendo su propia versión habrían acabado con nueve contratos, y el
    cliente distingue este caso **por el campo `estado`**.

    El cuerpo no lleva sujeto, correo ni fechas del trámite: un `409` se le
    enseña a cualquiera que mire una consola, y quien necesite esos datos los
    pide por `RUTA_DEL_TRAMITE` con su sesión.
    """
    return JSONResponse(
        {
            "detalle": detalle
            or (
                "tienes una solicitud de eliminación en curso: mientras dure no "
                "se registra ningún dato nuevo ni se puede usar el tutor"
            ),
            "estado": ESTADO,
            "usar": RUTA_DEL_TRAMITE,
        },
        status_code=409,
    )


class PuertaDeSupresion:
    """Responde una sola pregunta: ¿esta cuenta tiene el trámite abierto?

    Se construye una vez en la composición y se pasa a las familias de rutas.
    Guarda el puerto y nada más: sin caché, porque el trámite puede abrirse entre
    dos peticiones de la misma sesión y una respuesta memorizada dejaría pasar
    justo la siguiente.
    """

    def __init__(self, estado_vigente: PuertoEstadoVigente | None) -> None:
        self._estado_vigente = estado_vigente

    def negativa(self, sujeto_google: str) -> JSONResponse | None:
        """`None` si la operación puede seguir; si no, la respuesta que la niega.

        Tres desenlaces, y ninguno se confunde con otro:

        - **`None`** · no hay trámite abierto —o la persona no está registrada,
          que es un caso que la ruta ya trata por su cuenta—;
        - **`409`** · lo hay. Cero efectos, y se dice dónde consultarlo;
        - **`503`** · no se sabe. `EQ-024` prohíbe afirmar lo que no se sabe, así
          que **no se deja pasar**: una base caída no puede convertirse en
          permiso para escribir sobre quien pidió el borrado.

        Sin puerto tampoco se deja pasar. Es la misma regla que
        `rutas/turno.py` aplica desde B3: «no puedo comprobarlo» no se resuelve
        dejando entrar.
        """
        if self._estado_vigente is None:
            return mantenimiento(
                "no se puede comprobar el estado de tu cuenta en este momento"
            )
        try:
            estado = self._estado_vigente.estado_vigente(sujeto_google)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento(
                "no se puede comprobar el estado de tu cuenta en este momento"
            )
        if estado is None:
            # No hay fila de identidad. No es asunto de esta puerta: la ruta que
            # llama ya decide qué hacer con alguien sin registrar, y responder
            # aquí un 409 sugeriría un trámite que no existe.
            return None
        if estado.eliminacion_solicitada:
            return respuesta_de_supresion()
        return None
