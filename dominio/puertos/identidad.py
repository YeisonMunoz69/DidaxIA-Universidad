"""
identidad.py — Contrato del almacén de identidad y perfil (`EQ-020`)
======================================================================

Dónde vive hoy lo que este puerto contrata, y por qué se mueve
---------------------------------------------------------------------
La identidad de una persona autenticada vive hoy en tres claves de un `dict` del
almacén de sesiones (`adaptadores/entrantes/http/sesiones.py`), en memoria del
proceso: un reinicio del backend las pierde y no hay ninguna relación persistente
sujeto → perfil. El propio inventario de la Fase 2 lo dejó escrito como brecha.
Este puerto es la frontera de la relación que faltaba.

⚠️ **No sustituye todavía a nada.** Las rutas siguen leyendo y escribiendo el
`dict` de sesión exactamente igual, y el puerto heredado de consentimiento sigue
en su sitio. Conectar el borde es la sesión 3.

Cuatro operaciones, y por qué `registrar()` no es `guardar_perfil()`
---------------------------------------------------------------------------
Los datos de una persona tienen dos procedencias y no se escriben en el mismo
momento ni por la misma razón:

- **`registrar()`** guarda lo que Google confirmó —sujeto, correo, nombre— y se
  llama en cada ingreso. Es idempotente y **no toca** ni un campo declarado: si
  escribiera el perfil entero, volver a entrar borraría la edad y el programa.
- **`declarar_perfil()`** guarda lo que la persona escribió en el onboarding.

Fundirlas en un solo `guardar(perfil)` habría hecho que cada ingreso pisara la
declaración anterior con los valores por defecto del tipo, que es exactamente el
defecto que `EQ-020` no puede permitirse.

Ninguna de las dos es un evento histórico
--------------------------------------------------
`persona` es una fila por titular y se actualiza. Eso **no** contradice la regla
de inmutabilidad: lo inmutable es el consentimiento, el asentimiento y la
evidencia, que viven en sus propias tablas de eventos. Corregir un semestre mal
escrito no es reescribir una decisión.

Los cinco desenlaces
-----------------------
Están en `dominio/puertos/almacen.py`. Aquí sólo importa la consecuencia:
`consultar()` devuelve `None` **únicamente** cuando no hay fila. Un almacén
caído levanta `AlmacenNoDisponible`, y quien llama puede mostrar mantenimiento en
vez de mandar a alguien a repetir un onboarding que ya hizo.


"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from dominio.modelo.identidad import Identidad, PerfilOnboarding


@runtime_checkable
class PuertoIdentidad(Protocol):
    """Lo que el recorrido de `EQ-020` necesita de un almacén de personas."""

    def registrar(self, identidad: Identidad) -> PerfilOnboarding:
        """Deja constancia de la identidad verificada y devuelve el perfil.

        Idempotente: llamarla en cada ingreso actualiza correo y nombre —que
        Google puede haber cambiado— y **conserva** edad, programa, semestre y
        cualquier límite ya fijado.
        """
        ...

    def declarar_perfil(
        self,
        sujeto_google: str,
        *,
        edad: int | None = None,
        facultad: str = "",
        programa: str = "",
        semestre: int | None = None,
        motivo: str = "",
        origen: str = "onboarding_estudiante",
    ) -> PerfilOnboarding:
        """Guarda lo que la persona declaró y devuelve el perfil resultante.

        Mientras no exista una matrícula aprobada, también admite corregir un
        valor ya declarado. La corrección exige motivo y, si toca la edad, deja
        el acto inmutable de rectificación y sus efectos de categoría. Tras la
        vinculación, la rectificación sigue por la vía profesional gobernada.

        Levanta `ReferenciaDesconocida` si el sujeto no está registrado: declarar
        un perfil de alguien que no ha entrado nunca sería crear una identidad
        sin verificar, y `EQ-020` no admite identidades que no vengan de Google.
        """
        ...

    def consultar(self, sujeto_google: str) -> PerfilOnboarding | None:
        """El perfil, o `None` si esa persona no está registrada.

        `None` significa **exactamente** eso. La vinculación a clase se resuelve
        contra el mecanismo de `08-clases.sql`, no contra una columna propia.
        """
        ...

    def fijar_limite_representante(self, sujeto_google: str, limite: datetime) -> None:
        """Guarda la fecha límite de carga de `EQ-016`.

        Sólo la representa. En esta sesión nada la hace cumplir: no hay tarea
        programada que la venza ni bloqueo HTTP que la aplique, y un menor no
        queda habilitado ni antes ni después de ella.
        """
        ...
