"""
almacen.py — Los cinco desenlaces que un almacén de la Fase 3 debe distinguir
==============================================================================

Un solo sitio para las excepciones que los puertos nuevos de identidad,
consentimiento, menores y roles pueden producir. Existe porque el contrato
heredado —`dominio/puertos/consentimiento.py`— hace justo lo contrario y el
encargo de la Fase 3 · sesión 2 lo prohíbe explícitamente:

    `None` cubre tres situaciones distintas a propósito —no hay titular, no hay
    fila, el almacén no responde—: quien llama trata las tres igual.

Eso es tolerable para una pantalla que sólo pregunta «¿ya consintió?». Deja de
serlo en cuanto el sistema tiene que mostrar **mantenimiento** cuando la base no
responde (`EQ-024`) y **onboarding** cuando simplemente no hay fila: con un
único `None` las dos situaciones producirían la misma pantalla, y una de las dos
sería mentira.

Los seis desenlaces, y cómo se distinguen
-------------------------------------------------
| Desenlace | Cómo se ve desde quien llama |
|---|---|
| **ausencia de registro** | la consulta devuelve `None` y **no** levanta |
| **estado pendiente** | la consulta devuelve un estado cuyo valor es `pendiente` |
| **almacén no configurado** | `AlmacenNoConfigurado` |
| **almacén no disponible** | `AlmacenNoDisponible` |
| **dato no admitido** | `DatoNoAdmitido` — la operación no llegó a ejecutarse |
| **escritura rechazada** | `EscrituraRechazada` y sus cuatro subclases |

El sexto lo añadió `M1`, y por el mismo motivo que existían los cinco: un valor
que el controlador se niega a enviar no es una avería del almacén, y mientras
compartieron desenlace un código malformado del cliente se presentaba como
mantenimiento.

`None` sigue existiendo, pero ahora significa **una sola cosa**: no hay fila. Un
fallo del almacén ya no puede disfrazarse de ausencia porque levanta.

Por qué «no configurado» y «no disponible» son dos y no una
------------------------------------------------------------------
Se arreglan de formas distintas y se le cuentan al usuario de formas distintas.
Sin cadena de conexión el despliegue está incompleto y nadie debería ver una
pantalla de mantenimiento transitorio; con cadena y una base caída sí es
mantenimiento, y `EQ-024` pide reintento controlado y aviso al equipo. Fundirlas
obligaría a adivinar cuál de las dos ocurrió.

Las cuatro formas de rechazar una escritura
------------------------------------------------------------
`TransicionInvalida` (el acto no puede seguir al vigente), `ReferenciaDesconocida`
(nombra algo que no existe), `AlcanceIncorrecto` (se apoya en la versión de otra
dimensión) y `VersionNoVigente` (la versión no regía en ese momento). Las cuatro
son rechazos con motivo y ninguna se arregla reintentando, que es lo que las
separa de `AlmacenNoDisponible`.

`TransicionInvalida` no es un error de almacenamiento
------------------------------------------------------------
Y aun así vive aquí, bajo `EscrituraRechazada`: es el desenlace que el encargo
pide poder distinguir —«escritura rechazada por transición inválida»— y quien
llama necesita atraparlo junto a los demás rechazos de escritura sin conocer el
módulo de dominio que definió la regla. La regla en sí —qué transición es
válida— sí vive en `dominio/modelo/consentimiento.py`, que es quien la aplica.


"""

from __future__ import annotations


class ErrorDeAlmacen(RuntimeError):
    """Raíz común. Atraparla trata los cinco desenlaces por igual, que es
    exactamente lo que esta jerarquía existe para evitar: se declara para que
    un `except` amplio sea una decisión visible y no un descuido."""


class AlmacenNoConfigurado(ErrorDeAlmacen):
    """No hay a qué almacén hablarle. El despliegue está incompleto.

    No es mantenimiento: nada se va a recuperar solo. `EQ-024` separa salud de
    proceso y disponibilidad, y esto es lo primero.
    """


class AlmacenNoDisponible(ErrorDeAlmacen):
    """Hay almacén y no responde. Es el estado que `EQ-024` llama mantenimiento.

    Se levanta también en lectura, y por eso una consulta que devuelve `None`
    significa «no hay fila» sin ambigüedad.
    """


