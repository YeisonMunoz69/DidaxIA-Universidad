"""
Registro de rol docente · DD-18 · D-16 opción C · PM-B15 B
================================================================

Quién es docente, cuando Google no lo dice.

Google confirma que una cuenta es del dominio institucional (identidad); no
dice qué papel tiene esa persona dentro de la institución (rol) — dentro del
mismo dominio no hay una señal fiable y accesible sin permisos de
administrador de Workspace. `DD-18` ya fijó el principio —«el servidor
decide el rol con sus propios registros»— y `D-16` opción C
(`DECISIONES-PENDIENTES.md`) fijó de dónde salen esos registros: **dos
mecanismos que alimentan el mismo registro**, no dos registros distintos.

LISTA A MANO, para arrancar
--------------------------------
`DOCENTES_AUTORIZADOS`: correos separados por coma, leída al construir el
registro. Basta para el piloto, donde se sabe quiénes son las docentes — no hace
falta pantalla ni ruta para esto, es configuración.

⚠️ **Y es fail-closed desde el hito R7-C: sin variable, la lista está vacía.**
Antes traía cuatro correos institucionales como valor por defecto y volvía a
añadir tres a mano después de leerla, de modo que `DOCENTES_AUTORIZADOS=""` —la
forma de decir «nadie»— dejaba entrar igual a tres cuentas. **Ya no hay ninguna
cuenta docente de prueba por defecto**, ni aquí ni en ningún otro módulo: quien
deba entrar por esta vía se escribe en la variable.

Y la comparación es **exacta** tras normalizar espacios y mayúsculas. No se
quitan puntos ni se inventan equivalencias entre direcciones: dos alias que deban
autorizarse van los dos escritos en la variable. El porqué está en
`RegistroDeDocentes.es_de_la_lista_manual()`.

COLA DE SOLICITUD Y APROBACIÓN, para cuando crezca
-------------------------------------------------------
Cualquier cuenta autenticada del dominio institucional que no esté en la
lista a mano puede PEDIR el rol. Tres acciones DISTINTAS sobre una
solicitud —aprobar, rechazar, pedir más información—, la misma regla que
`RU-12` ya aplica a la cola de supervisión: nunca «aprobar todo».

Quién puede resolver una solicitud, hoy: **quien ya esté en la lista a
mano.** No es un tercer rol nuevo — es la misma lista de arriba, reusada. Una
cuenta que llegó a docente por la cola no hereda permiso para resolver la
cola de otros; se hace así explícitamente para no inventar una jerarquía de
permisos que nadie decidió.

Una sola mitad tiene almacén, y desde la Fase 2 · sesión 3 tiene contrato
------------------------------------------------------------------------------
La lista a mano no persiste nada: se lee del entorno. La cola sí, y hasta la
sesión 3 esta clase llevaba **dos implementaciones de esa mitad dentro**: un
`dict` en memoria escrito a mano y, detrás de `if self._adaptador is not
None`, la delegación al de PostgreSQL. Ahora hay un solo camino —siempre se
delega en un `PuertoSolicitudesDocentes`
(`dominio/puertos/rol_docente.py`)— y quien compone decide cuál construir:
`AdaptadorSolicitudesDocentesMemoria` o
`AdaptadorSolicitudesDocentesPostgres`. El comportamiento observable no
cambió; lo que desapareció es la segunda copia.

Qué NO resuelve este módulo, declarado y no escondido
-----------------------------------------------------------
**Una solicitud rechazada dos veces o abandonada.** No hay límite de
reintentos hoy: la persona puede volver a pedirlo tantas veces como quiera y
quien modera la vuelve a ver en la cola. Un tope o un enfriamiento es una
decisión de producto que nadie ha tomado; se declara aquí en vez de
inventarla con código.



"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from adaptadores.salientes.registro.solicitudes_docente_memoria import (
    AdaptadorSolicitudesDocentesMemoria,
)
from dominio.puertos.rol_docente import (
    ESTADO_APROBADA,
    ESTADO_PENDIENTE,
    ESTADO_RECHAZADA,
    Solicitud,
)

if TYPE_CHECKING:  # pragma: no cover
    from dominio.puertos.rol_docente import PuertoSolicitudesDocentes

__all__ = [
    "ESTADO_APROBADA",
    "ESTADO_PENDIENTE",
    "ESTADO_RECHAZADA",
    "VARIABLE_LISTA_MANUAL",
    "RegistroDeDocentes",
    "Solicitud",
]


#: El nombre de la variable, en un solo sitio. Se lee **al construir** cada
#: registro y no al importar el módulo: una constante resuelta en el import haría
#: que la lista dependiera del orden de importación y no de la configuración
#: vigente del proceso —la misma lección que `base_postgres.py` recoge de la
#: Fase 2 · sesión 3—.
VARIABLE_LISTA_MANUAL = "DOCENTES_AUTORIZADOS"


def _normalizar(correo: str) -> str:
    """Lo **único** que se le hace a un correo antes de compararlo: quitarle los
    espacios de los extremos y bajarlo a minúsculas.

    Dos operaciones, y ninguna más. Ver `_lista_manual()` para por qué la lista
    de lo que no se hace importa tanto como ésta.
    """
    return (correo or "").strip().lower()


def _lista_manual() -> frozenset[str]:
    """Los correos de `DOCENTES_AUTORIZADOS`, y **nada más** (hito R7-C).

    ⚠️ Aquí había cuatro correos institucionales escritos como valor por defecto,
    y tres de ellos se volvían a añadir a mano después de leer la variable. Las
    consecuencias que midió la revisión:

    - con `DOCENTES_AUTORIZADOS=""` —la variable puesta y vacía, que es como se
      dice «nadie»— `es_docente()` seguía devolviendo `True` para tres cuentas.
      La lista no se podía vaciar: los `add()` de después la reponían;
    - un despliegue que no definiera la variable autorizaba a cuatro cuentas que
      nadie había configurado allí.

    Ahora **ausente y vacía significan lo mismo: la lista manual está vacía**.
    Quien deba entrar por esta vía se escribe en la variable, que es lo que
    `D-16` opción C decidió. No hay lista alternativa para desarrollo y no debe
    haberla: sería este mismo defecto con otro nombre.

    Se devuelve un `frozenset` porque la lista de quién es docente no es algo que
    el registro deba poder modificar después de construirse.
    """
    correos = os.environ.get(VARIABLE_LISTA_MANUAL, "")
    return frozenset(
        normalizado for c in correos.split(",") if (normalizado := _normalizar(c))
    )


class RegistroDeDocentes:
    """El registro que `D-16` opción C describe: un almacén, dos mecanismos.

    La lista a mano SIEMPRE vive en la variable de entorno, y **sólo** ahí
    (hito R7-C): se lee al construir cada registro, de modo que una instancia
    nueva ve la configuración vigente de su proceso. La
    cola de solicitudes vive en el `PuertoSolicitudesDocentes` que se reciba;
    sin ninguno, en `AdaptadorSolicitudesDocentesMemoria`, que es lo que este
    archivo hacía a mano hasta la Fase 2 · sesión 3.

    Los cinco métodos de abajo son la única frontera entre las dos mitades:
    nada más en esta clase pregunta por el adaptador.
    """

    def __init__(self, adaptador_solicitudes: PuertoSolicitudesDocentes | None = None) -> None:
        self._manual = _lista_manual()
        self._adaptador: PuertoSolicitudesDocentes = (
            adaptador_solicitudes
            if adaptador_solicitudes is not None
            else AdaptadorSolicitudesDocentesMemoria()
        )

    def es_de_la_lista_manual(self, correo: str) -> bool:
        """La única fuente de verdad de QUIÉN PUEDE RESOLVER una solicitud —
        no «es docente» en general, que también lo son quienes llegaron por
        la cola. Confundir las dos crearía un tercer rol sin que nadie lo
        decidiera; ver la cabecera del módulo.

        ⚠️ **La comparación es exacta tras normalizar** (hito R7-C). Aquí había
        un segundo intento que comparaba los correos **sin sus puntos**, con el
        argumento de que un alias con punto y otro sin él son la misma cuenta en
        Google Workspace. Sea o no cierto para un dominio concreto, el efecto
        medido es que una lista con `nombre.apellido@` autorizaba **también** a
        `nombreapellido@`: una dirección que nadie escribió en la lista y que
        puede pertenecer a otra persona.

        Un sistema de autorización no puede inventar equivalencias entre
        identidades. Si dos alias institucionales deben entrar, los dos se
        escriben en `DOCENTES_AUTORIZADOS` — cuesta una coma y no adivina nada.
        """
        return _normalizar(correo) in self._manual

    def es_docente(self, correo: str) -> bool:
        """Lo que abrir una sesión necesita: lista a mano **o** solicitud
        aprobada. Los dos mecanismos de `D-16` C alimentan este único
        método."""
        correo_norm = _normalizar(correo)
        if self.es_de_la_lista_manual(correo_norm):
            return True
        return self._adaptador.aprobada(correo_norm)

    def solicitar(self, correo: str) -> Solicitud:
        """Reutiliza la solicitud pendiente si ya existe una — pedirlo dos
        veces seguidas no duplica la cola. Una solicitud rechazada SÍ puede
        volver a pedirse: es la política de «sin límite de reintentos» del
        docstring del módulo, hecha código, y crea una solicitud nueva."""
        return self._adaptador.solicitar(_normalizar(correo))

    def listar_pendientes(self) -> list[Solicitud]:
        return self._adaptador.listar_pendientes()

    def aprobar(self, identificador: str) -> bool:
        return self._adaptador.aprobar(identificador)

    def rechazar(self, identificador: str, motivo: str) -> bool:
        """Sin motivo no se llama a esto — igual que `ColaDeRevision.rechazar()`,
        la validación de que el motivo no esté vacío es del borde, no de
        este almacén."""
        return self._adaptador.rechazar(identificador, motivo)

    def pedir_mas_informacion(self, identificador: str, mensaje: str) -> bool:
        """La tercera acción, distinta de aprobar y de rechazar: la
        solicitud SIGUE pendiente —no se resuelve—, solo gana una nota
        visible para quien la pidió. Es lo que hace posible «sin límite de
        reintentos» sin escribir código de reintento: por esta vía la
        solicitud nunca sale de la cola."""
        return self._adaptador.pedir_mas_informacion(identificador, mensaje)
