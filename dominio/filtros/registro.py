"""
registro.py — Filtro 12 · el turno completo, en ruta fría (`PM-B20`)
=========================================================================

`ADR-001` §6.3 reserva el filtro 12 desde el primer día, y `dominio/
orquestador.py` dejó `ejecutar_fria()` lista desde `PM-B13` sin que ningún
filtro la ocupara todavía —«hoy no hace nada... ningún filtro construido
hasta ahora es "fría"»—. Este es el primero.

Por qué es fría, literal
------------------------------
`08-Contrato-del-Turno.md` §12 ya lo separaba: la persistencia del registro
**no** es parte de lo que el estudiante espera para recibir su respuesta.
`ADR-003` §6.5 S3 fija la regla que este filtro respeta por construcción: no
escribe nada de lo que la ruta caliente ya decidió, solo lo conserva. Nunca
se ejecuta antes de que el turno haya respondido — es responsabilidad de
quien compone el sistema llamarlo después, con `Orquestador.ejecutar_fria()`.

Qué hace, y qué no
----------------------
Traduce `ContextoTurno` a `dominio.puertos.registro.RegistroDeTurno` —las
mismas trazas que `RF-ORQ-14` ya garantiza, sin aplanarlas— y se lo entrega
al puerto. **No decide el almacén**: `DD-08` fija archivo con fila de
referencia, y eso es del adaptador (`adaptadores/salientes/registro/
archivo.py`), no de este filtro.

**No falla el turno si el registro falla.** Es ruta fría: para cuando este
filtro corre, la respuesta ya se emitió. Si `puerto.registrar_turno_completo`
lanza, este filtro deja subir la excepción como cualquier otro —
`Orquestador._ejecutar_lista` ya la envuelve en `ErrorDeOrquestacion`—, y es
decisión de quien compone el sistema si un fallo de registro en frío debe
alertar o solo quedar en el propio log de la aplicación; no es una decisión
de este filtro tomarla en silencio.

✅ La limitación que este docstring declaró, y que se cerró al verla ocurrir
------------------------------------------------------------------------------
Hasta el 2026-08-14 aquí decía que `ContextoTurno` no llevaba identificador de
turno propio, que `RegistroDeTurno.turno` usaba `identificador_sesion`, y que
por tanto **dos turnos de la misma sesión compartían clave de registro**. Estaba
escrito y se dejó para que alguien lo revisara antes de tocar `ContextoTurno`
otra vez.

**Lo que faltaba no era el permiso, era ver la consecuencia.** `PM-V15` corrió
la primera conversación de varios turnos del proyecto y de cinco turnos quedó
**uno**: cada uno sobrescribía el archivo y la fila del anterior. `RF-REG-01`
pide poder reconstruir *cualquier* turno, y con una clave por sesión eso era
falso — no en teoría, en el disco.

`ContextoTurno.identificador_turno` lo cierra, y es **el mismo** que viaja al
estudiante en `CuerpoTurno.turno`: un turno que alguien reporta se puede
encontrar ahora en el registro, que es lo que `RU-12` necesita poder hacer.
"""

from __future__ import annotations

from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno
from dominio.puertos.factores import PuertoFactores
from dominio.puertos.registro import (
    RELACION_OBSERVABLE,
    EntradaDeTurno,
    MaterialRegistrado,
    PuertoRegistro,
    RegistroDeTurno,
    TrazaRegistrada,
)


