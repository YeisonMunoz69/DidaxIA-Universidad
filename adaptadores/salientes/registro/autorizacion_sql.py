"""
autorizacion_sql.py — La comprobación de rol que comparte transacción y bloquea
================================================================================

Una sola redacción de «¿tiene esta persona el rol de `EQ-023` **ahora**?»,
pensada para llamarse **con un cursor ajeno**, dentro de la misma transacción de
la operación que autoriza. Es el hermano de `auditoria_sql.py`: mismo patrón,
mismo motivo, otra mitad del mismo invariante.

Qué encontró la revisión R7-B
--------------------------------------
Dos defectos distintos, y el primero era grave:

1. **`AdaptadorRolesPostgres.asignar()` y `revocar()` no comprobaban nada.** La
   ruta HTTP miraba el rol del actor antes de abrir la transacción, y el
   repositorio se fiaba. Reproducido contra PostgreSQL: un sujeto registrado con
   el conjunto de roles **vacío** llamó al adaptador directamente y el tercero
   terminó con `investigador_administrador`. Una comprobación que sólo vive en la
   ruta no es una regla del sistema: es una cortesía del borde, y basta con
   llamar al repositorio desde otro sitio —una tarea, un guion de operación, la
   ruta siguiente que alguien escriba— para saltársela.

2. **Las tres comprobaciones que sí existían leían sin bloquear.**
   `gobierno_db.py` y `menores_db.py` leían `rol_asignacion` con un `SELECT`
   normal. Entre esa lectura y el efecto protegido cabe una revocación
   concurrente que se confirma: la operación quedaría autorizada por un permiso
   que ya no existe cuando se aplica.

Y un tercero de forma: **tres implementaciones de la misma pregunta**, con dos
redacciones del SQL y dos mensajes distintos. Tres copias de una regla son tres
reglas en cuanto alguien corrige una.

Por qué `FOR SHARE` y no `FOR UPDATE`
-----------------------------------------------
Lo que hace falta es **retener** la asignación mientras dura la operación, no
modificarla. `FOR SHARE` es exactamente eso:

- **basta para lo que se protege** · una revocación es un `UPDATE` sobre esa
  fila, y `UPDATE` necesita `FOR UPDATE`, que es incompatible con `FOR SHARE`.
  Así que mientras esta transacción viva, ninguna revocación de esa asignación
  puede confirmarse: espera, o cae por `lock_timeout`;
- **no serializa a los administradores entre sí** · dos investigadores que
  aprueban cosas distintas a la vez comparten el bloqueo de sus propias filas y
  no se estorban. Con `FOR UPDATE` cada uno esperaría al otro sin motivo, y la
  cola de aprobaciones se volvería estrictamente secuencial;
- **es el mismo nivel que `exigir_version_requerida()`** ya usa para retener una
  versión de consentimiento mientras se escribe el acto que la cita. La misma
  necesidad merece el mismo lock, y no dos criterios.

⚠️ **Sin rol vigente no hay fila que bloquear, y no es un hueco.** Quien no tiene
el rol es rechazado aquí mismo; no hay operación protegida que proteger. El caso
que importa —tenerlo y perderlo a mitad— sí tiene fila, y sí queda retenida.

⚠️ **Dos administradores revocándose a la vez pueden interbloquearse.** Cada uno
retiene su propia asignación y quiere modificar la del otro; PostgreSQL detecta
el ciclo y aborta una de las dos transacciones (`40P01`), que sube traducida como
indisponibilidad. Es el desenlace correcto —ninguna de las dos se aplica a
medias— y es preferible a la alternativa, que es no bloquear y dejar que la
autorización y el efecto se separen. Se declara aquí en vez de descubrirse.


"""

from __future__ import annotations

from typing import Any

from dominio.modelo.roles import Rol, puede_revisar_evidencia
from dominio.puertos.almacen import EscrituraRechazada

#: La consulta, en un solo sitio. `FOR SHARE` retiene las asignaciones vigentes
#: de ese sujeto durante toda la transacción de quien llama — ver la cabecera.
_SQL_ROLES_VIGENTES = """
SELECT rol FROM rol_asignacion
 WHERE sujeto_google = %s AND revocado_en IS NULL
 FOR SHARE
"""

#: El motivo del rechazo, con una sola redacción. Antes había dos, y una consulta
#: de auditoría que buscara la primera no habría encontrado la mitad de los casos.
MOTIVO_SIN_ROL = "esta operación la reserva EQ-023 a un investigador administrador vigente"

# Predicado del directorio de destinatarios docentes. El alias p pertenece a
# las consultas del repositorio; no recibe nombres ni SQL del cliente.
DOCENTE_VIGENTE_SQL = (
    "EXISTS (SELECT 1 FROM rol_asignacion ra WHERE ra.sujeto_google=p.sujeto_google "
    "AND ra.rol='docente' AND ra.revocado_en IS NULL)"
)

#: El motivo cuando alguien se nombra a sí mismo. Separado del anterior a
#: propósito: quien lo recibe **sí** tiene el rol, y decirle que no lo tiene sería
#: falso y le haría buscar el problema donde no está.
MOTIVO_SOBRE_SI_MISMO = "nadie puede otorgarse ni retirarse un rol a sí mismo (EQ-023)"


def roles_vigentes_bloqueados(cur: Any, sujeto: str) -> frozenset[Rol]:
    """Los roles vigentes de ese sujeto, **reteniéndolos** hasta el commit.

    Recibe el cursor de quien llama y no abre nada: la lectura tiene que ocurrir
    en la misma transacción que el efecto, o el permiso que se comprueba y el que
    rige al aplicar pueden ser distintos.
    """
    cur.execute(_SQL_ROLES_VIGENTES, (sujeto,))
    return frozenset(Rol(fila[0]) for fila in cur.fetchall())


def exigir_investigador_administrador(cur: Any, actor: str) -> None:
    """Que el actor tenga el rol de `EQ-023` **ahora, aquí dentro y retenido**.

    La regla la decide el dominio —`puede_revisar_evidencia()`—, nunca un correo
    ni el rol que traiga la sesión; este módulo sólo lee las asignaciones y
    sostiene el bloqueo. Levanta `EscrituraRechazada` si no lo tiene, de modo que
    la transacción de quien llama se deshaga entera: sin rol no hay efecto y
    tampoco hay auditoría de un efecto que no ocurrió.
    """
    if not puede_revisar_evidencia(roles_vigentes_bloqueados(cur, actor)):
        raise EscrituraRechazada(MOTIVO_SIN_ROL)


def exigir_actor_distinto(actor: str, sujeto: str) -> None:
    """Que nadie se otorgue ni se retire un rol a sí mismo (`EQ-023`).

    Vive en el repositorio y no sólo en la ruta por el mismo motivo que la
    comprobación de rol: una regla que sólo aplica el borde se salta llamando al
    repositorio desde otro sitio. La ruta conserva la suya para poder responder
    409 con motivo antes de abrir una transacción, y las dos dicen lo mismo.

    Un administrador que se retirara el rol podría dejar el sistema sin ninguno,
    y recuperarlo exigiría volver a la base a mano.
    """
    if actor == sujeto:
        raise EscrituraRechazada(MOTIVO_SOBRE_SI_MISMO)
