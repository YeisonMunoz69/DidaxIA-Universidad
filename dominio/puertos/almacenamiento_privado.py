"""
almacenamiento_privado.py — Dónde vive el PDF del representante (`EQ-021`)
===========================================================================

`EQ-021` deja la evidencia firmada en *«almacenamiento privado controlado por el
equipo —inicialmente una carpeta de Google Drive institucional»*, y PostgreSQL
guarda sólo la referencia, la huella y los metadatos. Este puerto es esa
frontera.

Por qué existe antes que su adaptador real
----------------------------------------------------
Porque el recorrido de B2 tiene que poder probarse entero sin Google. `EQ-021`
también dice que las credenciales y la custodia de esa carpeta siguen abiertas
(`DECISIONES.md` § Decisiones abiertas), así que **el adaptador real de Drive no
se construye en este paquete**: sin credencial aprobada, escribirlo sería
adivinar cómo se autentica y dónde se guarda.

Lo que sí hay es el contrato y un adaptador que **falla cerrado**
(`adaptadores/salientes/almacenamiento/no_configurado.py`). Un despliegue sin
almacenamiento no puede aceptar evidencia, y lo dice: `EQ-024` prohíbe el éxito
parcial, y aceptar un PDF que no se guarda en ninguna parte lo sería.

Qué NO es la referencia que devuelve
----------------------------------------------
No es una URL. `EQ-021` descarta *«un enlace mutable del Drive personal del
estudiante»* como evidencia definitiva, y el tipo del dominio y el CHECK de
`representante_evidencia` rechazan cualquier `http(s)://`. Lo que este puerto
devuelve es un identificador **opaco y estable** que sólo el equipo puede
resolver: qué significa por dentro es asunto del adaptador.

⚠️ Dos fases, y por qué no basta con «guardar» · hito R4
---------------------------------------------------------------------
El contrato tenía un solo `guardar()`, y la auditoría V-B encontró lo que eso
permitía: **el archivo se guardaba y, si PostgreSQL fallaba después, quedaba un
PDF firmado por un representante legal en almacenamiento privado del que ninguna
base tenía noticia.** El comentario de la ruta lo declaraba —*«al revés deja, en
el peor caso, un archivo huérfano en la carpeta: recuperable»*—, pero
«recuperable» exige que alguien sepa que existe, y nadie lo sabía.

Ahora son tres operaciones y un protocolo de dos fases:

1. `reservar()` deja una carga **provisional**. Todavía no es evidencia de nada.
2. La fila entra en PostgreSQL.
3. `confirmar()` la promueve a definitiva — o `retirar()` la borra si la fila no
   entró.

Y la garantía que cierra el hueco: **una reserva que no se confirmó ni se retiró
queda pendiente y enumerable** (`pendientes()`). Si la compensación también
falla, no desaparece en silencio: sigue ahí, marcada como provisional, y un
operador puede encontrarla. Ésa es la «reserva durable y auditable» que hace
admisible responder 503 sin dejar un huérfano desconocido.

No hace falta un diario aparte porque la propia carga provisional **es** el
registro: un archivo en la zona de reserva significa exactamente «esto entró y
nunca se completó».

Y una cuarta operación, que lee · C2A
---------------------------------------------------------------------
`recuperar()`. Las tres primeras existen para que el archivo entre sin dejar
huérfanos; ésta existe para que alguien pueda mirarlo. Sin ella, C2A podría
listar evidencias y autorizar revisiones sobre documentos que nadie ha visto —y
`EQ-023` encarga *verificar*, no *sellar*.

Devuelve **bytes**, nunca un enlace. La diferencia no es de estilo: un enlace se
reenvía, sobrevive a la sesión y no vuelve a preguntar quién lo abre.

Qué NO decide este puerto
-------------------------------
No decide el límite de tamaño ni el tipo admitido —los fija `EQ-021` y los
comprueban el dominio y la base—, ni quién puede subir, ni qué se hace con el
archivo después, **ni quién puede leerlo**: `recuperar()` no recibe actor y no
debe recibirlo. Quien autoriza es `EQ-023` contra `rol_asignacion`, en la
frontera de evidencia y en una sola redacción. Reservar, confirmar, retirar,
recuperar y enumerar lo pendiente.

Tampoco valida el PDF: eso es leer un formato de archivo, que es trabajo del
borde (`adaptadores/entrantes/http/pdf.py`) y no de un contrato del dominio.


"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dominio.puertos.almacen import ErrorDeAlmacen


class AlmacenamientoNoConfigurado(ErrorDeAlmacen):
    """No hay dónde guardar el archivo privado.

    Cuelga de `ErrorDeAlmacen` a propósito: para quien llama es el mismo tipo de
    problema que una base sin cadena —el despliegue está incompleto y la
    operación no puede completarse—, y tratarlo aparte llevaría a olvidarlo en
    algún `except`.
    """


class AlmacenamientoNoDisponible(ErrorDeAlmacen):
    """Hay almacenamiento y no respondió. Transitorio, como una base caída."""


class DocumentoAusente(AlmacenamientoNoDisponible):
    """El almacenamiento respondió y no tiene nada bajo esa referencia.

    ⚠️ **No es «esa evidencia no existe».** Cuando esto ocurre, la fila SÍ está
    en PostgreSQL —quien llegó hasta aquí ya la encontró y ya demostró su rol— y
    lo que falta es el archivo. Es una discrepancia entre los dos almacenes, no
    una consulta equivocada, y responderla como si la evidencia no existiera
    sería mentirle a un revisor sobre algo que sí ocurrió.

    **Cuelga de `AlmacenamientoNoDisponible` a propósito**, con el mismo
    razonamiento que `AlmacenamientoNoConfigurado` cuelga de `ErrorDeAlmacen`:
    para quien llama es el mismo desenlace —no puedo entregar el documento, no
    informes éxito— y un tipo suelto acabaría olvidado en algún `except`. Quien
    quiera distinguirlo para dar un motivo más preciso puede atraparlo antes;
    quien no, ya lo trata bien.

    Que no se recupere **esperando** es la diferencia con su clase madre, y por
    eso merece nombre: un operador tiene que reconciliar los dos almacenes.
    Reintentar no lo arregla, y la reserva pendiente de `pendientes()` es el
    primer sitio donde mirar.
    """


class DocumentoPendienteDeConfirmacion(AlmacenamientoNoDisponible):
    """La carga existe y **sigue siendo provisional**: no es evidencia todavía.

    ⚠️ **Corrige una contradicción de la primera entrega de C2A.** Aquel
    `recuperar()` servía una reserva sin confirmar con el argumento de que «si la
    fila está en PostgreSQL, para el sistema eso es evidencia». No lo es, y el
    propio protocolo de dos fases lo dice: una reserva se convierte en evidencia
    definitiva cuando `confirmar()` la promueve, y sólo entonces. Mientras tanto,
    lo que hay es una carga a medio completar cuya petición **respondió 503 al
    estudiante**: el sistema le dijo que no había quedado registrada.

    Servirla a un revisor lo habría puesto a decidir sobre un documento que el
    sistema no acepta como entregado, y a aprobar —o rechazar— una autorización
    que su titular cree que no llegó. Las dos direcciones son injustas.

    Cuelga de `AlmacenamientoNoDisponible` por lo mismo que `DocumentoAusente`:
    para quien llama el desenlace es «no informes éxito», y un tipo suelto
    acabaría olvidado en algún `except`. Se distingue de ella porque aquí el
    archivo **sí está** y lo que falta es una operación administrativa —confirmar
    o retirar la reserva—, no una búsqueda.

    `pendientes()` sigue siendo cómo se encuentra. Esta excepción no la esconde:
    la nombra en el único sitio donde alguien podría confundirla con evidencia.
    """



@runtime_checkable
class PuertoAlmacenamientoPrivado(Protocol):
    """Guardar y recuperar el archivo que PostgreSQL no debe contener."""

    def reservar(self, contenido: bytes, *, sujeto_google: str, intento: int) -> str:
        """Deja una carga **provisional** y devuelve su referencia opaca y estable.

        Provisional significa: el archivo está, y todavía no cuenta como
        evidencia. Sólo `confirmar()` lo convierte en tal.

        `sujeto_google` e `intento` entran para que el adaptador pueda organizar
        lo que guarda, no para que quien llama construya la referencia: si la
        compusiera fuera, dos adaptadores distintos producirían referencias
        distintas para el mismo archivo y ninguna sería estable.

        La referencia que devuelve no puede ser una URL navegable — el tipo del
        dominio la rechazaría después, y esa comprobación es la red de seguridad,
        no el contrato.

        Levanta `AlmacenamientoNoConfigurado` si no hay dónde guardar y
        `AlmacenamientoNoDisponible` si lo hay y falló. Nunca devuelve una
        referencia inventada.
        """
        ...

    def confirmar(self, referencia: str) -> None:
        """Promueve una carga provisional a evidencia definitiva.

        Se llama **después** de que PostgreSQL aceptó la fila. Levanta
        `AlmacenamientoNoDisponible` si no pudo; quien llame no debe informar
        éxito en ese caso: la fila existe, pero el archivo no está donde vive la
        evidencia definitiva, y decir que sí lo está sería falso.
        """
        ...

    def retirar(self, referencia: str) -> bool:
        """Borra una carga **provisional**. `True` si existía.

        Es la compensación del protocolo: se llama cuando la fila no entró. No
        borra evidencia confirmada —para eso no hay operación, y no la hay a
        propósito: borrar evidencia es la cascada que el cierre V-B reserva a la
        decisión humana—.

        Levanta `AlmacenamientoNoDisponible` si no pudo retirarla. Ese fallo no
        se traga: quien llame tiene que dejar constancia de que la reserva sigue
        pendiente, que es lo que `pendientes()` permite comprobar.
        """
        ...

    def recuperar(self, referencia: str) -> bytes:
        """Los bytes del archivo guardado bajo esa referencia · C2A.

        La cuarta operación, y la primera que **lee**. Existe porque sin ella un
        investigador no puede ver lo que aprueba: `EQ-023` le encarga verificar
        la autorización, y verificar un documento que no se puede abrir es
        firmar a ciegas.

        ⚠️ **Devuelve bytes, no una URL, y eso es el contrato entero.** Una
        variante que devolviera un enlace temporal parecería más cómoda y
        rompería `EQ-021`: un enlace es transferible, sobrevive a la sesión que
        lo pidió y acaba pegado en un chat. Los bytes sólo llegan a quien ya se
        autorizó en **esta** petición, y el borde los sirve `inline` sin caché
        compartida.

        `referencia` es la que devolvió `reservar()` y que PostgreSQL conserva;
        quien llama la obtuvo de `PuertoEvidenciaDelRepresentante.
        referencia_del_documento()` **después** de comprobar el rol. Este puerto
        no autoriza a nadie: no sabe quién pregunta y no debe saberlo — mezclar
        custodia del archivo con permisos habría puesto la regla de `EQ-023` en
        dos sitios.

        ⚠️ **Sirve una carga CONFIRMADA y sólo ésa.** Una reserva provisional
        levanta `DocumentoPendienteDeConfirmacion` — ver esa clase para el
        razonamiento entero. En una frase: la petición que la dejó así respondió
        503 a quien subió el documento, así que enseñársela a un revisor lo
        pondría a resolver sobre algo que el sistema declaró no registrado.

        Que siga siendo enumerable por `pendientes()` es lo que permite
        reconciliarla después; poder **leerla** no hace falta para eso y es lo
        que la convertía en revisable por accidente.

        Levanta `AlmacenamientoNoConfigurado` si no hay almacenamiento,
        `AlmacenamientoNoDisponible` si lo hay y falló, `DocumentoAusente` si
        respondió y no tiene ese archivo, y `DocumentoPendienteDeConfirmacion` si
        lo tiene sin promover. Nunca devuelve bytes vacíos para disimular ninguno
        de los cuatro.
        """
        ...

    def pendientes(self) -> tuple[str, ...]:
        """Las reservas que no se confirmaron ni se retiraron.

        Es la **reserva durable y auditable** del hito R4: si la compensación
        falla, la carga no desaparece en silencio y esta lista la encuentra. Un
        despliegue sano la devuelve vacía; cualquier elemento aquí es un archivo
        privado que entró y quedó a medias, y merece una mirada.
        """
        ...

    def esta_configurado(self) -> bool:
        """Si este despliegue puede aceptar evidencia.

        Lo consulta `/api/salud` para declarar la carencia, igual que
        `identidad.esta_configurado()` hace con el cliente de Google. Un
        despliegue sin almacenamiento no es una avería: es una configuración
        incompleta, y la diferencia importa para quien la resuelve.
        """
        ...
