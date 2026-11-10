"""
no_configurado.py — El almacenamiento privado que todavía no existe (`EQ-021`)
===============================================================================

`PuertoAlmacenamientoPrivado` cuando el equipo aún no ha resuelto la carpeta
institucional, sus credenciales y su custodia. `DECISIONES.md` lo tiene como
decisión abierta:

    «Credenciales, carpeta institucional y custodia operativa del almacenamiento
    privado de autorizaciones, sin versionar secretos ni enlaces personales.»

Por qué esto y no un adaptador de Drive
-------------------------------------------------
Porque escribirlo exigiría decidir cómo se autentica, en qué carpeta escribe y
quién puede leerla — tres decisiones de custodia que no son de un ejecutor. El
paquete B tiene prohibido conectar Drive, y este adaptador es la forma de que
esa prohibición sea **visible en el sistema** en vez de un hueco.

Por qué falla y no guarda en disco
---------------------------------------------
Un adaptador de conveniencia que escribiera el PDF en una carpeta local sería
peor que ninguno: aceptaría la evidencia, devolvería una referencia y dejaría un
documento firmado por un representante legal fuera de toda custodia acordada.
`EQ-024` prohíbe el éxito parcial y esto es exactamente uno.

Lo que sí hace es fallar **con el error que corresponde**: `AlmacenamientoNoConfigurado`
—que no es transitorio— y no `AlmacenamientoNoDisponible`, para que quien lo lea
sepa que no se arregla esperando.

Qué hace falta para sustituirlo
-------------------------------------------
Una decisión del equipo sobre carpeta, credencial y custodia, y después un
adaptador que implemente el mismo puerto. Ninguna otra parte del sistema cambia:
`rutas/consentimiento.py` recibe el puerto por composición.


"""

from __future__ import annotations

from dominio.puertos.almacenamiento_privado import AlmacenamientoNoConfigurado


class AlmacenamientoNoConfiguradoAdaptador:
    """`PuertoAlmacenamientoPrivado` que declara su ausencia y no finge nada."""

    def reservar(self, contenido: bytes, *, sujeto_google: str, intento: int) -> str:
        """Nunca reserva. Ver el docstring del módulo.

        Falla en la **primera** de las tres fases, que es lo que hace que las
        otras dos no lleguen a importar: sin reserva no hay nada que confirmar ni
        que retirar, y la ruta responde mantenimiento antes de tocar PostgreSQL.

        El mensaje no nombra al titular ni al intento: un error acaba en una
        consola y en un registro, y ahí no tiene por qué aparecer quién intentó
        subir la autorización de su representante.
        """
        raise AlmacenamientoNoConfigurado(
            "el almacenamiento privado de EQ-021 no está configurado: la carpeta, "
            "la credencial y la custodia siguen siendo una decisión del equipo"
        )

    def confirmar(self, referencia: str) -> None:
        """Inalcanzable por el camino normal —`reservar()` ya falló—, y aun así
        declarada: un puerto a medio implementar es una excepción de atributo en
        la primera petición, no un rechazo con motivo."""
        raise AlmacenamientoNoConfigurado(
            "el almacenamiento privado de EQ-021 no está configurado"
        )

    def retirar(self, referencia: str) -> bool:
        """Igual que `confirmar()`. Nunca hubo nada que retirar."""
        raise AlmacenamientoNoConfigurado(
            "el almacenamiento privado de EQ-021 no está configurado"
        )

    def recuperar(self, referencia: str) -> bytes:
        """Nunca recupera nada, porque nunca guardó nada · C2A.

        Levanta y **no devuelve bytes vacíos**. Un PDF de cero bytes pasaría por
        una respuesta con éxito, el visor de C2B mostraría una página en blanco y
        un investigador podría aprobar una autorización que jamás existió: el
        éxito parcial de `EQ-024` en su forma más cara.

        `AlmacenamientoNoConfigurado` y no `AlmacenamientoNoDisponible` por el
        mismo motivo que `reservar()`: esto no se arregla esperando. Tampoco es
        `DocumentoAusente`, que significa «hay almacén y le falta este archivo» —
        aquí no hay almacén.

        El mensaje no nombra la referencia ni la evidencia. Un error acaba en una
        consola y en un registro, y la referencia del documento privado de un
        menor no tiene por qué estar ahí.
        """
        raise AlmacenamientoNoConfigurado(
            "el almacenamiento privado de EQ-021 no está configurado: no hay "
            "de dónde recuperar la autorización del representante"
        )

    def pendientes(self) -> tuple[str, ...]:
        """Vacío, y es cierto: aquí no se reservó nunca nada.

        No levanta, a diferencia de las otras tres. Preguntar «¿quedó algo a
        medias?» tiene respuesta aunque no haya almacenamiento, y esa respuesta
        es «no»; hacerla fallar obligaría a quien vigile las reservas pendientes
        a distinguir un despliegue sin configurar de uno con problemas.
        """
        return ()

    def esta_configurado(self) -> bool:
        return False

    def estado_publicable(self) -> dict:
        """Lo que `/api/salud` publica de un despliegue sin custodia · `D3`.

        El mismo método que `AlmacenamientoEnSistemaDeArchivos`, y con la misma
        forma, para que `rutas/salud.py` no tenga que preguntar de qué adaptador
        se trata. Un `if` allí habría sido el sitio donde, el día que apareciera
        un tercer adaptador, la salud se quedara callada.

        `disponible: False` y no `True`: no hay nada disponible. Y
        `reservas_pendientes: 0` porque `pendientes()` ya responde eso mismo — no
        se omite la clave, para que quien vigile las reservas no tenga que
        distinguir «no hay» de «esta versión no lo publica».
        """
        return {
            "configurado": False,
            "tipo": "no_configurado",
            "disponible": False,
            "reservas_pendientes": 0,
        }
