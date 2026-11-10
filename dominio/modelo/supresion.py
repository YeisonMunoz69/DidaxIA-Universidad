"""
supresion.py — El trámite de supresión de `EQ-022`, sin ejecutarlo
====================================================================

`EQ-022` describe la supresión como un **trámite**, no como un botón:

    «La supresión es un trámite distinto: exige reautenticación reciente con
    Google, diálogo explícito, frase de confirmación y aviso al correo
    institucional; dispone de 24 horas para cancelar antes de ejecutarse. […]
    El plazo operativo es de 15 días hábiles, con extensión excepcional
    informada de hasta 8 días hábiles adicionales.»

Este módulo modela ese trámite: sus estados, sus plazos y qué hace falta para
abrirlo. **No borra nada**, y el límite es del encargo, no una omisión.

⚠️ Por qué no hay ejecución aquí
------------------------------------------
Porque nadie ha decidido todavía qué se borra. Cambiar el sujeto técnico de una
conversación sólo la **seudonimiza**: su texto puede seguir conteniendo nombres,
correos u otros identificadores que la persona escribió. Llamar anónimo a ese
texto sería falso, y construir un «redactor automático» que los quitara sería
inventarse un criterio que el equipo no ha dado.

El cierre V-B decidirá qué textos se eliminan, qué se conserva seudonimizado
hasta el límite de retención, qué métricas estructuradas pueden anonimizarse de
forma irreversible y qué evidencia de la operación se conserva. Hasta entonces,
`EstadoSupresion.EJECUTADA` existe como valor posible y **nada en este árbol lo
escribe**.

Días hábiles, y dónde se cuentan
--------------------------------------------------
`EQ-022` habla de días **hábiles**, no naturales, y la diferencia son casi tres
semanas en el plazo de 15. Contarlos es una regla de negocio —qué día es hábil— y
por eso vive en el dominio y no en un `INTERVAL` de SQL.

✅ **Corregido en el cierre V-B.** Aquí decía que sólo se excluían sábados y
domingos, y que los festivos colombianos quedaban fuera porque nadie había
aprobado una fuente. La fuente es la ley, no un servicio:
`dominio/modelo/calendario.py` la calcula —Ley 51 de 1983 y la Pascua
gregoriana— sin red y sin tabla que mantener. Este módulo ya no cuenta días:
delega, para que la definición de «día hábil» exista una sola vez.


"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from dominio.modelo.calendario import es_habil, sumar_dias_habiles

#: `EQ-022` · la ventana para cancelar antes de que el trámite avance.
HORAS_PARA_CANCELAR = 24

#: `EQ-022` · el plazo operativo y su extensión excepcional, en días hábiles.
DIAS_HABILES_PARA_RESOLVER = 15
DIAS_HABILES_DE_EXTENSION = 8

#: Cuánto puede haber pasado desde la reautenticación con Google para que cuente
#: como «reciente» (`EQ-022`). Cinco minutos: suficiente para completar el
#: diálogo de confirmación y corto para que una sesión abierta ayer no baste.
#:
#: ⚠️ El valor no lo fija ninguna decisión del equipo; `EQ-022` dice «reciente»
#: sin cifra. Cinco minutos es el mínimo defendible y queda como deuda: si el
#: equipo prefiere otro, es una constante.
SEGUNDOS_DE_REAUTENTICACION_RECIENTE = 5 * 60

#: Cuánto se le perdona al reloj de Google respecto del de este servidor, en
#: segundos, al juzgar la frescura **firmada** de un `id_token` (hito R7-A).
#:
#: ⚠️ Pequeña y explícita, y las dos cosas importan. Dos relojes sincronizados por
#: NTP rara vez se separan más de unos segundos, así que treinta cubre el desfase
#: real con holgura. Lo que NO puede es acercarse a
#: `SEGUNDOS_DE_REAUTENTICACION_RECIENTE`: una tolerancia amplia sería la ventana
#: de reautenticación otra vez, escrita con otro nombre y sin que nadie la
#: hubiera decidido. Se aplica a los dos lados —un `iat` del pasado inmediato y
#: uno del futuro inmediato— porque un desfase de reloj no tiene signo.
TOLERANCIA_DE_RELOJ_SEGUNDOS = 30

#: La frase exacta que hay que escribir. La comprueba el **backend** (`EQ-024`
#: exige confirmación explícita) y no el navegador: una confirmación que valida
#: el cliente la puede saltar cualquiera que llame a la API directamente.
FRASE_DE_CONFIRMACION = "ELIMINAR MIS DATOS"


class SupresionInvalida(ValueError):
    """La solicitud no reúne lo que `EQ-022` exige para abrirse."""


class EstadoSupresion(StrEnum):
    """Los cuatro estados del trámite.

    `EJECUTADA` existe porque el trámite termina en algún sitio y omitirlo haría
    que el modelo mintiera sobre su propio ciclo. **Nada en este árbol lo
    escribe**: ver la cabecera del módulo.
    """

    SOLICITADA = "solicitada"
    CANCELADA = "cancelada"
    EJECUTADA = "ejecutada"
    RECHAZADA = "rechazada"


#: Reexportadas para los consumidores que ya las importaban de aquí. La
#: definición vive en `dominio/modelo/calendario.py`, que es donde se puede
#: comprobar contra el calendario colombiano real; aquí sólo se nombran para no
#: obligar a cada llamador a saber que se mudaron.
__all__ = [
    "DIAS_HABILES_DE_EXTENSION",
    "DIAS_HABILES_PARA_RESOLVER",
    "FRASE_DE_CONFIRMACION",
    "HORAS_PARA_CANCELAR",
    "SEGUNDOS_DE_REAUTENTICACION_RECIENTE",
    "TOLERANCIA_DE_RELOJ_SEGUNDOS",
    "EstadoSupresion",
    "SolicitudDeSupresion",
    "SupresionInvalida",
    "emision_recien_firmada",
    "es_habil",
    "extension_de",
    "frase_correcta",
    "plazos_de",
    "reautenticacion_reciente",
    "sumar_dias_habiles",
]


def reautenticacion_reciente(reautenticada_en: datetime, ahora: datetime) -> bool:
    """`EQ-022` · si esa reautenticación todavía sirve para abrir el trámite.

    Una del futuro no vale: sería un reloj mal puesto o un cliente mintiendo, y
    en los dos casos lo seguro es no aceptarla.
    """
    if reautenticada_en > ahora:
        return False
    return (ahora - reautenticada_en).total_seconds() <= SEGUNDOS_DE_REAUTENTICACION_RECIENTE


def emision_recien_firmada(
    emitido_en: datetime | None,
    ahora: datetime,
    *,
    autenticado_en: datetime | None = None,
) -> bool:
    """Si lo que Google **firmó** demuestra que la autenticación es de ahora.

    ⚠️ No es lo mismo que `reautenticacion_reciente()`, y confundirlas fue el
    defecto R7-A. Aquella juzga una marca que puso **este servidor** cuando
    acreditó algo; ésta juzga la marca que puso **Google** al emitir el token, y
    es la única de las dos que puede decir si el token era fresco.

    El reloj del servidor acredita *cuándo recibimos* el token, no *cuándo se
    emitió*: un `id_token` con una hora de vigencia por delante sigue llegando
    válido cincuenta minutos después de que su dueño se autenticara, y hasta el
    hito R7-A eso bastaba para reautenticar. Reautenticar existe justamente para
    exigir que la persona esté delante **ahora**.

    Tres condiciones, y las tres tienen que salir del token:

    1. **`iat` existe.** Sin él no hay frescura firmada que comprobar, y suponer
       una sería inventarla. Un token sin `iat` sirve para iniciar sesión —eso lo
       decide su vigencia— pero no para reautenticar.
    2. **`iat` no es más antiguo que la ventana** de
       `SEGUNDOS_DE_REAUTENTICACION_RECIENTE`, con `TOLERANCIA_DE_RELOJ_SEGUNDOS`
       de holgura por el desfase entre los dos relojes.
    3. **`iat` no está injustificadamente en el futuro.** Dentro de la tolerancia
       es un reloj adelantado; más allá es un token que dice haberse emitido
       cuando todavía no ha ocurrido, y aceptarlo alargaría la ventana tanto
       como el desfase que alguien declarara.

    `auth_time` —*cuándo se autenticó de verdad la persona*, frente a *cuándo se
    firmó este token*— **se comprueba si viene y no se inventa si falta**
    (`OIDC` no obliga a emitirlo salvo que se pida `max_age`). Cuando viene:

    - tiene que caber en la misma ventana, porque un `iat` recién firmado sobre
      una sesión de Google autenticada anteayer no demuestra que nadie esté
      delante — es exactamente la contradicción que el hito R7-A no admite;
    - no puede ser **posterior** al `iat` más la tolerancia: un token no se firma
      antes de la autenticación que certifica, y si lo dice, se contradice.

    Su ausencia no se convierte en una autenticación ficticia: no se copia `iat`
    encima ni se da por supuesto un momento. Simplemente no hay segunda
    comprobación que hacer, y la primera sigue mandando.
    """
    if emitido_en is None:
        return False
    if not _dentro_de_la_ventana(emitido_en, ahora):
        return False
    if autenticado_en is None:
        return True
    if not _dentro_de_la_ventana(autenticado_en, ahora):
        return False
    # Firmado antes de autenticarse: el token se contradice a sí mismo.
    return (autenticado_en - emitido_en).total_seconds() <= TOLERANCIA_DE_RELOJ_SEGUNDOS


def _dentro_de_la_ventana(momento: datetime, ahora: datetime) -> bool:
    """Ni más viejo que la ventana ni más adelantado que la tolerancia."""
    desfase = (ahora - momento).total_seconds()
    if desfase < -TOLERANCIA_DE_RELOJ_SEGUNDOS:
        return False
    return desfase <= SEGUNDOS_DE_REAUTENTICACION_RECIENTE + TOLERANCIA_DE_RELOJ_SEGUNDOS


def frase_correcta(escrita: str) -> bool:
    """Si la frase de confirmación coincide.

    Se comparan sin espacios de los extremos y sin distinguir mayúsculas: la
    persona está escribiendo bajo presión y `EQ-024` quiere una confirmación
    consciente, no un examen de mecanografía. Lo que no se admite es una frase
    distinta ni una vacía.
    """
    return (escrita or "").strip().casefold() == FRASE_DE_CONFIRMACION.casefold()


@dataclass(frozen=True, slots=True)
class SolicitudDeSupresion:
    """Una solicitud abierta o cerrada, con sus tres plazos.

    Los plazos se **guardan** y no se recalculan al consultarlos: el que rige es
    el que se le comunicó a la persona, y recalcularlo con reglas nuevas movería
    un compromiso ya adquirido.
    """

    sujeto_google: str
    estado: EstadoSupresion
    solicitada_en: datetime
    cancelable_hasta: datetime
    resolver_antes_de: datetime
    solicitada_por: str = ""
    extension_hasta: datetime | None = None
    extension_motivo: str = ""
    cerrada_en: datetime | None = None
    secuencia: int = 0

    @property
    def abierta(self) -> bool:
        return self.estado is EstadoSupresion.SOLICITADA

    def cancelable_en(self, ahora: datetime) -> bool:
        """`EQ-022` · 24 horas para cancelar. Después, ya no.

        Que el plazo pase **no** ejecuta nada: sólo cierra la puerta de la
        cancelación por parte del titular. Quién ejecuta y cuándo es de V-B.
        """
        return self.abierta and ahora <= self.cancelable_hasta

    @property
    def plazo_vigente(self) -> datetime:
        """La fecha en que hay que resolver, con la extensión si la hubo."""
        return self.extension_hasta or self.resolver_antes_de


def plazos_de(solicitada_en: datetime) -> tuple[datetime, datetime]:
    """`(cancelable_hasta, resolver_antes_de)` para una solicitud nueva.

    Una función y no dos cálculos repartidos: los dos plazos salen del mismo
    instante y separarlos permitiría que una ruta usara uno y otra el otro.
    """
    return (
        solicitada_en + timedelta(hours=HORAS_PARA_CANCELAR),
        sumar_dias_habiles(solicitada_en, DIAS_HABILES_PARA_RESOLVER),
    )


def extension_de(resolver_antes_de: datetime) -> datetime:
    """`EQ-022` · hasta 8 días hábiles adicionales, informados."""
    return sumar_dias_habiles(resolver_antes_de, DIAS_HABILES_DE_EXTENSION)
