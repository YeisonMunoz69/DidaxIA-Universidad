"""
registro.py — Puerto de registro y telemetría (S12)
=======================================================

Cuarto de los siete puertos de `ADR-001` §6.2. `RF-REG-01` exige registrar
**la totalidad de los turnos** con marca temporal, autor y contenido literal;
`RF-REG-02` exige que **cada actualización del vector conductual** sea
trazable a su evidencia — que es, casi palabra por palabra, lo que `ADR-003`
§6.6 promete: *«un registro de `(turno, señal, regla aplicada, valor previo,
valor nuevo, λ aplicado, certeza)`, sin sobrescribir la versión anterior»*.

Es la ruta **fría** (filtro 12, `ADR-001` §6.3): no condiciona la respuesta
del turno, así que ninguna operación de este puerto tiene presupuesto de
`RNF-EFI-01` que cuidar.

Por qué tres tipos de registro y no uno genérico
----------------------------------------------------
`ADR-003` §6.2 no es una preferencia de estilo: es la decisión que cierra
**DSC-04**. R-A (afectivo), R-C (conceptual) y R-E (estratégico) tienen
naturaleza distinta —continua con decaimiento, máquina de estados que **no**
decae, secuencia de eventos sobre ventana— y **«no comparten espacio de
representación»** (`ADR-003` K1, crítico).

Una tabla `(turno, dimensión, valor)` para los tres colapsaría la separación
justo donde `ADR-003` más insiste en que no colapse: R-C no tiene un
*«valor»* en `[0,1]`, tiene un **estado** de una máquina de cuatro; R-E no
tiene *«valor»* en absoluto, tiene un **contador** sobre una ventana.
Forzarlos al mismo esquema repetiría, en el registro, el error de
`BehavioralVector` que `ADR-003` corrigió en el modelo — es la advertencia
que el encargo de esta sesión hace explícita: *«si acabas con una tabla
plana, algo se perdió»*.

Qué cubre esta sesión, y qué no
------------------------------------
`RF-REG-01` a `RF-REG-08` declaran ocho cosas que registrar. La sesión que
abrió este archivo cubrió las dos que `ADR-003` hace estructurales: **el
turno** (`RF-REG-01`) y **los tres registros conductuales con su evidencia**
(`RF-REG-02`), y dejó dicho, literal, que verificación (`RF-REG-03`), latencia
por componente (`RF-REG-04`), fallos (`RF-REG-05`), estrato de decisión
pedagógica (`RF-REG-06`) y contexto recuperado (`RF-REG-07`) ya tienen su
información disponible en `ContextoTurno.trazas` —es lo que `RF-ORQ-14`
garantiza—, así que cubrirlas sería «añadir métodos a este puerto cuando haga
falta, no rediseñarlo». `PM-B20` es ese «cuando haga falta»: el filtro 12
—ruta fría, `dominio/filtros/registro.py`— necesita persistir el turno
completo para poder reconstruirlo y contrastar qué calculó el motor simbólico
frente a qué narró el generador, que es literalmente RF-REG-03 y RF-REG-06 a
la vez sobre el mismo turno.

**Un método, no cinco.** Las cinco piezas —verificación, latencia, fallos,
estrato pedagógico, contexto recuperado— viven todas en el mismo
`ContextoTurno.trazas` de un único turno; partirlas en cinco llamadas
obligaría a reconstruir el mismo turno cinco veces del lado del adaptador, o
a que el filtro 12 llame cinco métodos por turno sin que ninguno por separado
sea reconstructivo. `registrar_turno_completo()` recibe el turno entero y dejó
la reconstrucción como una propiedad de la forma, la misma razón por la que
`RF-ORQ-14` no se implementa función por filtro.

Lo que este puerto NO decide
--------------------------------
**No calcula nada.** No aplica la fórmula de decaimiento de `ADR-003` N2, no
avanza la máquina de estados de R-C ni cuenta la ventana de R-E — eso es
`dominio/modelo/estudiante.py` (todavía 🆕). Este puerto solo **conserva** lo
que ya se calculó, con la forma que le corresponde.

**No decide el almacén.** `ADR-001` §6.2 dice *«archivo estructurado por
sesión»*; qué formato concreto —JSONL, un archivo por sesión, uno por día—
es del adaptador, que tampoco existe todavía.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from dominio.modelo.contexto_de_uso import ContextoDeUso

#: R-A nivel 1 (ruta caliente, `ADR-003` S1) y nivel 2 (ruta fría, S2).
#: `ADR-003` §6.2. Una lista y no un `Enum` porque `RF-ADM-06` los declara
#: configurables — añadir un sub-componente de nivel 2 no debe exigir tocar
#: código, solo esta tabla si algún día se necesita validarla contra algo
#: más que la forma del dato.
SUBCOMPONENTES_AFECTIVOS = (
    "PS-Anx", "FAH", "autoeficacia",  # nivel 1 · ruta caliente · S1
    "E-Anx", "aburrimiento", "autoconcepto",  # nivel 2 · ruta fría · S2
    "utilidad_percibida", "identidad_matematica_negativa",
)

#: `ADR-003` §6.2: máquina de estados de cuatro posiciones. `RF-MEV-13`.
ESTADOS_CONCEPTUALES = ("no_detectada", "activa", "remediada", "recurrente")

#: `ADR-003` N5: el estado se actualiza por turno; el rasgo, al cierre de
#: sesión. Nunca se funden (C5) — por eso viajan con esta etiqueta y no como
#: dos campos numéricos que alguien podría promediar por descuido.
ALCANCES = ("estado", "rasgo")


@dataclass(frozen=True)
class BloqueRegistrado:
    """Un bloque del cuerpo emitido, ya en su forma de persistir · `PM-B25`.

    Es la misma información que `adaptadores/entrantes/http/turno.py::Bloque`
    —tipo, contenido, sello, alternativo—, pero como tipo de **este puerto** y
    no del borde: exactamente el mismo argumento que `TrazaRegistrada` da para
    `TrazaFiltro`. `ADR-001` §7.2 separa qué persiste de qué ocurrió, y el
    dominio no debe importar el tipo del adaptador para poder guardarlo.

    ⚠️ **`sello` es el campo que justifica todo esto.** `ADR-014` §5.1 lo
    define con dos valores y ninguno más: `verificado` dice que el motor
    simbólico comprobó esa matemática; `generado`, que la escribió el modelo.
    Un hilo que no distingue las dos cosas **pierde la única garantía
    pedagógica que este sistema ofrece**, y hasta hoy el historial no la
    guardaba.
    """

    tipo: str
    contenido: str
    sello: str
    alternativo: str = ""

    SELLOS = ("verificado", "generado")
    #: `§5` del contrato: sin texto alternativo no son accesibles.
    EXIGEN_ALTERNATIVO = ("notacion", "grafica")

    def validar(self) -> list[str]:
        fallos = []
        if self.sello not in self.SELLOS:
            fallos.append(f"sello inválido «{self.sello}»: §5.1 admite solo dos")
        if not self.contenido.strip():
            fallos.append("bloque sin contenido")
        if self.tipo in self.EXIGEN_ALTERNATIVO and not self.alternativo.strip():
            fallos.append(f"«{self.tipo}» exige alternativo (§5, accesibilidad)")
        return fallos


@dataclass(frozen=True)
class CitaRegistrada:
    """Una expresión citada, con su marca · `ADR-014` §5.4, `PM-B25`.

    **Sin esto, la narración guardada es irreconstruible.** El texto emitido
    dice «Para derivar {{c1}}, ¿qué función está adentro?»: la marca sin su
    expresión no se puede renderizar, y quien lea el hilo verá `{{c1}}` crudo.

    Es el mismo fallo que `PM-B25` corrigió en pantalla el 2026-08-11 —el piso
    emitía la marca sin resolver— reaparecido en el historial. El aviso estaba
    escrito en `http/turno.py`, veinte líneas encima del sitio donde se
    reintrodujo.
    """

    marca: str
    expresion: str

    def validar(self) -> list[str]:
        fallos = []
        if not self.marca.strip():
            fallos.append("cita sin marca: no hay dónde sustituirla")
        if not self.expresion.strip():
            fallos.append(f"cita «{self.marca}» sin expresión")
        return fallos


#: Qué relación tiene un fragmento del corpus con la respuesta de un turno.
#: **Cerrada, y hoy sólo se escribe la primera.** Fase 5 · paquete 5B.
#:
#: | Valor | Qué afirma | ¿Se produce hoy? |
#: |---|---|---|
#: | `recuperado` | el filtro 5 lo trajo y entró al contexto del prompt | **sí** |
#: | `soporte_del_turno` | la respuesta se apoya en él de forma general | no |
#: | `cita_literal` | la respuesta reproduce un pasaje suyo | no |
#: | `respaldo_de_afirmacion` | una afirmación concreta se apoya en él | no |
#:
#: Los tres últimos existen para que el contrato admita trazabilidad fina sin
#: rehacer el esquema. **No se escriben mientras el motor no los produzca**: el
#: encargo de Fase 5 lo prohíbe con estas palabras — *«si el motor no relaciona
#: una oración con un fragmento, no lo simules»*.
RELACIONES_DEL_MATERIAL = (
    "recuperado",
    "soporte_del_turno",
    "cita_literal",
    "respaldo_de_afirmacion",
)

#: La única relación que el sistema de hoy puede afirmar con verdad.
RELACION_OBSERVABLE = "recuperado"

#: Forma del identificador de fragmento, la misma que el `CHECK` de
#: `15-material-del-turno.sql`. Se repite en los dos sitios a propósito: una
#: fila escrita por SQL crudo tiene que cumplir lo mismo que una escrita por el
#: adaptador, y una sola de las dos comprobaciones dejaría un camino abierto.
_FRAGMENTO = re.compile(r"^F-\d{3}$")
_OBRA = re.compile(r"^[A-Z]{3}$")
_CONCEPTO = re.compile(r"^[A-Za-z0-9:._~-]{1,128}$")


@dataclass(frozen=True)
class MaterialRegistrado:
    """Un fragmento del corpus recuperado para un turno · Fase 5.

    **No guarda el texto.** Vive en `contenido/corpus/fragmentos/`, que es
    contenido versionado; copiarlo aquí crearía una segunda copia que el día
    que `DD-15` obligue a retirar una obra habría que perseguir dentro de la
    base. Lo que se conserva es el vínculo, y eso es justo lo que hace posible
    la propiedad que la fase pide: la evidencia histórica de que un turno
    consultó un material sobrevive aunque ese material deje de poder servirse.

    ⚠️ **`relacion` no se adivina.** Ver `RELACIONES_DEL_MATERIAL`.
    """

    fragmento: str
    obra: str
    orden: int
    relacion: str = RELACION_OBSERVABLE
    #: Similitud con la que entró, si el recuperador la reporta. `None` es «no
    #: consta» —un índice que no puntúa— y **no se sustituye por cero**, que
    #: significaría «no se parecía en nada».
    similitud: float | None = None

    def validar(self) -> list[str]:
        fallos = []
        if not _FRAGMENTO.match(self.fragmento or ""):
            fallos.append(f"identificador de fragmento inválido «{self.fragmento}»")
        if not _OBRA.match(self.obra or ""):
            fallos.append(f"{self.fragmento}: clave de obra inválida «{self.obra}»")
        if self.orden < 0:
            fallos.append(f"{self.fragmento}: orden negativo ({self.orden})")
        if self.relacion not in RELACIONES_DEL_MATERIAL:
            fallos.append(
                f"{self.fragmento}: relación desconocida «{self.relacion}»: "
                f"{RELACIONES_DEL_MATERIAL}"
            )
        if self.similitud is not None and not 0.0 <= self.similitud <= 1.0:
            fallos.append(f"{self.fragmento}: similitud fuera de escala ({self.similitud})")
        return fallos


@dataclass(frozen=True)
class EntradaDeTurno:
    """`RF-REG-01`. Un turno, tal como ocurrió — ni interpretado ni resumido.

    `autor` distingue de quién es `contenido`: el mismo turno produce (al
    menos) dos entradas, una por lado de la conversación, porque `RF-REG-01`
    pide poder **reconstruir la sesión completa**, y una sesión tiene dos
    voces.

    Lo que se guarda es el **texto literal**, sin normalizar (`T-05`, acta del
    2026-08-18): `RF-REG-01` dice «contenido literal», y el normalizado es del
    filtro 1 y ya viaja en las trazas de `RegistroDeTurno`.

    ⚠️ **Este tipo es el que fija la forma de la tabla, no al revés.**
    `05-historial.sql` tiene ocho columnas porque este tipo tiene ocho campos.
    `§6.bis` del encargo dibujaba siete —le faltaban `identificador_sujeto` y
    `degradado`—, y se escribió antes de que el acta decidiera `DD-27` y
    `T-04`. Cada campo dice abajo de qué decisión sale.
    """

    turno: str
    identificador_sesion: str
    #: `DD-27`, 2026-08-18 · la clave por la que `RD-22` borra. **Sin valor por
    #: defecto**, igual que en `RegistroDeTurno` y por el mismo motivo: una
    #: entrada sin sujeto es una fila insuprimible, y eso tiene que doler al
    #: escribir la llamada, no al ejercer un derecho seis meses después.
    #:
    #: `§6.bis` del encargo dibujaba la tabla con esta columna y el tipo no la
    #: tenía. Se añade **aquí primero** porque el esquema se deriva de este
    #: tipo y no al revés; al contrario, la tabla tendría durante un commit dos
    #: columnas que ningún tipo del dominio respalda.
    identificador_sujeto: str
    #: `RF-REG-01`, marca temporal. **ISO-8601 y con zona horaria**, las dos
    #: cosas — `validar()` lo exige.
    #:
    #: ⚠️ **La sella el SERVIDOR, nunca el cliente.** Hoy
    #: `TurnoEntrante.momento` sale del cuerpo de la petición
    #: (`rutas/turno.py`), y atar esta marca ahí dejaría en manos del cliente
    #: tres cosas: el reloj de retención de `C-01` —que cuenta 24 meses desde
    #: aquí—, el orden del historial —el índice es `momento DESC`— y la propia
    #: marca de `RF-REG-01`, que pasaría a ser un valor que el sistema no
    #: avala. Quién la sella se resuelve en el borde; este tipo solo se niega a
    #: aceptar una que no se pueda leer.
    #:
    #: **Sin respaldo silencioso.** Una entrada sin momento no se guarda con
    #: `now()` por descuido: se rechaza. El `DEFAULT now()` de
    #: `05-historial.sql` queda para inserciones manuales por SQL, no para
    #: tapar una entrada mal construida — eso sería el modo mock silencioso de
    #: `CONTEXTO-MAESTRO.md` §5.1 aplicado a una marca temporal.
    momento: str
    autor: str
    contenido: str
    #: `T-04` del acta del 2026-08-18 · si este contenido es la explicación de
    #: una degradación en vez de una respuesta del tutor.
    #:
    #: **Los turnos degradados sí entran al historial**: un hilo con huecos es
    #: peor que uno que dice «aquí el sistema no pudo responder», y `RP-17`
    #: pide degradación explícita **también hacia atrás**. Pero entran
    #: *marcados*, porque un hilo que presenta una disculpa como si fuera
    #: enseñanza es peor que las dos cosas.
    #:
    #: Es un campo y no una convención sobre el texto a propósito: deducirlo de
    #: cómo empieza el contenido ataría el contrato de `T-07.bis` a una cadena,
    #: y cambiar la redacción del mensaje rompería el indicador en silencio.
    degradado: bool = False
    #: `PM-B25`, 2026-08-18 · lo que el estudiante VIO, no solo lo que se
    #: narró. Vacío en la voz del estudiante; en la del sistema son los
    #: bloques del cuerpo emitido, **cada uno con su sello**.
    #:
    #: `contenido` sigue siendo el texto literal que `RF-REG-01` pide y `T-05`
    #: fija. Esto es la otra mitad del mismo requisito: *«poder reconstruir la
    #: sesión completa»*. Una narración sin sus bloques no dice si la
    #: matemática se verificó, y una sin sus citas no se puede ni renderizar.
    bloques: tuple[BloqueRegistrado, ...] = ()
    #: Las expresiones que la narración menciona con marcas `{{...}}`.
    citas: tuple[CitaRegistrada, ...] = ()
    #: `nivel` de divulgación y de dónde salió el material, para poder
    #: responder después «¿esta respuesta tenía respaldo del corpus?».
    nivel: str = ""
    procedencia_origen: str = ""
    procedencia_referencia: str = ""
    #: Fase 5 · el material recuperado, con su orden y su relación.
    #:
    #: **Convive con `procedencia_referencia` y no la sustituye.** Aquélla es
    #: una cadena de identificadores separados por comas y hay filas escritas
    #: con ella; a esas filas no se les puede inventar un orden ni una relación,
    #: así que se leen como están. Las nuevas escriben las dos cosas, y quien
    #: lee distingue por si hay material, no por una fecha.
    material: tuple[MaterialRegistrado, ...] = ()
    #: Fase 8 · identificadores del banco que el cuerpo del sistema expuso.
    #: Vacío significa que el turno no tuvo conceptos observables; no se
    #: infiere ninguno desde el texto ni desde una concepción diagnosticada.
    conceptos: tuple[str, ...] = ()
    #: `EQ-016`, hito B3 · bajo qué evento de consentimiento se recogió esto.
    #:
    #: *«Cada turno referencia el evento de consentimiento vigente al crearse.»*
    #: Sin este vínculo, revocar dejaría el historial sin forma de saber qué se
    #: recogió bajo qué autorización, y la decisión del cierre V-B sobre qué se
    #: conserva no tendría con qué separar.
    #:
    #: **Anulable, y con un significado propio.** `None` es «no consta»: las
    #: filas anteriores a B3 no lo tienen y no se les puede inventar uno. Lo que
    #: no se admite es un cero o una cadena vacía haciéndose pasar por vínculo.
    #:
    #: Lo resuelve el borde —es quien conoce la sesión— y llega aquí ya
    #: decidido, igual que `identificador_sujeto`.
    consentimiento_evento: int | None = None
    #: `EQ-031` · para qué se usó el tutor en este turno.
    #:
    #: Lo deriva el borde del **rol real de la sesión** y llega aquí decidido,
    #: igual que `identificador_sujeto` y `consentimiento_evento`. El valor por
    #: defecto es el del estudiante porque es el único uso que existía antes de
    #: `EQ-031`, así que un llamador antiguo —una prueba, un guion— sigue
    #: escribiendo lo que escribía.
    #:
    #: ⚠️ **No se recalcula al leer.** Un rol se otorga y se revoca (`EQ-023`);
    #: derivarlo en cada consulta haría que un docente que dejó de serlo viera
    #: sus consultas convertirse en actividad de estudiante.
    contexto_de_uso: str = ContextoDeUso.APRENDIZAJE_ESTUDIANTE

    AUTORES = ("estudiante", "sistema")
    #: Marcas de expresión citada, tal como el generador las escribe.
    MARCA = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")

    def validar(self) -> list[str]:
        """Errores de la entrada. Lista vacía significa que es admisible."""
        fallos = []
        if self.autor not in self.AUTORES:
            fallos.append(f"autor desconocido «{self.autor}»: {self.AUTORES}")
        if not self.contenido.strip():
            fallos.append("contenido vacío: no hay nada que reconstruir")
        if not self.identificador_sujeto.strip():
            fallos.append("identificador_sujeto vacío: la fila no se podría suprimir (DD-27)")
        if self.consentimiento_evento is not None and self.consentimiento_evento <= 0:
            # Cero o negativo no es «no consta»: es un vínculo roto que apuntaría
            # a un evento inexistente. `None` es la forma de decir que no lo hay.
            fallos.append("consentimiento_evento no es un identificador de evento válido")
        fallos.extend(self._fallos_del_momento())
        fallos.extend(self._fallos_de_las_marcas())
        for bloque in self.bloques:
            fallos.extend(bloque.validar())
        for cita in self.citas:
            fallos.extend(cita.validar())
        fallos.extend(self._fallos_del_material())
        fallos.extend(self._fallos_de_los_conceptos())
        if self.degradado and self.autor != "sistema":
            # Quien se degrada es el sistema. Una entrada del estudiante marcada
            # así significaría que alguien invirtió los autores al construirla,
            # y el hilo mostraría una disculpa del sistema atribuida a él.
            fallos.append(f"degradado con autor «{self.autor}»: solo el sistema se degrada")
        return fallos

    def _fallos_de_los_conceptos(self) -> list[str]:
        fallos = [
            f"identificador de concepto inválido «{concepto}»"
            for concepto in self.conceptos
            if not _CONCEPTO.fullmatch(concepto or "")
        ]
        repetidos = sorted({c for c in self.conceptos if self.conceptos.count(c) > 1})
        if repetidos:
            fallos.append("conceptos repetidos en el mismo mensaje: " + ", ".join(repetidos))
        if self.conceptos and self.autor != "sistema":
            fallos.append(
                f"conceptos colgados del autor «{self.autor}»: los expone el sistema"
            )
        return fallos

    def _fallos_del_material(self) -> list[str]:
        """El material tiene que ser coherente antes de tocar la base · Fase 5.

        Las tres reglas son las mismas que los `UNIQUE` y los `CHECK` de
        `15-material-del-turno.sql`, dichas en el lenguaje del dominio. No
        sobran: la base atraparía lo mismo como `violates unique constraint`,
        que dice dónde reventó y no qué falta — y la ruta fría se traga las
        excepciones, así que un mensaje ilegible sería un mensaje perdido.
        """
        fallos: list[str] = []
        for pieza in self.material:
            fallos.extend(pieza.validar())

        ordenes = [p.orden for p in self.material]
        if len(set(ordenes)) != len(ordenes):
            fallos.append("dos piezas de material comparten posición: el orden sería indefinido")

        fragmentos = [p.fragmento for p in self.material]
        repetidos = sorted({f for f in fragmentos if fragmentos.count(f) > 1})
        if repetidos:
            # Es el caso del reintento: el mismo turno vuelve a escribirse y su
            # material se duplicaría. El lector mostraría la misma fuente dos
            # veces y los recuentos del OE4 contarían de más.
            fallos.append("material repetido en el mismo mensaje: " + ", ".join(repetidos))

        if self.material and self.autor != "sistema":
            # El material lo recuperó el sistema para construir SU respuesta.
            # Colgarlo de la voz del estudiante diría que el estudiante citó el
            # corpus, que es lo contrario de lo que ocurrió.
            fallos.append(
                f"material colgado del autor «{self.autor}»: lo recupera el sistema"
            )
        return fallos

    def _fallos_de_las_marcas(self) -> list[str]:
        """Ninguna marca `{{...}}` puede guardarse sin su cita · `PM-B25`.

        **Esta es la comprobación que impide la tercera vez.** El 2026-08-11 el
        estudiante vio `{{c1}}` en pantalla y `PM-B25` lo corrigió allí; el
        2026-08-18 el historial volvió a guardar la marca sin la expresión, y
        el hilo habría mostrado `{{c1}}` otra vez —esta vez en el sidebar de
        `PM-F20`—. El aviso llevaba escrito desde entonces en
        `http/turno.py`, veinte líneas encima del sitio donde se reintrodujo.

        Se comprueba **aquí y no en el borde** porque aquí es donde el dato se
        va a quedar: una marca guardada sin su cita ya no se puede reparar
        leyendo la fila.
        """
        marcas = set(self.MARCA.findall(self.contenido))
        for bloque in self.bloques:
            marcas |= set(self.MARCA.findall(bloque.contenido))
        sin_cita = sorted(marcas - {c.marca for c in self.citas})
        if sin_cita:
            return [
                f"marcas sin cita {sin_cita}: el hilo mostraría «{{{{{sin_cita[0]}}}}}» "
                "crudo, que es el fallo de PM-B25"
            ]
        return []

    def _fallos_del_momento(self) -> list[str]:
        """`RF-REG-01`. Que la marca exista, se pueda leer, y sepa de qué zona.

        Se comprueba **aquí y no en el adaptador** para que un formato malo
        falle con un mensaje del dominio en vez de con un error de casteo de
        `psycopg`, que dice dónde reventó y no qué falta. Es la misma razón por
        la que el filtro 12 llama a `validar()` antes de entregar al puerto.

        **La zona no es un detalle de formato.** Sin ella, `2026-08-18T10:00`
        significa cosas distintas según quién lo lea, y de esta marca cuelgan
        el orden del hilo y el plazo de retención de `C-01`. Una hora sin zona
        en un plazo legal es una hora que alguien tendrá que adivinar.
        """
        if not self.momento.strip():
            return ["momento vacío: RF-REG-01 pide marca temporal"]
        try:
            marca = datetime.fromisoformat(self.momento)
        except ValueError:
            return [f"momento no es ISO-8601 legible: «{self.momento}»"]
        if marca.tzinfo is None:
            return [f"momento sin zona horaria: «{self.momento}» (RF-REG-01, C-01)"]
        return []


@dataclass(frozen=True)
class TrazaRegistrada:
    """Una traza de `ContextoTurno.trazas`, ya en su forma de persistir.

    Es la misma información que `dominio/modelo/turno.py::TrazaFiltro` trae
    —filtro, latencia, ruta, metadatos—, pero como tipo de este puerto y no
    del núcleo: `ADR-001` §7.2 separa qué persiste (el borde lo decide) de qué
    ocurrió (el dominio lo decide), y `TrazaFiltro` no sabe que existe un
    almacén, ni debe saberlo.
    """

    filtro: str
    latencia_ms: float
    ruta: str
    metadatos: dict


@dataclass(frozen=True)
class RegistroDeTurno:
    """`RF-REG-03` a `RF-REG-07`, juntos: el turno entero, listo para
    reconstruirse y para contrastar qué se calculó frente a qué se emitió.

    `RF-ORQ-14` ya garantiza que `ContextoTurno.trazas` trae, filtro por
    filtro, su latencia (`RF-REG-04`), sus metadatos —que es donde vive el
    veredicto de cada verificación (`RF-REG-03`), el estrato de decisión
    pedagógica del filtro 6 (`RF-REG-06`, `dominio/filtros/arbitraje.py`) y el
    contexto que recuperó el filtro 5 (`RF-REG-07`)—. Este tipo no vuelve a
    calcular nada de eso: **conserva la forma que `RF-ORQ-14` ya produce**, en
    vez de aplanarla y perder la trazabilidad por componente que la propia
    `RF-REG-04` exige.

    `RF-REG-05` (fallos por componente, diagnosticables) no exige un campo
    aparte: un filtro que falló dentro de la cadena no llega a `trazas` en
    absoluto —`dominio/orquestador.py::ErrorDeOrquestacion` interrumpe antes—,
    así que un turno que sí llegó a este registro **no tuvo fallos que
    diagnosticar**. Un turno degradado no genera `RegistroDeTurno`: genera
    `ErrorDeOrquestacion`, que es a su vez el registro del fallo, con
    `ctx_parcial` como el diagnóstico por componente que `RF-REG-05` pide.
    """

    turno: str
    identificador_sesion: str
    #: `DD-27`, 2026-08-18 · la clave por la que `RD-22` **borra**, que no es
    #: la misma por la que este registro se escribe. Sin ella el adaptador no
    #: puede dejar en la fila nada que una supresión por sujeto sepa encontrar,
    #: y un almacén así «es un almacén que no se puede suprimir».
    #:
    #: **Sin valor por defecto, a propósito.** Un registro al que se le olvidó
    #: el sujeto es una fila insuprimible, y eso tiene que doler al escribir la
    #: llamada, no al ejercer un derecho seis meses después.
    identificador_sujeto: str
    nivel_divulgacion: int
    trazas: tuple[TrazaRegistrada, ...]
    #: `EQ-031` · para qué se usó el tutor en este turno.
    #:
    #: Lo deriva el borde del **rol real de la sesión** y llega aquí decidido,
    #: igual que `identificador_sujeto` y `consentimiento_evento`. El valor por
    #: defecto es el del estudiante porque es el único uso que existía antes de
    #: `EQ-031`, así que un llamador antiguo —una prueba, un guion— sigue
    #: escribiendo lo que escribía.
    #:
    #: ⚠️ **No se recalcula al leer.** Un rol se otorga y se revoca (`EQ-023`);
    #: derivarlo en cada consulta haría que un docente que dejó de serlo viera
    #: sus consultas convertirse en actividad de estudiante.
    contexto_de_uso: str = ContextoDeUso.APRENDIZAJE_ESTUDIANTE

    def validar(self) -> list[str]:
        fallos = []
        if not self.turno.strip():
            fallos.append("turno vacío: no hay qué reconstruir")
        if not self.identificador_sujeto.strip():
            # `DD-27`. El guardia que de verdad detiene esto es el
            # `NOT NULL CHECK (btrim(...) <> '')` de
            # `infraestructura/esquema/04-registro-turno-sujeto.sql`; esto lo
            # dice en el lenguaje del dominio, para quien lea el puerto antes
            # que el esquema.
            fallos.append("identificador_sujeto vacío: la fila no se podría suprimir (DD-27)")
        if not self.trazas:
            fallos.append("sin trazas: RF-ORQ-14 promete al menos una por turno")
        return fallos

    @property
    def latencia_total_ms(self) -> float:
        return sum(t.latencia_ms for t in self.trazas)

    @property
    def latencia_por_componente(self) -> dict[str, float]:
        """`RF-REG-04`, literal: desagregada, no un total."""
        return {t.filtro: t.latencia_ms for t in self.trazas}


@dataclass(frozen=True)
class RegistroAfectivo:
    """R-A · `ADR-003` §6.2 y §6.6. Continuo `[0,1]` por sub-componente, con
    decaimiento — la única de las tres naturalezas que decae.

    Los siete campos después de `subcomponente` son literalmente los que
    `ADR-003` §6.6 promete: *«turno, señal, regla aplicada, valor previo,
    valor nuevo, λ aplicado, certeza»*. `regla_aplicada` no es decoración:
    es lo que permite distinguir un decaimiento temporal (N2) de una
    actualización por la regla del máximo (N3), y `RF-MEV-20` exige poder
    hacer esa distinción después.
    """

    turno: str
    subcomponente: str
    senal: str
    regla_aplicada: str
    valor_previo: float
    valor_nuevo: float
    lambda_aplicado: float
    certeza: float
    alcance: str

    def validar(self) -> list[str]:
        fallos = []
        if self.subcomponente not in SUBCOMPONENTES_AFECTIVOS:
            fallos.append(
                f"sub-componente desconocido «{self.subcomponente}»: "
                f"{SUBCOMPONENTES_AFECTIVOS}"
            )
        if self.alcance not in ALCANCES:
            fallos.append(f"alcance desconocido «{self.alcance}»: {ALCANCES}")
        for nombre, valor in (
            ("valor_previo", self.valor_previo),
            ("valor_nuevo", self.valor_nuevo),
            ("lambda_aplicado", self.lambda_aplicado),
            ("certeza", self.certeza),
        ):
            if not 0.0 <= valor <= 1.0:
                fallos.append(f"{nombre} fuera de [0,1]: {valor}")
        if not self.regla_aplicada.strip():
            # ADR-003 §6.6: sin la regla, la actualización no es auditable —
            # es exactamente el dato que distingue N2 de N3.
            fallos.append("regla_aplicada vacía: la actualización deja de ser auditable")
        return fallos


@dataclass(frozen=True)
class RegistroConceptual:
    """R-C · `ADR-003` §6.2. Máquina de estados que **no decae** — es la
    naturaleza que el encargo de esta sesión señala como la más fácil de
    modelar mal, precisamente porque no tiene un «valor» que se pueda forzar
    al mismo molde que R-A.

    `elemento` no se restringe a una concepción errónea `M01`–`M24`: `ADR-003`
    §6.2 mete en R-C también el *«dominio por nodo»* y el *«estado del
    patrón grados↔radianes»*, que son transiciones de la misma máquina sobre
    otra clave. Restringir el tipo a `M\\d\\d` excluiría dos de los tres
    contenidos que la decisión declara.
    """

    turno: str
    elemento: str
    estado_previo: str
    estado_nuevo: str
    evento_diagnostico: str = ""

    def validar(self) -> list[str]:
        fallos = []
        if self.estado_previo not in ESTADOS_CONCEPTUALES:
            fallos.append(f"estado_previo desconocido «{self.estado_previo}»: {ESTADOS_CONCEPTUALES}")
        if self.estado_nuevo not in ESTADOS_CONCEPTUALES:
            fallos.append(f"estado_nuevo desconocido «{self.estado_nuevo}»: {ESTADOS_CONCEPTUALES}")
        if not self.elemento.strip():
            fallos.append("elemento vacío: no hay sobre qué transiciona el estado")
        return fallos


@dataclass(frozen=True)
class RegistroEstrategico:
    """R-E · `ADR-003` §6.2. Secuencia de eventos con contador sobre ventana
    deslizante — ni valor continuo ni estado discreto, un tercer tipo de
    dato que tampoco cabe en los otros dos moldes.

    `RF-DET-21` define el par que este registro cuenta: retroalimentación
    correctiva seguida de reincidencia en la misma estrategia.
    """

    turno: str
    tipo_evento: str
    ventana: int
    contador: int
    ciclo_negativo: bool = False

    def validar(self) -> list[str]:
        fallos = []
        if not self.tipo_evento.strip():
            fallos.append("tipo_evento vacío")
        if self.ventana <= 0:
            fallos.append(f"ventana inválida: {self.ventana} (debe ser positiva)")
        if self.contador < 0:
            fallos.append(f"contador inválido: {self.contador} (no puede ser negativo)")
        return fallos


@runtime_checkable
class PuertoRegistro(Protocol):
    """Contrato de registro y telemetría. El almacén concreto —formato de
    archivo, un fichero por sesión o por día— es asunto del adaptador.

    Cinco operaciones. Ninguna devuelve nada: es la ruta fría, escribe y no
    decide.
    """

    def registrar_turno(self, entrada: EntradaDeTurno) -> None:
        """`RF-REG-01`. Persiste una entrada del turno tal como ocurrió."""
        ...

    def registrar_turno_completo(self, registro: RegistroDeTurno) -> None:
        """`RF-REG-03` a `RF-REG-07`, `PM-B20`. El turno entero —trazas,
        latencia por componente, estrato de decisión pedagógica, contexto
        recuperado—, para poder reconstruirlo y contrastar qué se calculó
        frente a qué se emitió. `DD-08` decide el almacén: archivo
        estructurado, con una fila en la base que lo referencia."""
        ...

    def registrar_afectivo(self, registro: RegistroAfectivo) -> None:
        """`RF-REG-02` sobre R-A. No agrega con R-C ni con R-E."""
        ...

    def registrar_conceptual(self, registro: RegistroConceptual) -> None:
        """`RF-REG-02` sobre R-C. No agrega con R-A ni con R-E."""
        ...

    def registrar_estrategico(self, registro: RegistroEstrategico) -> None:
        """`RF-REG-02` sobre R-E. No agrega con R-A ni con R-C."""
        ...
