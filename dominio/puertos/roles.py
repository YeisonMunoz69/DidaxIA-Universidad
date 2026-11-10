"""
roles.py — Contrato de las funciones profesionales persistentes (`EQ-023`)
===========================================================================

⚠️ **Relación con el sistema de roles que ya existe, antes que nada.**

`estudiante` no se almacena como rol: es la experiencia base. La compatibilidad
con docentes anteriores sigue en `adaptadores/entrantes/http/docentes.py`, que
combina la lista manual y `solicitud_docente`. Desde la migración 22, las altas
nuevas de docente y de investigador comparten este puerto persistente y
auditado.

Lo que este puerto añade es el rol que `EQ-023` crea y que hoy **no existe en
ningún sitio**: sin él, «un investigador autorizado verifica la evidencia» no se
puede comprobar, y la única alternativa habría sido comparar correos dentro del
dominio — que el encargo prohíbe.

Por qué la revocación no borra
--------------------------------------
`revocar()` pone fecha, no `DELETE`. Un permiso retirado tiene que seguir
explicando por qué alguien pudo aprobar una autorización el mes pasado; borrar la
fila dejaría esa aprobación sin respaldo. Es la misma disciplina que `EQ-022`
aplica al consentimiento: revocar bloquea, no borra.


"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dominio.modelo.roles import AsignacionDeRol, Rol


@runtime_checkable
class PuertoAsignacionDeRoles(Protocol):
    """Asignación, revocación y directorio de funciones profesionales."""

    def asignar(
        self, sujeto_google: str, rol: Rol, otorgado_por: str | None = None
    ) -> AsignacionDeRol:
        """Otorga el rol y devuelve la asignación creada.

        Levanta `EscrituraRechazada` si ya hay una asignación vigente de ese rol
        para esa persona —otorgar dos veces no es una decisión nueva— y
        `ReferenciaDesconocida` si el sujeto, o quien lo otorga, no está
        registrado como persona.

        ⚠️ **Con `otorgado_por`, quien otorga tiene que tener el rol vigente**
        (hito R7-B), y la implementación lo comprueba **dentro de la transacción
        que aplica el cambio**, no en quien la llama. Un actor sin rol, o que se
        nombre a sí mismo, levanta `EscrituraRechazada` y nada se escribe.
        Comprobarlo sólo en la ruta no era una regla del sistema: bastaba llamar
        al repositorio desde otro sitio para saltársela, y la revisión lo hizo.

        `otorgado_por = None` es el **bootstrap** operativo: la primera asignación
        del sistema, que ningún investigador puede otorgar porque todavía no hay
        ninguno. No se audita —no hay actor— y **ninguna ruta HTTP la ofrece**.
        """
        ...

    def revocar(self, sujeto_google: str, rol: Rol, revocado_por: str) -> bool:
        """Cierra la asignación vigente. `False` si no había ninguna.

        `revocado_por` es obligatorio: `EQ-023` audita cada cambio de permisos, y
        una revocación sin autor deja sin explicar por qué alguien pudo aprobar
        una autorización el mes pasado y hoy no. Levanta `ReferenciaDesconocida`
        si quien revoca no está registrado como persona.

        ⚠️ **Y tiene que tener el rol vigente**, con la misma disciplina que
        `asignar()` (hito R7-B): estar registrado como persona nunca fue un
        permiso. Aquí no hay bootstrap y no puede haberlo — revocar presupone que
        alguien ya tenía el rol, así que siempre hay a quién exigírselo.

        Conserva la fila con su fecha y su autor; nunca borra.
        """
        ...

    def roles_de(self, sujeto_google: str) -> frozenset[Rol]:
        """Los roles vigentes. Conjunto vacío para quien no tiene ninguno, que
        es lo normal y no un error: no levanta ni devuelve `None`."""
        ...

    def asignaciones(self, sujeto_google: str) -> tuple[AsignacionDeRol, ...]:
        """El historial completo, vigentes y revocadas, de la más antigua a la
        más reciente. Es lo que hace auditable una aprobación pasada."""
        ...

    def directorio_institucional(
        self, investigador: str, filtro: str = "", pertenencia: str = "todas",
        clase: str = "",
    ) -> list[dict]:
        """Directorio profesional autorizado y auditado para investigación."""
        ...

    def asignar_facultad_profesional(
        self, investigador: str, sujeto: str, facultad: str
    ) -> dict | None:
        """Actualiza la facultad de una cuenta docente o devuelve ``None``."""
        ...
