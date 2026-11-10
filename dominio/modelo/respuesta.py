"""
respuesta.py — El contrato entre el generador y el verificador
==============================================================

Implementa `ADR-014`: **el generador devuelve una narración y una lista de
afirmaciones, y la narración cita los identificadores de las afirmaciones en los
puntos donde las emplea.**

Por qué el contrato tiene esta forma
------------------------------------
`ADR-008` §1.1 estableció que los seis defectos del verificador de la iteración 0
eran síntoma de una decisión anterior: **la prosa como interfaz**. Ningún banco de
patrones cubre todas las formas de enunciar un resultado, y cada forma no
prevista se vuelve una aprobación silenciosa.

Con estructura, la extracción deja de ser reconocimiento y pasa a ser lectura. Y
lo que hace valiosa la referencia —frente a una lista suelta— es que la interfaz
puede marcar el estado de verificación **por bloque**, que es lo que `RF-IUC-04`
exige y una lista suelta no permite.

Las cuatro reglas de `ADR-014` §5.2
------------------------------------
- **C1** Matemática fuera de referencia invalida la respuesta entera.
- **C2** Una referencia a una afirmación inexistente invalida la respuesta.
- **C3** Un objeto malformado no se reintenta en silencio: se registra y se
  desciende al nivel 1.
- **C4** El nivel 1 no lleva afirmaciones — una pregunta socrática no contiene
  nada que verificar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from dominio.modelo.deteccion_matematica import hallar_matematica
from dominio.modelo.matematica import BloqueVerificable

#: Sintaxis de la referencia dentro de la narración: {{a1}}
_REFERENCIA = re.compile(r"\{\{\s*([A-Za-z0-9_-]+)\s*\}\}")

class RespuestaMalformada(ValueError):
    """El objeto devuelto por el generador no cumple el contrato (`ADR-014` C3)."""


@dataclass(frozen=True)
class Afirmacion:
    """Una afirmación matemática declarada por el generador.

    `regla_declarada` no es decoración: permite comprobar la correspondencia
    entre **lo que el modelo dice que aplica** y **lo que la transformación
    hace**. `ADR-013` señaló que la verificación de resultado no comprueba esa
    correspondencia, y es la clase de error que un estudiante con la concepción
    **M21** replicaría.
    """

    identificador: str
    izquierda: str
    relacion: str
    derecha: str
    regla_declarada: str = ""

    def como_bloque(self) -> BloqueVerificable:
        return BloqueVerificable(
            identificador=self.identificador,
            izquierda=self.izquierda,
            derecha=self.derecha,
            relacion=self.relacion,
            regla_declarada=self.regla_declarada or None,
        )


@dataclass(frozen=True)
class ExpresionCitada:
    """Matemática que se **menciona** sin afirmarse. `ADR-014` §5.4.

    *«Mira el numerador √(x+h) − √x»* no es prosa —hay que renderizarla— pero
    tampoco es una afirmación: **una expresión suelta no puede ser verdadera ni
    falsa**, así que no hay nada que el motor simbólico pueda verificar.

    Por qué existe, y por qué costó descubrirlo · *implementada el 2026-08-10*
    -------------------------------------------------------------------------
    `ADR-014` §5.4 la declaró el 2026-08-04 y **el contrato de datos se quedó
    sin ella**: solo había `narracion` y `afirmaciones`. La consecuencia se vio
    al medir con un proveedor real, en `PM-B05`: pedirle al modelo que explique
    la regla de la cadena **sin escribir `sen(x^2)` en ninguna parte** es pedirle
    que explique sin nombrar, y falla. Su narración mencionaba la expresión,
    `C1` invalidaba la respuesta entera, y el turno descendía a sondeo — de modo
    que **el nivel 2 era inalcanzable en la práctica** y el motor simbólico
    nunca llegaba a trabajar.

    La propia §5.4 lo había anticipado: *«dar al modelo un sitio legítimo donde
    poner matemática que solo menciona reduce las violaciones de C1»*.

    **Y `C1` no se relaja.** Una expresión citada sigue estando dentro de una
    marca; lo que se añade es **una marca más, no un permiso**. Lo que quede
    fuera de toda marca sigue invalidando la respuesta.
    """

    identificador: str
    expresion: str


@dataclass(frozen=True)
class RespuestaGenerada:
    """Lo que el filtro 8 entrega al filtro 9."""

    narracion: str
    afirmaciones: tuple[Afirmacion, ...] = ()
    nivel_divulgacion: int = 1
    #: `ADR-014` §5.4. Se renderizan y **no** se verifican.
    citadas: tuple[ExpresionCitada, ...] = ()

    # ── Lectura de la estructura ─────────────────────────────────────────────

    @property
    def referencias(self) -> tuple[str, ...]:
        """Identificadores citados por la narración, en orden de aparición."""
        return tuple(_REFERENCIA.findall(self.narracion))

    @property
    def identificadores(self) -> set[str]:
        """Todo lo que la narración puede citar: afirmaciones **y** citadas.

        Las dos cuentan porque `C2` pregunta si la referencia existe, no si es
        verificable. Dejar fuera a las citadas haría que toda expresión
        mencionada disparara «cita afirmaciones que no existen».
        """
        return {a.identificador for a in self.afirmaciones} | {
            c.identificador for c in self.citadas
        }

    def bloques(self) -> tuple[BloqueVerificable, ...]:
        return tuple(a.como_bloque() for a in self.afirmaciones)

    # ── Las cuatro reglas ────────────────────────────────────────────────────

    def problemas(self) -> list[str]:
        """Incumplimientos del contrato. Lista vacía significa que es admisible."""
        fallos: list[str] = []

        if not self.narracion.strip():
            fallos.append("la narración está vacía")

        if not 1 <= self.nivel_divulgacion <= 3:
            fallos.append(
                f"nivel de divulgación fuera de la escala: {self.nivel_divulgacion}"
            )

        # C4 · el nivel 1 no lleva afirmaciones
        if self.nivel_divulgacion == 1 and self.afirmaciones:
            fallos.append(
                "el nivel 1 es de sondeo y no puede llevar afirmaciones matemáticas"
            )

        # C2 · referencia a afirmación inexistente
        huerfanas = sorted(set(self.referencias) - self.identificadores)
        if huerfanas:
            fallos.append(
                "la narración cita afirmaciones que no existen: " + ", ".join(huerfanas)
            )

        # Declarada que nadie cita: no invalida, pero no se emite nada que la
        # respalde, así que se trata igual que matemática suelta.
        sueltas = sorted(self.identificadores - set(self.referencias))
        if sueltas:
            fallos.append(
                "hay afirmaciones declaradas que la narración no cita: "
                + ", ".join(sueltas)
            )

        # Identificadores repetidos: romperían el marcado por bloque. Se miran
        # afirmaciones y citadas **juntas**, porque comparten espacio de
        # nombres: dos marcas con el mismo identificador harían imposible saber
        # cuál de las dos se está renderizando.
        vistos, repetidos = set(), set()
        for a in (*self.afirmaciones, *self.citadas):
            (repetidos if a.identificador in vistos else vistos).add(a.identificador)
        if repetidos:
            fallos.append(
                "identificadores de afirmación repetidos: " + ", ".join(sorted(repetidos))
            )

        # C1 · matemática fuera de referencia
        for marcador in self.matematica_suelta():
            fallos.append(f"hay matemática fuera de referencia: {marcador}")

        return fallos

    def matematica_suelta(self) -> list[str]:
        """Indicios de matemática hallados fuera de una referencia (`C1`).

        Se retira el texto de las referencias y se busca en lo que queda. **La
        estrategia de detección vive en `deteccion_matematica.py` y es el punto
        revisable del contrato** — riesgo `R-23`, alternativas en `ADR-014`
        §8.1. Cambiarla no toca ninguna de las cuatro reglas.
        """
        return hallar_matematica(_REFERENCIA.sub(" ", self.narracion))

    @property
    def admisible(self) -> bool:
        return not self.problemas()

    # ── C4 · descenso al nivel 1 ─────────────────────────────────────────────

    def podada(self) -> RespuestaGenerada:
        """Devuelve la respuesta reducida al nivel 1: sin afirmaciones.

        `ADR-008` §6.1 lo llamó *la parte elegante*: **el modo seguro no hubo
        que inventarlo**. Cuando la verificación falla, la respuesta desciende a
        preguntar en lugar de afirmar, y una pregunta socrática no contiene
        afirmaciones que verificar.

        Descender es **podar**, no regenerar: se retiran las oraciones que citan
        afirmaciones y se conserva el resto de la narración.
        """
        # Se retiran las frases que citan AFIRMACIONES. Las que solo citan una
        # expresión mencionada se conservan: una expresión citada no afirma
        # nada, así que no hay nada que retirar por prudencia —y quitarla
        # dejaría la pregunta socrática sin poder nombrar aquello sobre lo que
        # pregunta, que es justo lo que `ADR-014` §5.4 vino a arreglar.
        # Las referencias sin definición tampoco pueden sobrevivir al descenso:
        # el lector las omitiría y el historial rechazaría el turno completo.
        de_afirmacion = {a.identificador for a in self.afirmaciones} | (
            set(self.referencias) - self.identificadores
        )
        conservadas = [
            frase
            for frase in _dividir_en_frases(self.narracion)
            if not (set(_REFERENCIA.findall(frase)) & de_afirmacion)
        ]
        texto = " ".join(f.strip() for f in conservadas).strip()
        citadas = tuple(
            c for c in self.citadas if "{{" + c.identificador + "}}" in texto
            or c.identificador in _REFERENCIA.findall(texto)
        )
        return RespuestaGenerada(
            narracion=texto,
            afirmaciones=(),
            nivel_divulgacion=1,
            citadas=citadas,
        )

    # ── Construcción desde el motor · el respaldo de `D-21` ──────────────────

    @classmethod
    def desde_transformacion_verificada(cls, ctx) -> RespuestaGenerada | None:
        """Reconoce una simplificación válida sin confundirla con el límite."""
        activo = ctx.ejercicio_activo or {}
        if activo.get("tipo") != "limite" or not ctx.transformacion_verificada:
            return None
        expresion = activo.get("expresion", "")
        if not expresion:
            return None
        return cls(
            narracion=(
                "Sí, simplificaste correctamente: {{a1}}. La igualdad vale donde "
                "la expresión original está definida. Ahora evalúa a qué valor "
                "se acerca la expresión simplificada en el límite."
            ),
            afirmaciones=(Afirmacion(
                identificador="a1", izquierda=expresion, relacion="=",
                derecha=ctx.transformacion_verificada,
                regla_declarada="simplificación algebraica",
            ),),
            nivel_divulgacion=2,
        )

    @classmethod
    def desde_acierto_verificado(cls, ctx) -> RespuestaGenerada | None:
        """Retroalimentación de cierre cuando el CAS comprobó la respuesta.

        El generador puede ofrecer un desarrollo más rico, pero este respaldo
        evita volver a preguntar si su estructura no supera la verificación.
        Cada igualdad se declara y vuelve a pasar por el filtro simbólico.
        """
        activo = ctx.ejercicio_activo or {}
        pre = ctx.precomputo
        if not ctx.resultado_verificado or pre is None or not pre.ok or not pre.resultado_corriente:
            return None
        expresion = activo.get("expresion", "")
        variable = activo.get("variable", "x")
        if not expresion or activo.get("tipo") not in ("limite", "derivada", "valor", "valor_derivada"):
            return None

        if activo["tipo"] == "limite":
            destino = activo.get("destino", "")
            pregunta_por_valor = bool(
                destino and re.search(
                    rf"(?:\bf\s*\(\s*{re.escape(destino)}\s*\)|"
                    rf"\b(?:la\s+)?funci[oó]n\s+en\s+{re.escape(destino)}\s+(?:vale|es\b))",
                    ctx.texto_estudiante, re.I,
                )
            )
            return cls._cierre_limite(pre, expresion, variable, destino, pregunta_por_valor)
        if activo["tipo"] in ("valor", "valor_derivada"):
            return cls(
                narracion=(
                    "Sí, tu resultado es correcto. Se respetan primero los paréntesis, "
                    "se evalúan las funciones y potencias, y luego las operaciones restantes. "
                    "Al evaluar la expresión se obtiene {{a1}}."
                ),
                afirmaciones=(Afirmacion(
                    identificador="a1", izquierda=pre.expresion_fuente if activo["tipo"] == "valor_derivada" else expresion, relacion="=",
                    derecha=pre.resultado_corriente, regla_declarada="evaluación exacta",
                ),),
                nivel_divulgacion=3,
            )
        return cls._cierre_derivada(pre, expresion, variable, activo.get("orden", 1))

    @classmethod
    def _orientacion_de_tecnicas(cls, pre) -> list[str]:
        frases = []
        tecnicas = [paso.regla for paso in pre.pasos if paso.tipo == "tecnica"]
        if any(paso.tipo == "indeterminacion" for paso in pre.pasos):
            frases.append("La sustitución directa revela una forma indeterminada.")
        if len(tecnicas) == 1:
            frases.append(f"La técnica que permite avanzar es «{tecnicas[0]}».")
        elif tecnicas and len(set(tecnicas)) == 1:
            frases.append(
                f"La técnica «{tecnicas[0]}» se usa {len(tecnicas)} veces, "
                "hasta obtener una expresión evaluable."
            )
        elif tecnicas:
            frases.append("Las técnicas, en orden, son: " + ", después ".join(
                f"«{tecnica}»" for tecnica in dict.fromkeys(tecnicas)
            ) + ".")
        return frases

    @classmethod
    def _cierre_limite(
        cls, pre, expresion: str, variable: str, destino: str,
        pregunta_por_valor: bool = False,
    ) -> RespuestaGenerada | None:
        if not destino:
            return None
        if pre.sin_limite_bilateral:
            return cls._cierre_limite_sin_valor(pre, expresion, variable, destino)
        afirmaciones: list[Afirmacion] = []
        frases = [
            (
                "El valor que propones para el límite es correcto; comprobé ese límite."
                if pregunta_por_valor else
                "Sí, tu resultado es correcto y lo comprobé con el ejercicio que estás resolviendo."
            ),
            *cls._orientacion_de_tecnicas(pre),
        ]
        if pregunta_por_valor and any(paso.tipo == "indeterminacion" for paso in pre.pasos):
            frases.append(
                "Pero ese valor corresponde al límite, no al valor de la función "
                "original en el punto. Allí el denominador se anula, así que "
                "la expresión original no está definida."
            )
        if pre.simplificacion_corriente:
            afirmaciones.append(Afirmacion(
                identificador="a1", izquierda=expresion, relacion="=",
                derecha=pre.simplificacion_corriente,
                regla_declarada="simplificación algebraica",
            ))
            frases.append(
                "Primero se simplifica la expresión: {{a1}}. Esta igualdad "
                "se usa donde la expresión original está definida."
            )
        else:
            frases.append("Primero se examina qué ocurre al acercarse al valor indicado.")
        for transformada in pre.limites_intermedios:
            identificador = f"a{len(afirmaciones) + 1}"
            afirmaciones.append(Afirmacion(
                identificador=identificador,
                izquierda=f"lim {variable}->{destino} ({transformada})",
                relacion="=", derecha=pre.resultado_corriente,
                regla_declarada="regla de L'Hôpital",
            ))
            frases.append(
                f"Al derivar numerador y denominador, la nueva expresión del límite da {{{{{identificador}}}}}."
            )
        identificador = f"a{len(afirmaciones) + 1}"
        afirmaciones.append(Afirmacion(
            identificador=identificador,
            izquierda=f"lim {variable}->{destino} ({expresion})",
            relacion="=", derecha=pre.resultado_corriente,
            regla_declarada="evaluación del límite",
        ))
        frases.append(
            f"Después se evalúa el comportamiento al acercarse al destino indicado: {{{{{identificador}}}}}."
        )
        if destino in ("oo", "-oo"):
            frases.append("Aquí se compara el comportamiento cuando la variable crece sin cota.")
        elif any(paso.tipo == "indeterminacion" for paso in pre.pasos):
            frases.append("La expresión original puede no dar un valor por sustitución directa y, aun así, tener límite.")
        else:
            frases.append("La sustitución directa confirma el valor al que se aproxima la función.")
        return cls(narracion=" ".join(frases), afirmaciones=tuple(afirmaciones), nivel_divulgacion=3)

    @classmethod
    def _cierre_limite_sin_valor(cls, pre, expresion: str, variable: str, destino: str) -> RespuestaGenerada:
        afirmaciones = []
        frases = ["Sí: aquí no existe un límite bilateral. Se comprueba comparando los dos lados."]
        for lado, valor, nombre in (
            ("-", pre.limite_izquierdo_corriente, "izquierda"),
            ("+", pre.limite_derecho_corriente, "derecha"),
        ):
            if valor:
                identificador = f"a{len(afirmaciones) + 1}"
                afirmaciones.append(Afirmacion(
                    identificador=identificador,
                    izquierda=f"lim {variable}->{destino}{lado} ({expresion})",
                    relacion="=", derecha=valor,
                    regla_declarada="límite lateral",
                ))
                frases.append(f"Por la {nombre}: {{{{{identificador}}}}}.")
        identificador = f"a{len(afirmaciones) + 1}"
        afirmaciones.append(Afirmacion(
            identificador=identificador,
            izquierda=f"lim {variable}->{destino} ({expresion})",
            relacion="=", derecha="no existe",
            regla_declarada="comparación de laterales",
        ))
        frases.append(f"Como no hay un valor común al acercarse, {{{{{identificador}}}}}.")
        return cls(narracion=" ".join(frases), afirmaciones=tuple(afirmaciones), nivel_divulgacion=3)

    @classmethod
    def _cierre_derivada(cls, pre, expresion: str, variable: str, orden=1) -> RespuestaGenerada:
        if orden > 1:
            return cls(narracion=(f"Tu resultado es correcto para la derivada de orden {orden}. "
                                 "Se deriva sucesivamente el resultado de cada etapa, manteniendo la misma variable. "
                                 "La comprobación final es {{a1}}."),
                       afirmaciones=(Afirmacion("a1", f"d^{orden}/d{variable}^{orden} ({expresion})", "=", pre.resultado_corriente),),
                       nivel_divulgacion=3)
        regla = (pre.regla_critica or "reglas de derivación").strip()
        vocabulario = (
            ("cociente", "la regla del cociente"),
            ("producto", "la regla del producto"),
            ("logarítmica", "la derivación logarítmica"),
            ("logar", "la derivada del logaritmo"),
            ("seno", "la derivada del seno"),
            ("coseno", "la derivada del coseno"),
            ("exponencial", "la derivada de la exponencial"),
            ("cadena", "la regla de la cadena"),
            ("suma", "la regla de la suma"),
            ("potencia", "la regla de la potencia"),
            ("constante", "la derivada de las constantes"),
        )
        etapas = []
        for paso in pre.pasos:
            if paso.tipo != "regla":
                continue
            rotulo = paso.regla.lower().split(":", 1)[0]
            nombre = next((nombre for clave, nombre in vocabulario if clave in rotulo), "")
            if nombre and nombre not in etapas:
                etapas.append(nombre)
        afirmaciones = []
        frases = ["Sí, tu derivada es correcta. Primero identificamos la estructura de la función."]
        if etapas:
            frases.append("El desarrollo usa, en orden, " + ", después ".join(etapas[:5]) + ".")
        for fuente, valor, regla_componente in pre.componentes_derivada:
            identificador = f"a{len(afirmaciones) + 1}"
            afirmaciones.append(Afirmacion(
                identificador=identificador,
                izquierda=f"d/d{variable} ({fuente})", relacion="=", derecha=valor,
                regla_declarada=regla_componente,
            ))
            frases.append(f"Esta parte se deriva así: {{{{{identificador}}}}}.")
        if pre.paso_intermedio_corriente and pre.paso_intermedio_corriente != pre.resultado_corriente:
            identificador = f"a{len(afirmaciones) + 1}"
            afirmaciones.append(Afirmacion(
                identificador=identificador, izquierda=f"d/d{variable} ({expresion})",
                relacion="=", derecha=pre.paso_intermedio_corriente,
                regla_declarada=pre.paso_intermedio_regla,
            ))
            frases.append(f"Con esas partes aplicamos la {pre.paso_intermedio_regla}: {{{{{identificador}}}}}.")
        identificador = f"a{len(afirmaciones) + 1}"
        afirmaciones.append(Afirmacion(
            identificador=identificador, izquierda=f"d/d{variable} ({expresion})",
            relacion="=", derecha=pre.resultado_corriente,
            regla_declarada=regla,
        ))
        frases.append(f"Después reunimos y simplificamos los términos: {{{{{identificador}}}}}.")
        return cls(narracion=" ".join(frases), afirmaciones=tuple(afirmaciones), nivel_divulgacion=3)

    @classmethod
    def desde_precomputo(
        cls, precomputo, expresion: str, variable: str = "x", orden: int = 1
    ) -> RespuestaGenerada | None:
        """El desarrollo que el CAS ya calculó, como respuesta emitible.

        `PM-B31` · `D-21`: cuando el arbitraje pide nivel 3 y el generador no
        cumple —ni afirma, o afirma algo que la verificación tumba— el sistema
        emite **esto** en vez de caer a un sondeo. Quien lleva cinco intentos no
        puede recibir otra pregunta.

        **No contradice `ADR-013` §7.3 ni `R-22`.** Lo que aquéllos prohíben es
        que el desarrollo precalculado **entre al contexto del generador** —y
        `Precomputo.truncado()` sigue haciéndolo—. Esto es la dirección
        contraria: se emite **como respuesta**, y el generador no lo ve.

        🐛 **Es UNA afirmación y no tantas como pasos, y lo decidió el propio
        contrato.** `D-21` dio por hecho que los `PasoDerivacion` servían de
        material —*«ya lleva `latex` y `regla`»*—. Al construirlo con ellos, la
        respuesta **salió inadmisible**: el campo `regla` de un paso no es el
        nombre de una regla sino una descripción del motor, y algunas traen
        LaTeX dentro —*«$\\frac{d}{dx}x^2 = 2 \\cdot x^{2-1}$»*—, de modo que
        `C1` invalidaba la narración entera. Lo atrapó `problemas()` en una
        prueba, y es exactamente la razón por la que este respaldo pasa por el
        mismo control que cualquier respuesta del generador.

        Así que se nombra **la regla crítica**, que sí es vocabulario del
        dominio y viene limpia, y la afirmación es la única cosa concreta y
        comprobable: el resultado. Emitir el desarrollo paso a paso completo
        exige que el motor entregue sus pasos como nombre + igualdad separados,
        y hoy no lo hace — queda anotado en `PLAN-MAESTRO.md`, no fingido aquí.

        Devuelve `None` cuando no hay con qué —sin precómputo, con error, o sin
        el resultado en notación corriente—. Quien llame decide qué hacer;
        aquí no se inventa un desarrollo que no se calculó.
        """
        if precomputo is None or not precomputo.ok or not precomputo.resultado_corriente:
            return None

        regla = (precomputo.regla_critica or "").strip()
        return cls(
            narracion=(
                "Lo hemos intentado ya varias veces, así que vamos a verlo entero. "
                + (f"En {{{{c1}}}} lo que manda es la {regla}, " if regla
                   else "Para {{c1}}, ")
                + "y el resultado es {{a1}}. Comprueba en qué paso se te fue."
            ),
            afirmaciones=(
                Afirmacion(
                    identificador="a1",
                    izquierda=(f"d/d{variable} ({expresion})" if orden == 1
                               else f"d^{orden}/d{variable}^{orden} ({expresion})"),
                    relacion="=",
                    derecha=precomputo.resultado_corriente,
                    regla_declarada=regla,
                ),
            ),
            nivel_divulgacion=3,
            citadas=(ExpresionCitada("c1", expresion),),
        )

    # ── Construcción desde lo que devuelve el proveedor ──────────────────────

    @classmethod
    def desde_objeto(cls, datos: object) -> RespuestaGenerada:
        """Construye la respuesta desde el objeto del proveedor.

        `ADR-014` C3: un objeto malformado **no se reintenta en silencio**. Se
        levanta un error explícito para que el adaptador lo registre y el
        orquestador descienda al nivel 1. `ADR-007` E6 prohíbe expresamente la
        degradación silenciosa, que en la iteración 0 convertía un fallo del
        proveedor en una clase válida con confianza cero.
        """
        if not isinstance(datos, dict):
            raise RespuestaMalformada(
                f"se esperaba un objeto y llegó {type(datos).__name__}"
            )

        narracion = datos.get("narracion")
        if not isinstance(narracion, str):
            raise RespuestaMalformada("falta la narración o no es texto")

        crudas = datos.get("afirmaciones", [])
        if not isinstance(crudas, (list, tuple)):
            raise RespuestaMalformada("«afirmaciones» debe ser una lista")

        afirmaciones = []
        for i, a in enumerate(crudas):
            if not isinstance(a, dict):
                raise RespuestaMalformada(f"la afirmación {i} no es un objeto")
            faltan = [c for c in ("id", "izquierda", "relacion", "derecha") if c not in a]
            if faltan:
                raise RespuestaMalformada(
                    f"la afirmación {i} no declara: {', '.join(faltan)}"
                )
            afirmaciones.append(
                Afirmacion(
                    identificador=str(a["id"]),
                    izquierda=str(a["izquierda"]),
                    relacion=str(a["relacion"]),
                    derecha=str(a["derecha"]),
                    regla_declarada=str(a.get("regla", "")),
                )
            )

        # `ADR-014` §5.4 · las expresiones que solo se mencionan. Opcionales:
        # una respuesta sin ninguna es perfectamente válida, y por eso su
        # ausencia no es un objeto malformado.
        crudas_citadas = datos.get("citadas", [])
        if not isinstance(crudas_citadas, (list, tuple)):
            raise RespuestaMalformada("«citadas» debe ser una lista")

        citadas = []
        for i, c in enumerate(crudas_citadas):
            if not isinstance(c, dict):
                raise RespuestaMalformada(f"la expresión citada {i} no es un objeto")
            faltan = [k for k in ("id", "expresion") if k not in c]
            if faltan:
                raise RespuestaMalformada(
                    f"la expresión citada {i} no declara: {', '.join(faltan)}"
                )
            citadas.append(
                ExpresionCitada(identificador=str(c["id"]), expresion=str(c["expresion"]))
            )

        nivel = datos.get("nivel", 1)
        if not isinstance(nivel, int) or isinstance(nivel, bool):
            raise RespuestaMalformada("«nivel» debe ser un entero de la escala")

        return cls(
            narracion=narracion,
            afirmaciones=tuple(afirmaciones),
            nivel_divulgacion=nivel,
            citadas=tuple(citadas),
        )


def _dividir_en_frases(texto: str) -> list[str]:
    """Divide conservando el signo de cierre, para no romper la puntuación."""
    partes = re.split(r"(?<=[.!?¿¡])\s+", texto)
    return [p for p in partes if p.strip()]