class FiltroRegistro(Filtro):
    """Filtro 12 de `ADR-001` §6.3. Ruta fría — `PM-B20`."""

    nombre = "registro del turno completo"
    ruta = "fría"

    def __init__(
        self, puerto: PuertoRegistro, puerto_entradas: PuertoRegistro | None = None,
        puerto_factores: PuertoFactores | None = None,
    ) -> None:
        """DOS colaboradores, y no es un descuido · `PM-B37`, 2026-08-18.

        `PuertoRegistro` declara cinco métodos y **ningún adaptador implementa
        los cinco**: `archivo.py` cubre `registrar_turno_completo` (`DD-08`, el
        archivo con su fila de referencia) y `historial.py` cubre
        `registrar_turno` (`RF-REG-01`, el texto literal). Son almacenes con
        disciplinas distintas —uno se reescribe, el otro no— y juntarlos
        repetiría lo que `archivo.py` argumenta para no juntar los cinco.

        Así que este filtro recibe los dos y llama a cada uno por su método, en
        vez de exigir un adaptador compuesto que existiría solo para satisfacer
        la forma del `Protocol`.

        `puerto_entradas` es `None` cuando no hay `AGENTE_BD`: entonces el
        turno se registra igual —trazas y latencias— y **el historial no se
        escribe**, lo cual `composicion.py` declara en `faltantes` y
        `GET /api/salud` publica. Degradar sin decirlo es lo que `A4` cerró.
        """
        self._puerto = puerto
        self._puerto_entradas = puerto_entradas
        self._puerto_factores = puerto_factores

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        trazas = tuple(
            TrazaRegistrada(
                filtro=t.filtro, latencia_ms=t.latencia_ms, ruta=t.ruta, metadatos=t.metadatos
            )
            for t in ctx.trazas
        )
        registro = RegistroDeTurno(
            # `PM-V15`, 2026-08-14. Antes era `identificador_sesion`, y por eso
            # cada turno pisaba al anterior. El respaldo se conserva para el
            # turno que llega sin identidad —una prueba, un guion— porque
            # perder el registro entero sería peor que compartir clave.
            turno=ctx.identificador_turno or ctx.identificador_sesion,
            identificador_sesion=ctx.identificador_sesion,
            # `DD-27`, 2026-08-18. El respaldo vive AQUÍ y no en el borde, en
            # el mismo punto de uso que el de `turno` y por el mismo motivo:
            # una decisión, un sitio. Y no es un respaldo de adorno —
            # `rutas/turno.py:326` deja el sujeto vacío cuando
            # `modulo_conductual_habilitado()` es falso (`RL-09`, sin edad
            # declarada), incluso con la sesión autenticada. Sin esta línea,
            # esos turnos chocarían contra el `CHECK` del esquema y el
            # `contextlib.suppress` del borde se tragaría el fallo.
            identificador_sujeto=ctx.identificador_sujeto or ctx.identificador_sesion,
            nivel_divulgacion=ctx.nivel_divulgacion,
            trazas=trazas,
            # `EQ-031` · se persiste tal como llegó del borde. Este filtro no
            # lo deriva ni lo corrige: derivarlo aquí exigiría conocer el rol,
            # que es justo lo que el dominio no tiene ni debe tener.
            contexto_de_uso=ctx.contexto_de_uso,
        )
        # `DD-27`, 2026-08-18 · se valida ANTES de entregar al puerto, y el
        # fallo sube. `RegistroDeTurno.validar()` existía desde el principio y
        # no lo llamaba nadie — el `CHECK` del esquema habría atrapado un
        # sujeto vacío, pero como un error de SQL opaco, y la ruta fría lo
        # traga (`http/turno.py::_registrar_en_frio`). Un mensaje del dominio
        # dice QUÉ falta; «violates check constraint» dice dónde reventó.
        #
        # Sube en vez de degradar en silencio: `Orquestador._ejecutar_lista` ya
        # lo envuelve en `ErrorDeOrquestacion`, y decidir qué hacer con un
        # fallo de ruta fría es de quien compone el sistema, no de este filtro
        # — está escrito arriba, en este mismo docstring.
        fallos = registro.validar()
        if fallos:
            raise ValueError(f"registro del turno no admisible: {'; '.join(fallos)}")

        # SE VALIDA TODO ANTES DE ESCRIBIR NADA. Si las voces se validaran
        # sobre la marcha, un turno con la marca temporal mal puesta dejaría el
        # registro completo escrito y el historial a medias — y la ruta fría se
        # traga la excepción, así que nadie vería que quedó descuadrado.
        entradas = self._entradas_del_turno(ctx, registro.identificador_sujeto)
        for entrada in entradas:
            fallos = entrada.validar()
            if fallos:
                raise ValueError(
                    f"entrada de turno no admisible ({entrada.autor}): {'; '.join(fallos)}"
                )

        self._puerto.registrar_turno_completo(registro)
        if self._puerto_entradas is not None:
            for entrada in entradas:
                self._puerto_entradas.registrar_turno(entrada)

        factores_guardados = self._puerto_factores.registrar(ctx) if self._puerto_factores is not None else False

        meta = {
            "trazas_registradas": len(trazas),
            "lectura_conductual_guardada": factores_guardados,
            "latencia_total_ms": registro.latencia_total_ms,
            # Cuántas VOCES se registraron. Dos en un turno completo; una si el
            # sistema no llegó a decir nada y tampoco se degradó de forma
            # explicable. Cero significaría que el historial no se escribió, y
            # eso se ve en la traza en vez de deducirse.
            "voces_registradas": len(entradas) if self._puerto_entradas is not None else 0,
        }
        return ctx, meta

    def _entradas_del_turno(self, ctx: ContextoTurno, sujeto: str) -> list[EntradaDeTurno]:
        """Las dos voces de este turno · `RF-REG-01`, `T-04`, `T-05`.

        `EntradaDeTurno` lo dice: *«el mismo turno produce (al menos) dos
        entradas, una por lado de la conversación»*. Aquí se construyen; quien
        las guarda es el adaptador.

        **El texto va literal** (`T-05`): `ctx.texto_estudiante` y no
        `ctx.expresiones`, que es lo que el filtro 1 normalizó y ya viaja en
        las trazas.

        **La voz del sistema es la respuesta, o la degradación** (`T-04`). Un
        turno degradado entra al historial con la explicación **marcada**, para
        que el hilo diga «aquí el sistema no pudo responder» en vez de tener un
        hueco — pero marcada, o presentaría una disculpa como si fuera
        enseñanza.
        """
        comun = {
            "turno": ctx.identificador_turno or ctx.identificador_sesion,
            "identificador_sesion": ctx.identificador_sesion,
            "identificador_sujeto": sujeto,
            "momento": ctx.momento,
            # `EQ-016`, hito B3 · las dos voces del turno se recogen bajo el
            # mismo consentimiento; separarlas permitiría que la del estudiante
            # y la del sistema quedaran ligadas a autorizaciones distintas.
            "consentimiento_evento": ctx.consentimiento_evento,
            # `EQ-031` · las dos voces del turno comparten contexto, por el
            # mismo motivo que comparten consentimiento: separarlas dejaría la
            # pregunta del estudiante clasificada de una forma y la respuesta
            # del sistema de otra, y un agregado excluiría media conversación.
            "contexto_de_uso": ctx.contexto_de_uso,
        }
        entradas = []
        if ctx.texto_estudiante.strip():
            entradas.append(
                EntradaDeTurno(**comun, autor="estudiante", contenido=ctx.texto_estudiante)
            )
        if ctx.respuesta.strip():
            entradas.append(
                EntradaDeTurno(
                    **comun,
                    autor="sistema",
                    contenido=ctx.respuesta,
                    # `PM-B25` · lo que el estudiante vio, con su sello y sus
                    # citas. Sin esto, `validar()` rechaza la entrada en cuanto
                    # la narración lleve una marca `{{...}}`.
                    bloques=ctx.bloques_emitidos,
                    citas=ctx.citas_emitidas,
                    nivel=ctx.nivel_emitido,
                    procedencia_origen=ctx.procedencia_origen,
                    procedencia_referencia=ctx.procedencia_referencia,
                    # Fase 5 · el mismo material que la cadena de arriba
                    # resume, aquí con su orden y su relación. Ver
                    # `_material_del_turno`.
                    material=_material_del_turno(ctx),
                    conceptos=ctx.conceptos_emitidos,
                )
            )
        elif ctx.degradacion.strip():
            entradas.append(
                EntradaDeTurno(
                    **comun, autor="sistema", contenido=ctx.degradacion, degradado=True
                )
            )
        return entradas


