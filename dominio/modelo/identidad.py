"""
identidad.py — Quién es la persona y qué declaró en el onboarding (`EQ-020`)
==============================================================================

El primer tipo explícito de la Fase 3. Hasta hoy la identidad vivía como cuatro
claves sueltas dentro de un `dict` del almacén de sesiones
(`adaptadores/entrantes/http/sesiones.py`) y la edad como un entero con valor por
defecto decidido por una variable de entorno (`aviso_legal.edad_por_defecto()`).
Nada de eso puede sostener `EQ-020`: un `dict` no rechaza una edad imposible, no
sabe si el perfil está completo y no distingue «no declarada» de «18».

Qué es identidad y qué es perfil, y por qué van juntos
--------------------------------------------------------------
`Identidad` es lo que trae Google: el sujeto estable, el correo y el nombre.
`PerfilOnboarding` añade lo que la persona declara: edad exacta, programa,
semestre y su vínculo con una clase. Van en el mismo módulo porque el onboarding
sólo tiene sentido colgado de una identidad verificada —`EQ-020`: «sólo existen
usuarios autenticados con cuenta institucional»— y separarlos en dos archivos
habría obligado a importarlos siempre juntos.

El identificador estable es el sujeto de Google, no el correo
--------------------------------------------------------------------
`DD-18` y `EQ-020`. El correo puede cambiar de alias dentro del mismo Workspace;
el `sub` del `id_token` no. Es además el valor que hoy ya viaja como
`identificador_estable` en la sesión autenticada, así que este modelo se apoya en
un dato que el sistema ya produce: no reinterpreta ninguno.

La ausencia de edad NO es mayoría de edad
------------------------------------------------
`edad` admite `None` y eso significa **no declarada**, que deja el perfil
incompleto. Es la corrección deliberada de `DD-26`, que durante el piloto asumía
18 por defecto: `EQ-020` dice que quien no la suministre puede consultar las
rutas públicas pero no usar el tutor, y para eso hace falta que «no la dijo» sea
un valor distinto de cualquier edad.

⚠️ Este módulo no valida identidad ni edad contra ninguna fuente. `EQ-020` es
explícito en que la edad es **autodeclarada**. Lo que sí hace es impedir que un
valor imposible —negativo, booleano, absurdo— entre al sistema disfrazado de
declaración.


"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

#: `RL-09` y `EQ-016`. No es un umbral calibrable: es la mayoría de edad legal.
#: Se repite aquí en vez de importarse de `adaptadores/entrantes/http/
#: aviso_legal.py` porque el dominio no puede depender de un adaptador; que las
#: dos valgan 18 lo comprueba `pruebas/unidad/test_dominio_consentimiento.py`.
MAYORIA_DE_EDAD = 18

#: El rango que se admite como edad **declarada**. No valida identidad: filtra lo
#: imposible. Una edad negativa no es «menor de edad», es un cuerpo mal formado,
#: y tratarla como minoría bloquearía a alguien por un error de tecleo.
EDAD_MINIMA_ADMISIBLE = 0
EDAD_MAXIMA_ADMISIBLE = 120

#: El rango admisible de semestre. Mismo criterio que la edad.
SEMESTRE_MINIMO_ADMISIBLE = 1
SEMESTRE_MAXIMO_ADMISIBLE = 20


class IdentidadInvalida(ValueError):
    """Un dato de identidad o de perfil que el sistema no puede aceptar.

    Se levanta en el borde del tipo —`__post_init__`— y no más tarde: un
    `PerfilOnboarding` que existe es un perfil cuyos valores ya son admisibles,
    y ningún consumidor tiene que volver a comprobarlo.
    """


class CategoriaDeEdad(StrEnum):
    """Tres valores, no dos. `NO_DECLARADA` es el que `DD-26` no tenía."""

    MENOR = "menor"
    ADULTO = "adulto"
    NO_DECLARADA = "no_declarada"


def categoria_de_edad(edad: int | None) -> CategoriaDeEdad:
    """`EQ-016`: menor es **edad inferior a 18**. El límite exacto es adulto.

    `None` devuelve `NO_DECLARADA` y nunca `ADULTO`: es la regla que hace que un
    perfil sin edad quede en onboarding en vez de habilitarse.
    """
    if edad is None:
        return CategoriaDeEdad.NO_DECLARADA
    return CategoriaDeEdad.MENOR if edad < MAYORIA_DE_EDAD else CategoriaDeEdad.ADULTO


def _texto_obligatorio(valor: str, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise IdentidadInvalida(f"{campo} no puede quedar vacío")
    return valor.strip()


def _entero_o_nada(valor: int | None, campo: str, minimo: int, maximo: int) -> int | None:
    """`None`, o un entero dentro del rango. Un booleano no cuenta como entero.

    `True` es `int` en Python y aquí no vale: sería el booleano de antes de
    `DD-26` colándose por el campo nuevo, y `True` valdría 1 —una edad de un
    año— sin que nadie lo hubiera escrito.
    """
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise IdentidadInvalida(f"{campo} tiene que ser un entero o quedar sin declarar")
    if not minimo <= valor <= maximo:
        raise IdentidadInvalida(f"{campo} fuera del rango admisible [{minimo}, {maximo}]")
    return valor


def exigir_edad_admisible(edad: int | None) -> int | None:
    """La edad declarada, o `None`. Levanta `IdentidadInvalida` si es imposible.

    Pública para que un repositorio pueda rechazar un valor **antes** de abrir
    una conexión, sin tener que fabricar un `PerfilOnboarding` de mentira sólo
    para aprovechar su validación.
    """
    return _entero_o_nada(edad, "edad", EDAD_MINIMA_ADMISIBLE, EDAD_MAXIMA_ADMISIBLE)


def exigir_semestre_admisible(semestre: int | None) -> int | None:
    """El semestre declarado, o `None`. Mismo criterio que la edad."""
    return _entero_o_nada(
        semestre, "semestre", SEMESTRE_MINIMO_ADMISIBLE, SEMESTRE_MAXIMO_ADMISIBLE
    )


@dataclass(frozen=True, slots=True)
class Identidad:
    """Lo que Google confirma, y nada más (`DD-18`, `EQ-020`).

    No hay teléfono ni documento de identidad, y no puede haberlos sin cambiar
    este tipo: `EQ-020` lo prohíbe y una restricción que se puede saltar
    añadiendo una clave a un `dict` no es una restricción.
    """

    sujeto_google: str
    correo: str
    nombre: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "sujeto_google", _texto_obligatorio(self.sujeto_google, "sujeto_google"))
        correo = _texto_obligatorio(self.correo, "correo").lower()
        if "@" not in correo[1:]:
            raise IdentidadInvalida("correo no tiene la forma de una dirección")
        object.__setattr__(self, "correo", correo)
        object.__setattr__(self, "nombre", (self.nombre or "").strip())


@dataclass(frozen=True, slots=True)
class PerfilOnboarding:
    """La identidad más lo que `EQ-020` pide confirmar antes del tutor.

    `clase_vinculada` es un booleano y no un identificador de clase **a
    propósito**: la relación persona↔clase ya la sostiene `clase_matricula`
    (`08-clases.sql`) por el mismo sujeto, y duplicarla aquí crearía dos
    respuestas para la misma pregunta. Quien construye el perfil la resuelve
    consultando ese mecanismo; ver `AdaptadorIdentidadPostgres`.
    """

    identidad: Identidad
    edad: int | None = None
    facultad: str = ""
    programa: str = ""
    semestre: int | None = None
    clase_vinculada: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.identidad, Identidad):
            raise IdentidadInvalida("un perfil de onboarding cuelga de una identidad verificada")
        object.__setattr__(
            self,
            "edad",
            _entero_o_nada(self.edad, "edad", EDAD_MINIMA_ADMISIBLE, EDAD_MAXIMA_ADMISIBLE),
        )
        object.__setattr__(
            self,
            "semestre",
            _entero_o_nada(
                self.semestre, "semestre", SEMESTRE_MINIMO_ADMISIBLE, SEMESTRE_MAXIMO_ADMISIBLE
            ),
        )
        facultad = (self.facultad or "").strip()
        programa = (self.programa or "").strip()
        object.__setattr__(self, "facultad", facultad)
        object.__setattr__(self, "programa", programa)
        # Una fila histórica puede no tener facultad todavía; la migración la
        # conserva así hasta que una persona autorizada la corrija. En cuanto
        # hay facultad, la pareja sí tiene que pertenecer al catálogo.
        if facultad and programa:
            from dominio.modelo.oferta_academica import (  # noqa: PLC0415
                OfertaAcademicaInvalida,
                exigir_oferta_valida,
            )

            try:
                exigir_oferta_valida(facultad, programa)
            except OfertaAcademicaInvalida as error:
                raise IdentidadInvalida(str(error)) from error
        object.__setattr__(self, "clase_vinculada", bool(self.clase_vinculada))

    @property
    def sujeto_google(self) -> str:
        return self.identidad.sujeto_google

    @property
    def categoria_de_edad(self) -> CategoriaDeEdad:
        return categoria_de_edad(self.edad)

    @property
    def es_menor(self) -> bool:
        """Sólo `True` con una edad declarada por debajo de 18.

        Sin edad devuelve `False` y eso **no** habilita nada: el perfil queda
        incompleto y `dominio/modelo/acceso.py` lo deja en onboarding. Son dos
        preguntas distintas y este módulo no las mezcla.
        """
        return self.categoria_de_edad is CategoriaDeEdad.MENOR

    @property
    def completo(self) -> bool:
        """El perfil mínimo de acceso, incluida la transición de filas heredadas.

        La facultad es obligatoria en toda alta nueva desde la migración 22,
        pero no se suma todavía a esta puerta: las filas anteriores se migran
        vacías a propósito y bloquearlas en masa impediría que el profesional
        las corrigiera de forma ordenada. El borde de onboarding sí rechaza un
        alta nueva sin facultad.
        """
        return (
            self.edad is not None
            and bool(self.programa)
            and self.semestre is not None
            and self.clase_vinculada
        )

    @property
    def campos_pendientes(self) -> tuple[str, ...]:
        """Qué falta, para que la pantalla de la sesión 5 no tenga que deducirlo."""
        faltan = []
        if self.edad is None:
            faltan.append("edad")
        if not self.programa:
            faltan.append("programa")
        if self.semestre is None:
            faltan.append("semestre")
        if not self.clase_vinculada:
            faltan.append("clase")
        return tuple(faltan)
