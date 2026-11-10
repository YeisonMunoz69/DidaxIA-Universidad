"""
gobierno.py — Supresión solicitada, retención, auditoría y notificación (B3)
=============================================================================

Los cuatro contratos del gobierno de datos reversible de `EQ-022`/`EQ-023`.
Juntos porque los cuatro los consume el mismo recorrido y separarlos en cuatro
archivos habría obligado a importarlos siempre a la vez.

Y `SupresionEnCurso`, que es de aquí y no de ninguna operación concreta
------------------------------------------------------------------------------
La regla «durante el trámite no se trata nada nuevo» gobierna **todas** las
escrituras de la persona, así que su excepción vive en la frontera del gobierno
de datos y no colgando del puerto de la ruta que primero la necesitó.

⚠️ Ninguno ejecuta una supresión
-------------------------------------------
`PuertoSolicitudesDeSupresion` abre, cancela y consulta el trámite. **No borra**,
y no tiene un método que borre. El cierre V-B decidirá qué se elimina, qué se
conserva seudonimizado y qué puede anonimizarse de forma irreversible; hasta
entonces, este contrato no ofrece la operación ni la deja a medio construir.

La notificación va detrás de un puerto y nada más
------------------------------------------------------------
`EQ-022` pide avisar al correo institucional y `EQ-024` dice que *«Resend será un
canal de notificación, no una dependencia del diagnóstico ni una garantía de
disponibilidad»*. Aquí está el contrato; el adaptador real de Resend **no se
construye en este paquete** —haría falta una credencial que nadie ha aprobado— y
el árbol trae uno que registra la intención sin enviar nada.


"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from dominio.modelo.propuestas import Propuesta
from dominio.modelo.supresion import SolicitudDeSupresion
from dominio.puertos.almacen import EscrituraRechazada


class SupresionEnCurso(EscrituraRechazada):
    """Hay un trámite de supresión abierto: no se trata nada nuevo.

    `EQ-022` y `ESTADO-ACTUAL.md` §10.2 lo dicen igual: durante el trámite se
    puede **consultar y cancelar**, no aportar ni registrar datos nuevos. Vale
    para cualquier escritura de la persona —su consentimiento, su perfil, su
    evidencia, su matrícula—, no sólo para la decisión conjunta.

    ⚠️ **Vivía en `dominio/puertos/decision_conjunta.py`**, donde nació con la
    corrección de `f95fa28`. Se muda aquí porque la regla no es de esa operación
    sino del **gobierno de los datos**: dejarla colgando del puerto de una sola
    ruta invitaba a que la siguiente familia que la necesitara declarara la suya,
    y dos clases con el mismo significado son dos reglas en cuanto alguien
    corrige una. Aquel módulo la reexporta para no romper importaciones.

    ⚠️ **Rechazar tampoco es la excepción.** Parece inofensivo porque no
    autoriza, pero deja su fila igual, y `PanelDeEstado.svelte` le promete a la
    persona que durante el trámite no se registra nada nuevo. Una promesa que
    sólo cumple el navegador no es una garantía.

    Es un rechazo del almacén, como los demás, para que el borde lo atrape junto
    a ellos y publique su estado **sin comparar mensajes de texto**.
    """


@runtime_checkable
class PuertoSolicitudesDeSupresion(Protocol):
    """El trámite de `EQ-022`: abrirlo, cancelarlo, consultarlo. Nada más."""

    def abrir(
        self,
        sujeto_google: str,
        *,
        reautenticada_en: datetime,
        frase: str,
        actor: str = "",
    ) -> SolicitudDeSupresion:
        """Abre el trámite si se cumplen las tres condiciones de `EQ-022`.

        Levanta `EscrituraRechazada` si la reautenticación no es reciente, si la
        frase no coincide o si ya hay un trámite abierto. Las tres son rechazos
        con motivo: ninguna se arregla reintentando sin corregir algo.

        Los plazos —cancelación y resolución— se calculan al abrir y se guardan.

        `reautenticada_en` llega **ya acreditada por el servidor** (hito R3): el
        implementador comprueba que siga siendo reciente, no que exista. Nunca es
        una fecha que el cliente haya enviado.

        `actor` es quien realiza la operación y sale de la sesión. La constancia
        de `EQ-023` se escribe en la **misma transacción**: si no se puede
        registrar, el trámite no queda abierto.
        """
        ...

    def cancelar(self, sujeto_google: str, *, ahora: datetime, actor: str = "") -> bool:
        """`EQ-022` · 24 horas para cancelar. `False` si no había nada abierto.

        Levanta `EscrituraRechazada` si la ventana ya pasó: pasado el plazo, el
        titular ya no puede retirarla por su cuenta, y decirle que sí pudo sería
        mentira.

        `actor` audita la cancelación en la misma transacción, igual que `abrir()`.
        """
        ...

    def abierta_de(self, sujeto_google: str) -> SolicitudDeSupresion | None:
        """El trámite abierto de ese titular, o `None`.

        `None` significa **sólo** que no hay ninguno abierto. Un almacén caído
        levanta, para que `dominio/modelo/acceso.py` no reciba «no hay trámite»
        cuando lo que pasa es que no se sabe.
        """
        ...

    def historial(self, sujeto_google: str) -> tuple[SolicitudDeSupresion, ...]:
        """Todos los trámites, abiertos y cerrados, del más antiguo al más
        reciente. Los cerrados se conservan: son la evidencia de que ocurrieron.
        """
        ...


@dataclass(frozen=True, slots=True)
class Retencion:
    """El plazo de `EQ-022`, tal como está fijado hoy.

    `sustentacion_en` admite `None` y hoy **siempre** lo es: la fecha no existe.
    `limite` devuelve `None` en ese caso en vez de una fecha inventada, y quien
    pregunte tiene que decir «sin fijar».
    """

    sustentacion_en: datetime | None = None
    meses_despues: int = 6
    nota: str = ""

    @property
    def limite(self) -> datetime | None:
        """Sustentación + los meses acordados, o `None` si no hay fecha.

        ✅ **Corregido en el cierre V-B.** Aquí se sumaban bloques de 30 días y se
        declaraba como aproximación aceptable porque «para seis meses la
        diferencia es de días». Sobre un plazo de retención esos días deciden si
        se borra antes de lo comprometido o se conserva más de lo autorizado, y
        `EQ-022` dice «seis meses», no «ciento ochenta días».

        El caso raro que quedaba sin decidir —31 de enero + 1 mes— lo resuelve
        `calendario.sumar_meses()` con una regla escrita y probada: el último día
        del mes destino cuando el día no existe allí.
        """
        if self.sustentacion_en is None:
            return None
        from dominio.modelo.calendario import sumar_meses  # noqa: PLC0415

        return sumar_meses(self.sustentacion_en, self.meses_despues)


@runtime_checkable
class PuertoRetencion(Protocol):
    """La política de retención, representable y consultable (`EQ-022`)."""

    def vigente(self) -> Retencion:
        """La política que rige. Con la fecha sin fijar, `sustentacion_en` es
        `None` y quien la muestre tiene que decirlo así."""
        ...

    def fijar(
        self, sustentacion_en: datetime, *, registrada_por: str, meses_despues: int = 6
    ) -> Retencion:
        """Registra una política nueva. No edita la anterior: queda constancia
        de cuál se comunicó antes.

        ⚠️ **Este método no comprueba la doble aprobación, y no debe.** `EQ-023`
        la reserva a dos actos autenticados, y eso no cabe en una llamada: la
        gobierna `PuertoPropuestas`, que aplica el efecto dentro de la
        transacción de la aprobación. Un repositorio que la comprobara por su
        cuenta sería un segundo sitio donde se decide quién puede qué.
        """
        ...


@dataclass(frozen=True, slots=True)
class OperacionAuditada:
    """Una operación administrativa registrada (`EQ-023`).

    `detalle` lleva identificadores y conteos. **Nunca** texto de conversaciones
    ni datos personales: la auditoría se conserva más tiempo que lo que audita, y
    copiar aquí lo que la supresión tendría que borrar lo dejaría vivo.
    """

    operacion: str
    actor: str
    momento: datetime
    sujeto_afectado: str | None = None
    detalle: dict | None = None
    exige_doble_aprobacion: bool = False
    aprobada_por: str | None = None
    secuencia: int = 0


@runtime_checkable
class PuertoAuditoria(Protocol):
    """El registro de `EQ-023`. Sólo se añade; nunca se corrige."""

    def registrar(
        self,
        operacion: str,
        *,
        actor: str,
        sujeto_afectado: str | None = None,
        detalle: dict | None = None,
        exige_doble_aprobacion: bool = False,
        aprobada_por: str | None = None,
    ) -> OperacionAuditada:
        """Deja constancia de una operación administrativa.

        Levanta `EscrituraRechazada` si la operación exige doble aprobación y no
        llega un segundo aprobador distinto del actor: `EQ-023` no admite que
        nadie se apruebe a sí mismo, y una aprobación automática sería
        exactamente eso.
        """
        ...

    def de(self, sujeto_google: str) -> tuple[OperacionAuditada, ...]:
        """Lo registrado sobre un titular, del más antiguo al más reciente."""
        ...

    def consultar_institucional(  # noqa: PLR0913 -- contrato explícito de filtros
        self, actor: str, pagina: int, tamano: int, *,
        operacion: str = "", actor_filtro: str = "", sujeto_filtro: str = "",
        desde: datetime | None = None, hasta: datetime | None = None,
        categoria: str = "", doble_aprobacion: str = "",
    ) -> dict:
        """Historial paginado; autoriza y audita antes de leerlo."""
        ...

    def informe_institucional(
        self, actor: str, *, filtros: dict, confirmado: bool,
        corte_instante: datetime,
    ) -> tuple[bytes, dict]:
        """Corte completo, generado y auditado antes de devolver bytes."""
        ...


@runtime_checkable
class PuertoNotificacion(Protocol):
    """El aviso al correo institucional (`EQ-022`), detrás de un puerto.

    `EQ-024`: Resend es un canal, no una garantía. Por eso las operaciones que
    notifican **no fallan** si el aviso no sale: la solicitud ya está registrada
    y decir que no se guardó sería mentira. Lo que sí queda es constancia.

    ⚠️ **`clave_idempotencia` es obligatoria desde `D2`**, y sólo por palabra
    clave. Las dos razones son distintas y las dos importan:

    - **obligatoria** · un reintento sin clave duplica el correo, y el titular
      recibe dos avisos del mismo hecho. Con valor por defecto, olvidarla sería
      silencioso: el aviso saldría igual y el duplicado aparecería semanas
      después, en el buzón de alguien;
    - **por palabra clave** · la firma ya lleva tres cadenas seguidas y una
      cuarta posicional se puede confundir con el cuerpo. Nombrarla obliga a
      leer qué se está pasando.

    Quien la deriva es el **caso de uso**, no el adaptador: sale de la secuencia
    o del comprobante del acto ya persistido —`decision-conjunta/<secuencia>`,
    `supresion-solicitada/<secuencia>`— y **nunca del correo**, que es un dato
    personal y además cambia de persona a persona sin identificar el hecho.
    """

    def avisar(
        self,
        correo: str,
        asunto: str,
        cuerpo: str,
        *,
        clave_idempotencia: str,
        html: str = "",
        adjuntos: tuple[dict[str, str], ...] = (),
    ) -> bool:
        """`True` si el aviso salió. Nunca levanta: el canal no decide el
        trámite.

        `False` significa **«no se pudo enviar»**, nunca «el trámite falló».
        Quien llame ya tiene su escritura confirmada y no puede deshacerla por
        esto (`EQ-024`).
        """
        ...


@runtime_checkable
class PuertoPropuestas(Protocol):
    """La doble aprobación de `EQ-023`, que necesita **dos actos autenticados**.

    Existe porque una aprobación no cabe en una sola petición. La primera deja
    una propuesta pendiente; la segunda, de otra persona en otra sesión, la
    aprueba. Sin algo que persista entre las dos, «aprobación de ambos» se
    reduce a que el primero escriba el identificador del segundo — que es
    exactamente el defecto que el cierre V-B devolvió.

    ⚠️ **`aprobar()` aplica el efecto.** No es una impureza del contrato: `EQ-023`
    exige que aprobación, cambio y auditoría se confirmen atómicamente, y eso
    obliga a que ocurran en la misma transacción. Repartirlos entre puertos los
    repartiría entre conexiones, y volverían a poder confirmarse por separado.
    """

    def crear(self, operacion: str, payload: dict, *, propuesta_por: str) -> Propuesta:
        """Deja la propuesta pendiente. No aplica nada.

        No recibe aprobador **por diseño**: quien propone no tiene dónde escribir
        que otro aprobó. Levanta `PropuestaInvalida` si la operación no es de las
        que admiten doble aprobación, y `EscrituraRechazada` si quien propone no
        es un investigador vigente.
        """
        ...

    def aprobar(self, identificador: int, *, aprobador: str) -> Propuesta:
        """Aprueba, aplica y audita, en una transacción.

        Levanta `ReferenciaDesconocida` si la propuesta no existe y
        `EscrituraRechazada` si el aprobador no tiene el rol, es quien la
        propuso, la propuesta ya no está pendiente o su contenido no coincide con
        la huella registrada.
        """
        ...

    def consultar(self, identificador: int) -> Propuesta | None:
        """Una propuesta por su identificador, o `None` si no existe."""
        ...

    def pendientes(self) -> tuple[Propuesta, ...]:
        """Las que esperan un segundo administrador, de la más reciente atrás."""
        ...