def _material_del_turno(ctx: ContextoTurno) -> tuple[MaterialRegistrado, ...]:
    """Los fragmentos que ESTE turno recuperó · Fase 5 · paquete 5B.

    **El mismo criterio que `procedencia_origen`**, y por eso se calcula al
    lado. El borde declara `corpus` cuando `recuperacion.utilizable`, es decir
    cuando hubo fragmentos y el turno **no** operó en modo sin fuente
    (`ADR-006` U3). Con `sin_fuente`, el filtro 5 recuperó por debajo del umbral
    y no se inyectó contexto: registrar aquello como «material recuperado para
    el turno» diría que la respuesta se apoyó en algo que nunca entró.

    Las dos mitades tienen que decir lo mismo. Si una lista material y la otra
    declarara `sin-fuente`, el hilo se contradiría a sí mismo.

    ⚠️ **La relación es `recuperado` y nada más.** Es lo único observable: el
    filtro 5 pidió al corpus y esto es lo que trajo. Que la respuesta lo use, o
    que una frase concreta se apoye en uno, son afirmaciones que hoy nadie
    produce — y `RELACIONES_DEL_MATERIAL` las reserva sin escribirlas.
    """
    recuperacion = ctx.recuperacion
    if recuperacion is None or not recuperacion.utilizable:
        return ()

    similitudes = recuperacion.similitudes
    material: list[MaterialRegistrado] = []
    vistos: set[str] = set()
    # Dos índices distintos, y confundirlos daría a cada pieza la puntuación de
    # otra: `posicion` es dónde venía en lo que devolvió el recuperador —y es el
    # índice de su similitud— mientras que `orden` es dónde queda después de
    # descartar repetidos.
    for posicion, fragmento in enumerate(recuperacion.fragmentos):
        # Un recuperador que devolviera el mismo fragmento dos veces dejaría el
        # material duplicado. Se conserva la primera aparición, que es la de
        # mayor puntuación, y la segunda no se cuenta: es la misma fuente.
        if fragmento.identificador in vistos:
            continue
        vistos.add(fragmento.identificador)
        material.append(
            MaterialRegistrado(
                fragmento=fragmento.identificador,
                obra=fragmento.procedencia.obra,
                orden=len(material),
                relacion=RELACION_OBSERVABLE,
                # `ADR-006` U5 pidió conservar la distribución de puntuaciones.
                # `None` cuando el recuperador no puntúa —un doble de pruebas,
                # un índice léxico sin escala— y no cero, que diría otra cosa.
                similitud=(
                    float(similitudes[posicion]) if posicion < len(similitudes) else None
                ),
            )
        )
    return tuple(material)
