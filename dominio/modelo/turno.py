"""
turno.py — El contexto que recorre la cadena de filtros
=======================================================

`ADR-001` §6.3: *«cada filtro recibe y devuelve el mismo objeto de contexto del
turno, y emite una traza con su latencia y sus metadatos»*. Ese contrato es lo
que hace que la trazabilidad de `RF-ORQ-14` sea una propiedad de la forma de la
cadena y no una funcionalidad que haya que acordarse de añadir.

`ContextoTurno` es inmutable: cada filtro devuelve uno nuevo. Es deliberado —
un objeto que se muta a lo largo de doce filtros no permite reconstruir el
estado intermedio, y `RF-ORQ-14` pide exactamente eso.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from dominio.arbitraje.divulgacion import Señales
from dominio.diagnostico.clasificador import Diagnostico, RespuestaAlItem
from dominio.modelo.contexto_de_uso import ContextoDeUso
from dominio.modelo.estudiante import PerfilEstudiante
from dominio.modelo.matematica import InformeVerificacion, Precomputo
from dominio.modelo.respuesta import RespuestaGenerada
from dominio.pedagogia.conversacion import EstadoDeConversacion
from dominio.pedagogia.intenciones import Intencion
from dominio.pedagogia.politica import DecisionPedagogica
from dominio.pedagogia.sondeo import DesenlaceDelSondeo, EstadoDeSondeo, ItemOfrecido
from dominio.puertos.corpus import Recuperacion
from dominio.puertos.generacion import RespuestaDeGeneracion
from dominio.puertos.plantillas import ItemDosNiveles
from dominio.puertos.registro import BloqueRegistrado, CitaRegistrada


@dataclass(frozen=True)
class TrazaFiltro:
    """Lo que cada filtro deja registrado al pasar.

    `RF-REG-04` exige latencia **desagregada por componente**; `RF-DET-04`
    exige que la latencia del sistema se registre por separado de la del
    estudiante, para poder descontarla al calcular indicadores afectivos.
    """

    filtro: str
    latencia_ms: float
    ruta: str = "caliente"
    metadatos: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ContextoTurno:
    """Estado del turno, tal como viaja por la cadena."""

    texto_estudiante: str
    identificador_sesion: str = ""
    #: `PM-V15` · el identificador de ESTE turno, distinto del de la sesión.
    #: Lo pone el adaptador de entrada, igual que `identificador_sesion`: el
    #: dominio no genera identidad, la recibe.
    #:
    #: **Existe porque sin él el registro del filtro 12 se pisaba a sí mismo.**
    #: `dominio/filtros/registro.py` usaba `identificador_sesion` como clave y
    #: lo dejaba escrito —«dos turnos de la misma sesión comparten la misma
    #: clave de registro»—, así que de una conversación de cinco turnos
    #: sobrevivía **uno**. Se vio ocurrir el 2026-08-14, al correr la primera
    #: conversación de varios turnos del proyecto: `RF-REG-01` pide poder
    #: reconstruir *cualquier* turno, y con una clave por sesión eso era falso.
    #:
    #: Y es **el mismo** identificador que viaja al estudiante en
    #: `CuerpoTurno.turno`, a propósito: si son distintos, un turno que alguien
    #: reporta no se puede encontrar en el registro, que es justo lo que
    #: `RU-12` (la cola de supervisión) necesita poder hacer.
    identificador_turno: str = ""
    #: `DD-27` · 2026-08-18 · el sujeto al que pertenece este turno: el
    #: `identificador_estable` de `PM-B15` cuando la sesión se autenticó con
    #: Google, y el de la sesión cuando no. Lo pone el adaptador de entrada ya
    #: resuelto —`sujeto_de()` es quien decide la preferencia—, igual que
    #: `identificador_sesion`: el dominio no genera identidad, la recibe.
    #:
    #: **Existe porque `RD-22` se ejerce por sujeto y el registro se escribía
    #: por sesión.** `DD-27` lo deja como regla general: *un almacén cuya clave
    #: de escritura difiere de su clave de supresión es un almacén que no se
    #: puede suprimir*. Sin este campo, el filtro 12 —que solo recibe `ctx`— no
    #: puede clavar nada al identificador que sobrevive a cerrar el navegador,
    #: y el borde queda obligado a pasarlo por fuera del contexto, que es lo
    #: que hoy hace `http/turno.py::_registrar_en_frio`.
    #:
    #: Es el mismo movimiento que `identificador_turno` hizo el 2026-08-14, y
    #: se escribe igual a propósito para que las dos se lean igual. Aquel costó
    #: cinco turnos perdidos antes de que alguien viera la consecuencia
    #: —`dominio/filtros/registro.py` lo narra—: la limitación llevaba tiempo
    #: escrita, esperando que alguien la revisara.
    #:
    #: ⚠️ **Puede llegar vacío**, y no solo en sesión anónima:
    #: `rutas/turno.py:326` solo lo resuelve cuando
    #: `aviso_legal.modulo_conductual_habilitado()` es cierto (`RL-09`, edad
    #: declarada). El respaldo a `identificador_sesion` se aplica en el punto
    #: de uso —el filtro 12—, igual que el de `identificador_turno`, para no
    #: tener la misma decisión escrita en dos sitios.
    identificador_sujeto: str = ""
    #: `EQ-016`, hito B3 · bajo qué evento de consentimiento se recoge este
    #: turno. Lo resuelve el borde —es quien conoce la sesión y el estado
    #: vigente— y el filtro 12 lo copia a cada voz que persiste.
    #:
    #: `None` es «no consta»: un despliegue sin la migración 12, o una fila
    #: anterior a B3. No se inventa un vínculo, y el dominio no lo deduce.
    consentimiento_evento: int | None = None
    #: `RF-REG-01`, 2026-08-18 · cuándo ocurrió este turno, **sellado por el
    #: servidor** al entrar la petición. ISO-8601 con zona.
    #:
    #: ⚠️ **Nunca sale del cuerpo de la petición.** `TurnoEntrante.momento`
    #: existe y lo trae el cliente; atar esta marca ahí pondría en manos de
    #: quien llama tres cosas que no le corresponden: el reloj de retención
    #: —`C-01` cuenta 24 meses desde aquí—, el orden del historial —el índice
    #: es `momento DESC`— y la propia marca de `RF-REG-01`, que pasaría a ser
    #: un valor que el sistema no avala.
    #:
    #: Se comprobó al decidirlo: `TurnoEntrante.momento` **no lo lee nadie** en
    #: `adaptadores/` ni en `dominio/`. Era dato muerto, así que sellarlo del
    #: lado del servidor no rompió ningún consumidor.
    #:
    #: Lo pone el adaptador de entrada, igual que `identificador_turno` y
    #: `identificador_sujeto`: el dominio no genera identidad ni mide tiempo,
    #: los recibe.
    momento: str = ""
    #: `T-04` del acta del 2026-08-18 · la explicación de degradación de este
    #: turno, cuando lo hubo. Vacía en un turno normal.
    #:
    #: **Existe porque el filtro 12 no podía verla.** Se construía en
    #: `http/turno.py`, en el `except`, **después** de llamar a
    #: `_registrar_en_frio(...)`, así que la ruta fría corría sin saber que el
    #: turno se había degradado. `T-04` pide que los degradados entren al
    #: historial *marcados* —un hilo con huecos es peor que uno que dice qué
    #: pasó—, y para marcarlos hay que verlos.
    #:
    #: Misma forma que `identificador_sujeto` adoptó en `A3`, y por el mismo
    #: motivo: si el dominio tiene que decidir dónde va algo, tiene que poder
    #: verlo; pasarlo por fuera obliga al borde a hacer de intermediario.
    degradacion: str = ""
    #: `PM-B25`, 2026-08-18 · lo que el estudiante VIO, ya traducido a tipos de
    #: `dominio/puertos/registro.py` por quien compone el borde.
    #:
    #: **No lo calcula el dominio.** Separar la narración en bloques y decidir
    #: el sello es `_cuerpo()` en `http/turno.py`, y recalcularlo aquí daría
    #: dos implementaciones de la misma cuenta —el fallo que
    #: `COMO-TRABAJAMOS.md` §4.bis describe—. El borde lo traduce y lo deja
    #: aquí antes de la ruta fría, igual que hace con `degradacion`.
    #:
    #: **Existe porque el historial guardaba solo la narración**, con sus
    #: marcas `{{c1}}` sin resolver y sin decir qué se había verificado. Es la
    #: reaparición de `PM-B25` en otra superficie: aquel se vio en pantalla el
    #: 2026-08-11, éste se habría visto en el sidebar de `PM-F20`.
    bloques_emitidos: tuple[BloqueRegistrado, ...] = ()
    citas_emitidas: tuple[CitaRegistrada, ...] = ()
    #: Fase 8 · conceptos del banco que el cuerpo expuso en este turno. Los
    #: decide el mismo borde que construye ``CuerpoTurno.conceptos`` y se
    #: conservan por identificador, sin copiar nombres ni contenido.
    conceptos_emitidos: tuple[str, ...] = ()
    #: Nivel de divulgación como cadena y de dónde salió el material. Los pone
    #: el borde junto con los bloques, y de la misma traducción.
    nivel_emitido: str = ""
    procedencia_origen: str = ""
    procedencia_referencia: str = ""
    #: `PM-B21` · qué clase de `DD-12` es dueña de este turno, si se puede
    #: resolver sin ambigüedad. Viene de fuera de la cadena —igual que
    #: `señales`—: el turno no puede deducirlo de su propio texto, y una
    #: sesión matriculada en más de una clase a la vez no tiene una única
    #: respuesta correcta, así que el adaptador de entrada deja vacío en vez
    #: de adivinar. **Nunca cruza a `RespuestaTurno`**:
    #: `08-Contrato-del-Turno.md` §12 ya declara que la clase no viaja en el
    #: turno — este campo es para uso interno del servidor (`RU-12`, la cola
    #: de supervisión), no para el cliente.
    clase: str = ""
    #: `EQ-031` · para qué se usó el tutor en este turno.
    #:
    #: Viene de fuera de la cadena, igual que `clase` y `señales`: el turno no
    #: puede deducir de su propio texto quién lo escribe, y el cliente no puede
    #: mandarlo o se reclasificaría a sí mismo. Lo deriva el borde del **rol
    #: real de la sesión** (`adaptadores/entrantes/http/rutas/turno.py`).
    #:
    #: Lo consume el filtro 12 para persistirlo con el turno. **Nunca cruza a
    #: `RespuestaTurno`**: es contexto de servidor, y el estudiante no tiene por
    #: qué recibir una clasificación que no es suya, igual que con `clase`.
    #:
    #: El valor por defecto es el del estudiante porque es el único uso que
    #: existía antes de `EQ-031`; ver `dominio/modelo/contexto_de_uso.py` sobre
    #: por qué la derivación del borde falla hacia el lado contrario.
    contexto_de_uso: str = ContextoDeUso.APRENDIZAJE_ESTUDIANTE
    #: Las expresiones matemáticas que el filtro 1 segmentó del canal de texto,
    #: ya en su forma canónica cuando la cascada determinista de `ADR-007` N2
    #: pudo resolverlas. El canal de texto (`texto_estudiante`) no se toca: N4
    #: exige que la normalización **añada**, no sustituya.
    expresiones: tuple[str, ...] = ()
    #: `PM-B31` · la última expresión que el estudiante escribió en ESTA sesión,
    #: aportada por el borde igual que `señales`. El filtro 1 la hereda **solo
    #: si este turno no trae ninguna**, para que el respaldo determinista de
    #: `D-21` pueda entrar en un turno como «sigo sin verlo, qué hago con lo de
    #: adentro» — que es el caso típico, no el raro.
    expresion_previa: str = ""
    #: Problema declarado en esta conversación, distinto de la última fórmula
    #: (que puede ser ya una propuesta del estudiante).
    ejercicio_activo: dict[str, str] | None = None
    #: Paquete E · si `expresiones` **no** se escribió en este mensaje sino que
    #: el filtro 1 la heredó de la sesión. Lo necesita el modelo del problema:
    #: una expresión heredada es del turno anterior por definición, así que no
    #: puede ser evidencia de que el estudiante cambió de ejercicio. Sin este
    #: campo, el problema activo pasaba a ser la respuesta del propio
    #: estudiante y los contadores se reiniciaban solos.
    expresiones_heredadas: bool = False
    precomputo: Precomputo | None = None
    #: Qué pide el estudiante, según el filtro 2: **una de las diez clases del
    #: catálogo v1** (`dominio/pedagogia/intenciones.py`). Cadena vacía
    #: significa que el filtro no ha corrido todavía, que no es lo mismo que
    #: `ambigua` — `ADR-007` I4 exige que la clase indecisa se declare como tal
    #: y no como hueco silencioso.
    #:
    #: Las cuatro familias de `ADR-007` §6.3 —`conceptual`, `procedimental`,
    #: `emocional`, `ambigua`— **no viven en un segundo campo**: se derivan con
    #: `familia_de(ctx.intencion)`. Dos clasificaciones del mismo turno pueden
    #: desincronizarse, y entonces la que gobierna la compuerta del filtro 4 no
    #: sería la que gobierna la estrategia.
    intencion: str = ""
    #: De dónde salió `intencion`: `regla` cuando la cascada determinista
    #: decidió, `sin_resolver` cuando ninguna regla casó. `ADR-007` I4 prohíbe
    #: que una clasificación indecisa se disfrace de sustantiva.
    intencion_origen: str = ""
    #: La decisión de intención **entera**: candidatas, descartadas, motivo y
    #: las señales ortogonales del turno —cortesía, confirmación de ayuda,
    #: preferencia de no adaptación, carga emocional expresada—. `RF-REG-06`
    #: pide reconstruir la decisión, no sólo su resultado, y las señales las
    #: consumen el selector y el modelo de problema sin volver a leer el texto.
    #:
    #: `None` mientras el filtro 2 no haya corrido.
    intencion_detalle: Intencion | None = None
    #: `PM-B24` · el filtro 2 detectó una petición de **límite**, no de
    #: derivada — `RF-IUC-03`. `False` por defecto: mientras no se detecte con
    #: una regla léxica, el filtro 6.5 sigue el camino de siempre (derivada).
    #: No hay quinta clase de intención por esto: sigue siendo `procedimental`,
    #: esto es una señal aparte de **qué tipo** de cálculo procedimental es.
    es_limite: bool = False
    #: La expresión del límite, extraída del texto — no necesariamente la
    #: misma que `expresiones[0]`: la sintaxis de un límite («de 1/x») no es
    #: la que el filtro 1 segmenta para derivadas, así que viaja aparte.
    limite_expresion: str = ""
    #: Variable escrita en el ejercicio (x, t, θ, etc.). La función enviada
    #: al navegador se normaliza a x sólo después de calcular con esta.
    limite_variable: str = "x"
    #: A qué tiende la variable: `"oo"`, `"-oo"`, o un número, en la misma
    #: forma que `adaptadores/salientes/simbolico/limites.py` ya analiza.
    limite_destino: str = ""
    #: Nodo del grafo que el filtro 4 fijó para este turno, si lo fijó. Vacío
    #: significa que la recuperación identifica el suyo, que es la rama de
    #: respaldo de `ADR-002` y el 14,5 % que `R-17` mide.
    nodo_activo: str = ""
    #: La compuerta de contexto del filtro 4 (`ADR-001` §6.3, filtro 4). `True`
    #: por defecto: mientras el filtro 4 no haya corrido, la rama segura es
    #: recuperar, igual que `ADR-007` I3 hace con la intención `ambigua`.
    procede_recuperar: bool = True
    #: Lo que el filtro 5 recuperó. `None` mientras no haya pasado por él, que
    #: no es lo mismo que haber recuperado nada: eso es `sin_fuente`.
    recuperacion: Recuperacion | None = None
    #: El prompt que el filtro 7 construyó a partir del contexto. Viaja hasta el
    #: filtro 8, que es el único que lo envía al puerto de generación: el puerto
    #: «no decide qué se pide», así que el texto tiene que llegarle ya hecho.
    prompt: str = ""
    #: Lo que el filtro 8 generó, **sin verificar todavía**. `None` mientras no
    #: haya pasado por él. No es la respuesta del sistema y por eso es un campo
    #: aparte de `respuesta`: `ADR-008` pone la verificación dos filtros más
    #: adelante, y confundir la generación con la respuesta es justo lo que la
    #: separación evita.
    generacion: RespuestaDeGeneracion | None = None
    respuesta: str = ""
    #: La estructura que el filtro 9 verificó —narración más afirmaciones—,
    #: podada si descendió. `respuesta` (arriba) es la narración ya aplanada a
    #: texto y basta para la cadena interna; el borde de entrada (`PM-B14`)
    #: necesita la estructura para separar prosa de notación por bloque, que
    #: es lo que `08-Contrato-del-Turno.md` §5 exige. `None` mientras no haya
    #: pasado por el filtro 9, o si no había nada que verificar.
    respuesta_generada: RespuestaGenerada | None = None
    informe: InformeVerificacion | None = None
    nivel_divulgacion: int = 1
    #: `DEC-R3` · sobre QUÉ se puede revelar lo que el nivel autoriza. El nivel
    #: dice cuánto; el alcance dice de qué. `ejercicio_activo` cuando lo abrió
    #: el trabajo del estudiante; `analogo` cuando lo abrió una petición de
    #: teoría o de ejemplo, que no autoriza resolver el ejercicio de delante.
    alcance_divulgacion: str = "ejercicio_activo"
    #: Lo que el filtro 6 mira para decidir cuánto se revela · `PM-B05`.
    #:
    #: Viene **de fuera de la cadena**: cuántos intentos lleva el estudiante en
    #: este paso y si pidió ver la solución no son cosas de este turno sino de
    #: la sesión, y el turno no las puede deducir de su propio texto. Las pone
    #: el adaptador de entrada, que es quien conoce la sesión.
    #:
    #: `None` significa que nadie las aportó, y entonces el filtro 6 opera con
    #: el piso conservador —sondeo— y lo deja dicho. No es lo mismo que unas
    #: señales vacías, que sí serían una afirmación sobre el estudiante.
    señales: Señales | None = None
    #: `PM-B13` · la otra mitad del filtro 6: **qué** intervención de `T6` se
    #: eligió, no cuánto se revela. `5` (autorregulación) es el piso seguro,
    #: por la misma razón que `nivel_divulgacion` empieza en `1`: es el nivel
    #: que no presupone ningún estado del estudiante que nadie midió todavía.
    nivel_intervencion: int = 5
    #: `PM-B10` · el perfil tal como llegaba ANTES de este turno. Viene de
    #: fuera de la cadena, igual que `señales` — lo trae el adaptador de
    #: entrada, que es quien conoce la persistencia (`PM-B11`). `None`
    #: significa «sin historial todavía», no «historial vacío»: el filtro 3
    #: parte de `EstadoAfectivo()` en blanco en ese caso, sin que eso
    #: signifique que el estudiante mide 0 en todo.
    perfil_previo: PerfilEstudiante | None = None
    #: `PM-B10` · lo que el filtro 3 produjo al aplicar la observación de
    #: este turno sobre `perfil_previo`. `None` mientras no haya pasado por
    #: él. Quien compone el sistema decide cuándo persistirlo —esto es ruta
    #: caliente y no hace ningún `I/O`; persistir es asunto de quien reciba
    #: este campo después del turno, `PM-B11`.
    perfil_actualizado: PerfilEstudiante | None = None
    #: `PM-B08` · lo que el estudiante contestó a un ítem de dos niveles, en
    #: crudo. Viene **de fuera de la cadena**, igual que `señales` y
    #: `perfil_previo`: el ítem se le planteó en un turno anterior y el turno
    #: no puede deducir de su propio texto a qué está respondiendo.
    #:
    #: `None` en un turno de texto libre, que es **todos los de hoy**: el
    #: sistema no plantea ítems todavía —eso es el flujo conversacional de dos
    #: turnos de `RF-DGC-01`, que es decisión de producto y no existe—. Ese
    #: `None` no es un hueco silencioso: `dominio/filtros/diagnostico.py` lo
    #: declara en su traza en cada turno.
    respuesta_al_item: RespuestaAlItem | None = None
    #: Fase 4 · `RC-PED-06` · los ítems que ESTA sesión llegó a plantear, con
    #: sus razones. Lo aporta el borde desde la sesión, igual que `señales`: el
    #: turno no puede saber de su propio texto qué se le ofreció antes.
    #:
    #: Sin esto, el servidor clasificaba cualquier `(nodo, resultado, razón)`
    #: que llegara y un cliente podía provocar un diagnóstico sobre un nodo que
    #: el estudiante nunca vio.
    sondeos_ofrecidos: tuple[ItemOfrecido, ...] = ()
    #: Paquete H · los ítems que esta sesión ya contestó. Un ítem contestado
    #: está cerrado: volver a contestarlo produciría un segundo diagnóstico
    #: sobre las mismas cuatro razones, ya sabidas.
    sondeos_contestados: tuple[str, ...] = ()
    #: Fase 4 · lo que la sesión recuerda del tope de frecuencia de los ítems.
    #: Lo aporta el borde, igual que `señales`: cuántos turnos van desde el
    #: último ítem no es algo que este turno pueda deducir de su propio texto.
    estado_de_sondeo: EstadoDeSondeo | None = None
    #: `R2-B` · qué hizo el servidor con `respuesta_al_item`: la **fuente única**
    #: de «esta respuesta cerró el ítem». Lo pone el filtro 6.75, que es el que
    #: valida y clasifica, y lo leen los dos sitios que mutan estado fuera de la
    #: cadena —`cerrar_estado()` y el borde HTTP—.
    #:
    #: 🔴 Ninguno de los dos puede volver a mirar `respuesta_al_item` para
    #: decidir: ese campo es **lo que el cliente mandó**, y que llegara no dice
    #: que el servidor lo admitiera. Ver `DesenlaceDelSondeo`.
    desenlace_del_sondeo: DesenlaceDelSondeo = field(default_factory=DesenlaceDelSondeo)
    #: Fase 4 · el ítem que **este** turno plantea, si el filtro 6.8 decidió que
    #: procede. `None` en la mayoría de los turnos.
    #:
    #: La decisión se movió del adaptador a la cadena porque
    #: `diagnostico_two_tier` pasó a ser una estrategia: si el turno va a
    #: plantear un ítem, la respuesta del tutor no debe además preguntar, y eso
    #: lo tiene que saber el prompt. Con la decisión después de la cadena, la
    #: regla de la política que lo produce era inalcanzable.
    item_ofrecido: ItemDosNiveles | None = None
    #: `PM-B32` · `D-21` · la notación en la que el estudiante quiere leer lo
    #: que el sistema le escribe: `lagrange` (`f'(x)`), `leibniz` (`dy/dx`) u
    #: `operador` (`d/dx`). **Cadena vacía cuando no eligió**, y entonces
    #: decide el adaptador simbólico, que es quien sabe cuáles tiene escritas.
    #:
    #: Es lo contrario de `RF-IUC-02`, y conviene no confundirlas: aquella
    #: normaliza a forma canónica lo que el estudiante ESCRIBE; esto elige
    #: cómo se le escribe a él. Por eso vive en el contexto y no toca el
    #: filtro 1: no cambia nada de lo que se interpreta.
    notacion: str = ""
    #: Turnos previos recientes de la sesión para mantener el hilo de la conversación.
    historial_reciente: tuple[dict, ...] = ()
    # Optativo y explícito: el laboratorio conserva hechos con su turno de origen.
    contexto_conversacional: dict | None = None
    #: `PM-B08` · el estado `E1`–`E4` que salió de clasificar lo anterior.
    #: `None` mientras el filtro no haya corrido **y también** cuando corrió y
    #: no había nada que clasificar: son el mismo caso para quien lo consume
    #: —`dominio/pedagogia/andamiaje.py` cae a lo que hace sin diagnóstico— y
    #: distinguirlos aquí obligaría a un tercer valor que nadie miraría.
    #:
    #: ⚠️ **Nunca cruza a `RespuestaTurno`.** `RP-20` obliga a comunicar las
    #: inferencias como probabilísticas y no diagnósticas, y `08-Contrato-del-
    #: Turno.md` §9 ya deja fuera del turno la confianza del diagnóstico. Este
    #: campo orienta la pregunta que se hace; no se le enseña al estudiante.
    diagnostico: Diagnostico | None = None
    #: Fase 4 · lo que el filtro 6.6 concluyó sobre la propuesta del estudiante:
    #: `valida`, `invalida` o `no_verificable`. Cadena vacía significa que no se
    #: intentó comprobar —el turno no proponía nada—, que **no es lo mismo** que
    #: `no_verificable`: aquello es «se intentó y no se pudo», y la política los
    #: trata distinto.
    veredicto_del_intento: str = ""
    #: Resultado final comprobado contra el ejercicio activo. Sólo el CAS
    #: puede rellenarlo; abre la retroalimentación de cierre de este turno.
    resultado_verificado: str = ""
    #: Transformación algebraica comprobada que aún no concluye el ejercicio.
    transformacion_verificada: str = ""
    #: Referencia explícita del último paso preguntado, separada del ejercicio completo.
    paso_pendiente: dict | None = None
    paso_verificado: str = ""
    #: Fase 4 · el estudiante pidió que el estilo NO se adapte a sus
    #: expresiones. Viene de fuera de la cadena, igual que `señales`: es una
    #: preferencia de la conversación y el borde la conserva.
    sin_adaptacion: bool = False
    #: Fase 4 · **el estado que toma las decisiones de este turno**, y es el de
    #: la conversación activa, no el perfil longitudinal (política F.6). Trae
    #: el afectivo temporal, el problema abierto con sus contadores y episodios,
    #: y las preferencias. Lo mantiene el borde en la sesión.
    #:
    #: `None` significa que nadie lo aportó, y entonces la cadena opera con uno
    #: en blanco — que es exactamente cómo empieza una conversación nueva, y por
    #: eso el piso y el arranque coinciden.
    estado_conversacion: EstadoDeConversacion | None = None
    #: Fase 4 · la estrategia del turno anterior de esta conversación. La aporta
    #: el borde, y sirve para saber si hay cambio que anunciar al estudiante con
    #: la frase neutral de la política G.
    estrategia_previa: str = ""
    #: Fase 4 · la decisión del filtro 6.9, entera: estrategia, motivo,
    #: candidatas, descartadas, incertidumbre, fallback, procedencia del
    #: diagnóstico, intervención y modificadores. `RF-REG-06` pide reconstruir
    #: la decisión sin consultar logs, y esto es lo que lo permite.
    decision_pedagogica: DecisionPedagogica | None = None
    #: Base de retroalimentación comprobada, activada sólo por composición optativa.
    retroalimentacion_del_intento: RespuestaGenerada | None = None
    necesidad_pedagogica: str = ""
    trazas: tuple[TrazaFiltro, ...] = ()
    # Campos optativos al final: conservar el constructor posicional existente.
    continuidad: dict | None = None
    actos_conversacionales: tuple[dict, ...] = ()
    siguiente_objetivo: dict | None = None
    mensajes_generacion: tuple[dict, ...] = ()

    def con_traza(self, traza: TrazaFiltro, **cambios) -> ContextoTurno:
        """Devuelve un contexto nuevo con la traza añadida.

        Es el único camino por el que un filtro devuelve resultado, de modo que
        **no se puede modificar el contexto sin dejar traza**.
        """
        return replace(self, trazas=self.trazas + (traza,), **cambios)

    @property
    def hay_item_ofrecible(self) -> bool:
        """Si este turno plantea un ítem. Derivado, no un segundo campo."""
        return self.item_ofrecido is not None

    @property
    def latencia_total_ms(self) -> float:
        return sum(t.latencia_ms for t in self.trazas)

    @property
    def latencia_por_ruta(self) -> dict:
        out: dict = {}
        for t in self.trazas:
            out[t.ruta] = out.get(t.ruta, 0.0) + t.latencia_ms
        return out
