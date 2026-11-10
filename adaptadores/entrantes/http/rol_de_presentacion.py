"""
rol_de_presentacion.py — Qué árbol monta el frontend, y quién lo decide
========================================================================

Una sola pregunta: **con qué rol se presenta esta cuenta al abrir sesión**.
Tres respuestas posibles y una prioridad declarada.

Por qué hacía falta, y qué contradicción cierra
------------------------------------------------------
`rol_asignacion` podía tener `investigador_administrador` vigente, las rutas de
`EQ-023` autorizaban con él, y `POST /api/sesion/google` seguía entregando
`estudiante` o `docente`. El resultado era una cuenta que **podía** consultar la
cola de evidencias por API y a la que el frontend nunca le montaba la vista
capaz de hacerlo. La revisión independiente lo devolvió como contradicción, y lo
es: dos partes del mismo sistema respondiendo distinto a «quién es esta persona».

⚠️ Esto NO es un segundo sistema de permisos
--------------------------------------------------------
Y conviene leer por qué antes de tocarlo, porque la tentación de convertirlo en
uno es real.

Aquí no se decide **qué puede hacer** nadie. Las rutas de evidencia siguen
comprobando `rol_asignacion` contra PostgreSQL en cada petición, dentro de la
transacción de la consulta y reteniendo la asignación. Lo que se decide aquí es
**qué pantallas se le ofrecen**, que es una decisión de presentación y por eso
vive en el borde HTTP y no en el dominio.

La consecuencia práctica de esa separación: una sesión abierta como
`investigador` a la que después le revocan el rol **sigue viendo el panel y
recibe 403 en cuanto lo use**. No es un agujero — es lo correcto. La alternativa
sería que el servidor caducara cookies al revocar un rol, que exigiría un canal
de invalidación que nadie ha decidido y que tampoco haría más segura ninguna
API. El permiso efectivo se comprueba donde se ejerce.

Las dos autoridades que se combinan, y ninguna se sustituye
-------------------------------------------------------------------
- **`investigador_administrador`** vive en `rol_asignacion` (`EQ-023`), se
  concede y se retira por una operación auditada, y lo lee el mismo
  `PuertoAsignacionDeRoles` que usa el gobierno de datos. Una sola composición:
  dos adaptadores distintos leyendo la misma tabla acabarían discrepando en
  cuanto uno cambiara de criterio.
- **`docente`** lo sigue decidiendo `RegistroDeDocentes` con los dos mecanismos
  de `D-16` opción C —lista manual del entorno y cola de `solicitud_docente`—.
  **No se toca**, no se duplica y no entra en `dominio/modelo/roles.py`, que
  tiene un solo valor a propósito.

La prioridad, y por qué investigador va primero
--------------------------------------------------------
`investigador` → `docente` → `estudiante`.

Quien es las dos cosas recibe `investigador` porque es el rol **más específico y
el que menos gente tiene**: se concede por una operación explícita y auditada,
mientras que docente puede llegar por una cola de solicitudes. Al revés, una
investigadora que además diera clase entraría siempre en el panel docente y no
tendría forma de llegar al suyo — y el árbol no-estudiante le deja alcanzar las
pantallas de docente igual, así que esta prioridad no le quita nada.

⚠️ Falla cerrado, y «cerrado» aquí significa NO ABRIR SESIÓN
---------------------------------------------------------------------
Si no se puede determinar el rol —sin puerto cableado, sin cadena, base caída—
esto **levanta** y quien llama responde mantenimiento. No degrada a
`estudiante`.

Degradar habría sido cómodo y silencioso: una investigadora entraría un martes
con la base a medias, vería el árbol del estudiante y concluiría que le
retiraron el permiso. Peor todavía en el caso simétrico —un fallo transitorio
durante el login de una docente— porque la persona no tiene forma de distinguir
«el sistema no pudo mirarlo» de «ya no eres eso». `EQ-024` prohíbe el éxito
parcial y una sesión con el rol equivocado lo es.


"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dominio.modelo.roles import Rol, puede_revisar_evidencia
from dominio.puertos.almacen import AlmacenNoConfigurado

if TYPE_CHECKING:  # pragma: no cover
    from adaptadores.entrantes.http.docentes import RegistroDeDocentes
    from dominio.puertos.roles import PuertoAsignacionDeRoles

#: Los tres roles de presentación que el servidor puede declarar. Son los mismos
#: que `frontend/src/nucleo/sesion/rol.js::ROLES` conoce, y esa correspondencia
#: la comprueba una prueba: un cuarto valor aquí sería una vista que el cliente
#: no sabría montar, y el suyo trata lo desconocido como estudiante.
ROL_ESTUDIANTE = "estudiante"
ROL_DOCENTE = "docente"
ROL_INVESTIGADOR = "investigador"

#: La prioridad, escrita como dato para que la prueba la lea y no la repita.
PRIORIDAD = (ROL_INVESTIGADOR, ROL_DOCENTE, ROL_ESTUDIANTE)


def rol_de_presentacion(
    *,
    roles: PuertoAsignacionDeRoles | None,
    registro_docentes: RegistroDeDocentes,
    sujeto_google: str,
    correo: str,
) -> str:
    """El rol con el que se presenta esta cuenta. Ver la cabecera del módulo.

    Todos los parámetros son **por nombre**: son cuatro, dos de ellos cadenas, y
    posicionalmente sería cuestión de tiempo que alguien pasara el correo donde
    va el sujeto — con el efecto de preguntarle a `rol_asignacion` por una clave
    que nunca tendrá y devolver `estudiante` sin fallar.

    `sujeto_google` y `correo` salen los dos del **token de Google ya
    verificado**, nunca del cuerpo de la petición. Esta función no puede
    exigirlo, pero sí puede no ofrecer ninguna vía para lo contrario: no recibe
    la petición ni la sesión, así que quien la llame tiene que traer los dos
    valores de donde los tenga, y `rutas/sesion.py` es el único sitio que la
    llama.

    Levanta `AlmacenNoConfigurado` si no hay puerto de roles cableado, y deja
    subir lo que levante el puerto —`AlmacenNoDisponible` con la base caída—.
    Las dos son `ErrorDeAlmacen`, así que quien llama las trata juntas con un
    solo `except` y no puede olvidarse de una.
    """
    if roles is None:
        # Sin puerto no se puede afirmar que NO tiene el rol; sólo que no se
        # sabe. Devolver `estudiante` aquí sería exactamente la degradación
        # silenciosa que la cabecera descarta, y con la agravante de que un
        # despliegue mal compuesto no daría ninguna señal.
        raise AlmacenNoConfigurado(
            "no hay registro de roles cableado: no se puede determinar el rol "
            "de esta cuenta"
        )
    roles_vigentes = roles.roles_de(sujeto_google)
    if puede_revisar_evidencia(roles_vigentes):
        return ROL_INVESTIGADOR
    if Rol.DOCENTE in roles_vigentes:
        return ROL_DOCENTE
    if registro_docentes.es_docente(correo):
        return ROL_DOCENTE
    return ROL_ESTUDIANTE
