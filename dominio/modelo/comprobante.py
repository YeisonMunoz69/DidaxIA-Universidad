"""
comprobante.py — La huella del recibo, y la forma que tiene una huella
=======================================================================

Dos cosas pequeñas que estaban en dos sitios equivocados y ahora están en uno.

`comprobante_de()` vivía dentro de `rutas/consentimiento.py`
--------------------------------------------------------------
Era una **regla del acto** escondida en un adaptador entrante: el algoritmo que
produce el comprobante que `EQ-021` exige conservar en cada evento. Mientras el
único que lo calculaba era el router, pasaba por detalle de presentación.

`D1B` lo deja de ser. La decisión conjunta calcula el comprobante **dentro de la
transacción de escritura** —tiene que hacerlo: la versión y su huella se
resuelven allí, con la fila de la persona bloqueada— y un adaptador saliente no
puede importar una función de un adaptador entrante sin invertir la dirección
que `ADR-001` §7.2 fija.

⚠️ **El algoritmo no cambia ni un byte.** Sigue siendo el SHA-256 de las partes
unidas por `␟` (U+241F), en el mismo orden: sujeto, código de versión, huella
del documento y decisión. `pruebas/unidad/test_decision_conjunta_contratos.py`
lo comprueba contra vectores fijos, y la ruta de revocación —que lo sigue
usando— lo importa de aquí en vez de tener el suyo.

`SHA256` estaba escrito dos veces
------------------------------------
`dominio/modelo/consentimiento.py` y `dominio/modelo/menores.py` llevaban cada
uno su `re.compile(r"^[0-9a-f]{64}$")`. Dos redacciones de la misma forma son
dos formas en cuanto alguien corrija una —admitir mayúsculas en un sitio y no en
el otro dejaría pasar por una puerta lo que la otra rechaza—, y ahora la
decisión conjunta necesitaba una tercera.


"""

from __future__ import annotations

import hashlib
import re

#: Un SHA-256 en minúsculas. Se exige la **forma**, nunca un valor concreto: la
#: huella del contenido y el comprobante son huellas de algo que existe fuera
#: del dominio —el texto publicado, el recibo de lo que se mostró— y ningún
#: modelo puede calcularlos sin inventárselos.
SHA256 = re.compile(r"^[0-9a-f]{64}$")

#: El separador de las partes del comprobante: U+241F, «symbol for unit
#: separator». No puede aparecer dentro de un sujeto de Google, de un código de
#: versión ni de una decisión, así que dos juegos de partes distintos no pueden
#: producir la misma cadena por concatenación.
SEPARADOR = "␟"


def comprobante_de(*partes: str) -> str:
    """El SHA-256 del recibo de lo que la persona vio y aceptó (`EQ-021`).

    Se calcula en el servidor y **no se recibe del cliente**: un comprobante que
    el navegador enviara probaría lo que el navegador quisiera.

    Las partes que entran son sujeto, código de versión, huella del documento y
    decisión. **El momento no entra**, y no por descuido: lo asigna PostgreSQL
    al insertar, así que no existe todavía cuando esto se calcula. Lo que
    identifica el acto concreto es el recibo completo —secuencia y momento
    reales de la fila, junto a esta huella—; el comprobante identifica *qué se
    aceptó*, no *cuándo*.

    La consecuencia es deliberada y hay que saberla: dos actos iguales del mismo
    sujeto sobre la misma versión tienen el **mismo** comprobante, y por eso
    quien audite uno puede recomputarlo sin conocer el reloj del servidor.
    """
    return hashlib.sha256(SEPARADOR.join(partes).encode("utf-8")).hexdigest()