class DatoNoAdmitido(ErrorDeAlmacen):
    """El valor no es representable y **la operación no llegó a ejecutarse**.

    El caso real y el único que hoy la produce: un `\\x00` dentro de un `str`.
    Psycopg se niega a enviarlo —«PostgreSQL text fields cannot contain NUL»— y
    la consulta no sale de la máquina. No hay SQLSTATE porque no hubo servidor
    que lo asignara.

    Por qué no es `AlmacenNoDisponible` · `M1`
    ---------------------------------------------
    Porque el almacén está perfectamente. Lo que no sirve es el dato. Mientras
    las dos cosas compartieron desenlace, `GET
    /api/consentimiento/version/{codigo}/texto` respondía 503 a un código
    malformado: le pedía a la persona que reintentara algo que nunca va a
    funcionar, y usaba el lenguaje de mantenimiento de `EQ-024` —el que avisa al
    equipo de que hay que ir a mirar la base— para un error del cliente.

    Por qué no es `EscrituraRechazada`
    -------------------------------------
    Porque también ocurre leyendo, y porque aquel nombre promete que el almacén
    vio la operación y se negó. Aquí no la vio.

    Qué significa para quien lee
    -------------------------------
    Un valor que la base no puede ni almacenar **no identifica ninguna fila**.
    Para una búsqueda por identificador, el desenlace honesto es «no existe», y
    ésa es la traducción que hacen las rutas: 404, con el mismo cuerpo que un
    identificador desconocido. Responder algo distinto separaría «no existe» de
    «no puede existir», que es un oráculo que nadie pidió.

    Qué significa para quien escribe
    -----------------------------------
    Que la escritura no ocurrió. Cuelga de `ErrorDeAlmacen` y no de ninguna de
    las otras cuatro precisamente para que un `except` pensado para mantenimiento
    no se la trague en silencio.
    """


class EscrituraRechazada(ErrorDeAlmacen):
    """La operación llegó al almacén y el almacén se negó, con motivo.

    Distinta de `AlmacenNoDisponible`: repetirla no la arregla. Distinta de la
    ausencia de registro: aquí hubo una petición de cambio y se denegó.
    Distinta de `DatoNoAdmitido`: aquí el almacén vio la operación.
    """


class TransicionInvalida(EscrituraRechazada):
    """El estado nuevo no puede seguir al vigente.

    La tabla de transiciones vive en `dominio/modelo/consentimiento.py` y en
    `dominio/modelo/menores.py`; esta clase es sólo cómo se comunica el rechazo.
    """


class ReferenciaDesconocida(EscrituraRechazada):
    """La escritura nombra algo que no existe: una versión, una persona, una
    evidencia. Es la integridad referencial de la base traducida a un desenlace
    del contrato, para que quien llama no tenga que reconocer un error de
    Psycopg."""


class AlcanceIncorrecto(EscrituraRechazada):
    """El acto se apoya en una versión de otra dimensión.

    Un consentimiento del titular sobre la versión del asentimiento, o una
    evidencia del representante sobre la del titular. La base lo impide con una
    clave foránea compuesta contra `(codigo, alcance)`; esta clase existe para
    que el rechazo llegue con motivo en vez de como una violación de clave.
    """


class VersionNoVigente(EscrituraRechazada):
    """La versión existe y es del alcance correcto, pero no regía en ese momento.

    Cubre las dos mitades: una versión **futura**, cuyo `vigente_desde` todavía
    no llegó, y una **vencida**, cuyo `vigente_hasta` ya pasó. Ninguna de las dos
    puede recibir un acto nuevo — aceptar sobre un texto que no estaba publicado,
    o sobre uno retirado, no autoriza nada.
    """


class PerfilSinEdad(EscrituraRechazada):
    """La persona existe y no ha declarado edad, así que el acto no se registra.

    `EQ-016` hace depender el régimen entero de la edad: cuántos actos produce
    una decisión, si hace falta asentimiento y si hace falta la autorización del
    representante. Sin ella no hay régimen que aplicar, y **no se asume mayoría
    de edad** — es la corrección deliberada de `DD-26`.

    Cuelga de `EscrituraRechazada` como los demás rechazos con motivo, y es una
    clase propia por lo mismo que `VersionNoVigente` lo es: se arregla de una
    forma concreta —completar el perfil— y presentarla como un rechazo genérico
    dejaría a quien la reciba sin poder decirlo. `D1B` la traduce a un `409` con
    `estado: "perfil_incompleto"`, distinto del `409` de una versión que falta.
    """
