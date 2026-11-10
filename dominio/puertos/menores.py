"""
menores.py — Contrato del asentimiento y de la evidencia del representante
============================================================================

Las dos dimensiones que `EQ-016` declara independientes del consentimiento. Dos
puertos, porque son dos almacenes con dos consumidores: el asentimiento lo
produce el menor y la evidencia la revisa un investigador autorizado.

El archivo no entra aquí
---------------------------------
`registrar_intento()` recibe **metadatos**: una referencia opaca al
almacenamiento privado del equipo, la huella del archivo, su tipo y su tamaño. No
recibe bytes, no recibe una ruta local y no recibe una URL — `EQ-021` descarta un
enlace mutable del Drive personal como evidencia definitiva, y el tipo del
dominio lo rechaza antes de que llegue a la base.

Descargar el DOCX y subir el PDF es la sesión 3. Aquí sólo se modela lo que queda
persistido cuando eso ocurra.

Una carga nueva no borra la anterior
---------------------------------------------
`registrar_intento()` crea un intento con el número siguiente y conserva todos
los anteriores. `revisar()` añade una fila de revisión y conserva las anteriores.
No hay ninguna operación en este contrato que actualice o borre un intento o una
revisión, y desde la corrección de la revisión la base tampoco la admite: un
disparador rechaza UPDATE y DELETE sobre las dos tablas.

Un adulto no da asentimiento
---------------------------------------------
`PuertoAsentimiento.registrar()` sólo acepta actos de una persona menor, y lo
comprueba dentro de la misma transacción. Una fila de cuando sí lo era se
conserva y deja de intervenir: la derivación de un adulto es `no_requerido`.

Quién puede revisar
--------------------------
`revisar()` exige que el sujeto revisor tenga `investigador_administrador`
(`EQ-023`), comprobado contra `dominio/puertos/roles.py` y **no** contra una
lista de correos. Un revisor sin el rol recibe `EscrituraRechazada`, que es un
rechazo con motivo y no un fallo del almacén.

Consultar tampoco es gratis · C2A
-------------------------------------------
`cola()`, `detalle()` y `referencia_del_documento()` **leen**, y aun así exigen
el mismo rol y con la misma disciplina transaccional que `revisar()`. No es
simetría por gusto: una lista de autorizaciones firmadas por representantes
legales de menores es tan sensible como el poder de aprobarlas, y un permiso de
lectura más flojo que el de escritura habría dejado enumerar lo que no se puede
resolver.

Por eso `actor` es un parámetro **obligatorio y con nombre** en las tres. Sin
valor por defecto: una consulta que se pudiera llamar sin decir quién la hace
sería una consulta sin autorizar, y la única forma de garantizar que no exista
es que Python se niegue a construirla.


"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dominio.modelo.evidencia_revisable import (
    EvidenciaRevisable,
    FiltroDeEvidencias,
    PaginaDeEvidencias,
    PosicionDeCursor,
)
from dominio.modelo.menores import (
    EstadoAsentimiento,
    EventoAsentimiento,
    HistorialDeAsentimiento,
    IntentoDeEvidencia,
    ResultadoDeRevision,
    RevisionDeEvidencia,
)


@runtime_checkable
class PuertoAsentimiento(Protocol):
    """El historial inmutable del asentimiento del menor."""

    def registrar(
        self,
        sujeto_google: str,
        version: str,
        estado: EstadoAsentimiento,
        comprobante: str,
    ) -> EventoAsentimiento:
        """Añade un acto de asentimiento y devuelve el evento persistido.

        Mismo contrato que el consentimiento del titular: transición comprobada
        dentro de la transacción, `TransicionInvalida` si no procede,
        `ReferenciaDesconocida` si el sujeto o la versión no existen, y ninguna
        fila anterior modificada.
        """
        ...


    def version_de_la_concesion(self, sujeto_google: str) -> str | None:
        """La versión de la última concesión **otorgada**, o `None`.

        Es lo que permite revocar sin que el cliente elija versión (hito R3).
        `EQ-022` separa dos vigencias y ésta es la segunda: quien otorgó conserva
        el derecho a retirar **esa** concesión aunque su documento haya vencido o
        haya sido desplazado por uno posterior.

        `None` significa que no hay ninguna concesión otorgada que retirar —ni un
        rechazo ni una revocación previa lo son—, y quien llame debe responder un
        rechazo con motivo, no un error. Un almacén caído levanta.

        ⚠️ No sustituye a la comprobación de la escritura. `registrar()` vuelve a
        exigir que la versión sea la de la concesión otorgada dentro de su propia
        transacción, así que una revocación concurrente entre esta lectura y
        aquella escritura se rechaza limpiamente en vez de retirar otra cosa.
        """
        ...

    def historial(self, sujeto_google: str, *, requerido: bool) -> HistorialDeAsentimiento:
        """Los eventos ordenados, más si el asentimiento hace falta.

        `requerido` lo decide la edad y entra por parámetro a propósito: el
        almacén de asentimientos no tiene por qué saber leer un perfil, y
        deducirlo aquí crearía una segunda regla de mayoría de edad.
        """
        ...


@runtime_checkable
class PuertoEvidenciaDelRepresentante(Protocol):
    """Los intentos de carga y sus revisiones. Nunca el archivo."""

    def registrar_intento(
        self,
        sujeto_google: str,
        version: str,
        referencia: str,
        sha256: str,
        tamano_bytes: int,
    ) -> IntentoDeEvidencia:
        """Crea el intento siguiente y conserva todos los anteriores.

        `version` es qué documento del representante se firmó, y es obligatoria:
        sin ella una autorización firmada sobre un texto retirado parecería cubrir
        el que rige hoy. Tiene que ser de alcance `representante` y estar vigente,
        y las dos cosas las exige también la base.

        El número de intento lo asigna el almacén dentro de la transacción; quien
        llama no lo elige, para que dos cargas simultáneas no puedan compartirlo.
        Se numera por persona y no por versión, para que el historial de cargas se
        lea entero de una vez. El tipo MIME no es parámetro porque `EQ-021` sólo
        admite uno.
        """
        ...

    def revisar(
        self,
        evidencia: int,
        revisor: str,
        resultado: ResultadoDeRevision,
        motivo: str = "",
    ) -> RevisionDeEvidencia:
        """Aprueba o rechaza un intento, conservando actor y momento.

        `motivo` es obligatorio al rechazar. Levanta `EscrituraRechazada` si el
        revisor no tiene el rol de `EQ-023` y `ReferenciaDesconocida` si la
        evidencia no existe.
        """
        ...

    def intentos(self, sujeto_google: str) -> tuple[IntentoDeEvidencia, ...]:
        """Todos los intentos, del primero al último, cada uno con su última
        revisión si la tiene. Vacío —no `None`— para quien no ha cargado nada."""
        ...

    # ── C2A · lo que ve quien revisa ─────────────────────────────────────
    #
    # Las tres devuelven o consumen `EvidenciaRevisable`, que **no tiene
    # `referencia`**. La única que produce una referencia es la última, y lo
    # dice en su nombre: quien la llame está pidiendo el identificador del
    # archivo privado y no puede hacerlo por descuido.

    def cola(
        self,
        *,
        actor: str,
        filtro: FiltroDeEvidencias = FiltroDeEvidencias.PENDIENTE,
        limite: int = 20,
        cursor: PosicionDeCursor | None = None,
    ) -> PaginaDeEvidencias:
        """Un tramo de la cola de revisión, ordenado y sin la referencia privada.

        `actor` es de quién se comprueba el rol, y va **primero**: la
        implementación exige `investigador_administrador` vigente antes de mirar
        ninguna evidencia, en la misma transacción y reteniendo la asignación.
        Un actor sin rol recibe `EscrituraRechazada` y ni siquiera aprende
        cuántas evidencias hay.

        `actor` sale de la sesión verificada de quien llama y nunca del cuerpo ni
        de la cadena de consulta — el puerto no puede exigirlo, pero el borde sí,
        y `rutas/evidencias.py` es el único sitio que lo compone.

        El orden es `(recibido_en, id)` ascendente: la evidencia que lleva más
        tiempo esperando se revisa primero, y el desempate por identidad monótona
        da un orden **total**, de modo que dos filas del mismo instante no
        cambian de sitio entre dos peticiones.

        Una cola vacía devuelve una página vacía. No es un error: es el estado
        sano de un sistema con todo revisado.
        """
        ...

    def detalle(self, evidencia: int, *, actor: str) -> EvidenciaRevisable:
        """Una evidencia por su identificador, para quien tiene el rol vigente.

        ⚠️ **El orden de las dos comprobaciones es el contrato, no una
        preferencia.** Primero el rol, después la existencia. Al revés, un
        usuario autenticado sin rol distinguiría una evidencia existente de una
        inexistente por el código de respuesta —o por el tiempo que tarda— y eso
        es un oráculo de enumeración: bastaría recorrer identificadores para
        saber cuántas autorizaciones de representante legal hay en el sistema y
        cuáles.

        Levanta `EscrituraRechazada` sin rol —el mismo desenlace exista o no la
        evidencia— y `ReferenciaDesconocida` si no existe, que sólo puede verla
        quien ya demostró el rol.
        """
        ...

    def referencia_del_documento(self, evidencia: int, *, actor: str) -> str:
        """La referencia opaca del archivo privado. **El único punto de salida.**

        Existe aparte de `detalle()` para que la referencia no viaje dentro de
        ningún tipo que alguien pueda serializar: quien la obtiene es porque la
        pidió por su nombre, y lo único que puede hacer con ella es dársela a
        `PuertoAlmacenamientoPrivado.recuperar()`.

        Misma disciplina que `detalle()`: rol primero, existencia después. Y el
        mismo aviso que el resto de la frontera — esta cadena no se registra, no
        se devuelve en JSON y no se pone en una cabecera.
        """
        ...
