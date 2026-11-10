from __future__ import annotations

import re
from dataclasses import dataclass

from dominio.modelo.deteccion_matematica import hallar_matematica
from dominio.modelo.matematica import BloqueVerificable


_REFERENCIA = re.compile(r"\{\{\s*([A-Za-z0-9_-]+)\s*\}\}")

class RespuestaMalformada(ValueError):
    pass

@dataclass(frozen=True)
class Afirmacion:

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

    identificador: str
    expresion: str

@dataclass(frozen=True)
class RespuestaGenerada:

    narracion: str
    afirmaciones: tuple[Afirmacion, ...] = ()
    nivel_divulgacion: int = 1

    citadas: tuple[ExpresionCitada, ...] = ()

    @property
    def referencias(self) -> tuple[str, ...]:
        return tuple(_REFERENCIA.findall(self.narracion))

    @property
    def identificadores(self) -> set[str]:
        return {a.identificador for a in self.afirmaciones} | {
            c.identificador for c in self.citadas
        }

    def bloques(self) -> tuple[BloqueVerificable, ...]:
        return tuple(a.como_bloque() for a in self.afirmaciones)

    def problemas(self) -> list[str]:
        fallos: list[str] = []

        if not self.narracion.strip():
            fallos.append("la narración está vacía")

        if not 1 <= self.nivel_divulgacion <= 3:
            fallos.append(
                f"nivel de divulgación fuera de la escala: {self.nivel_divulgacion}"
            )

        if self.nivel_divulgacion == 1 and self.afirmaciones:
            fallos.append(
                "el nivel 1 es de sondeo y no puede llevar afirmaciones matemáticas"
            )

        huerfanas = sorted(set(self.referencias) - self.identificadores)
        if huerfanas:
            fallos.append(
                "la narración cita afirmaciones que no existen: " + ", ".join(huerfanas)
            )

        sueltas = sorted(self.identificadores - set(self.referencias))
        if sueltas:
            fallos.append(
                "hay afirmaciones declaradas que la narración no cita: "
                + ", ".join(sueltas)
            )

        vistos, repetidos = set(), set()
        for a in (*self.afirmaciones, *self.citadas):
            (repetidos if a.identificador in vistos else vistos).add(a.identificador)
        if repetidos:
            fallos.append(
                "identificadores de afirmación repetidos: " + ", ".join(sorted(repetidos))
            )

        for marcador in self.matematica_suelta():
            fallos.append(f"hay matemática fuera de referencia: {marcador}")

        return fallos

    def matematica_suelta(self) -> list[str]:
        return hallar_matematica(_REFERENCIA.sub(" ", self.narracion))

    @property
    def admisible(self) -> bool:
        return not self.problemas()

    def podada(self) -> RespuestaGenerada:
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

    @classmethod
    def desde_transformacion_verificada(cls, ctx) -> RespuestaGenerada | None:
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

    @classmethod
    def desde_objeto(cls, datos: object) -> RespuestaGenerada:
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
    partes = re.split(r"(?<=[.!?¿¡])\s+", texto)
    return [p for p in partes if p.strip()]
