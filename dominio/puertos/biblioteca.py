"""
biblioteca.py — Puerto de la biblioteca de fuentes · Fase 5
============================================================

`EQ-013` decidió que el estudiante pueda consultar la fuente original de un
fragmento. Este puerto es el contrato de esa consulta, y su forma sale de una
distinción que la Fase 5 exige y que hasta hoy nadie modelaba:

    **que un archivo exista no autoriza a publicarlo.**

`corpus/FUENTES.md` conserva la decisión por obra y canal. Desde el 2026-09-05
las cinco obras del corpus están autorizadas para el piloto institucional
autenticado; eso no convierte su presencia local en acceso público. Este
puerto traduce esa puerta a tipos y el borde HTTP añade la sesión.

Las seis situaciones que NO son la misma
-----------------------------------------
El encargo de Fase 5 pide separarlas, y se separan porque cada una falla de una
manera distinta y el estudiante merece un mensaje distinto:

| # | Situación | Qué la decide |
|---|---|---|
| 1 | El archivo existe en el disco | `Path.is_file()` en el entorno que sirve |
| 2 | El recurso está catalogado | Aparece en `FUENTES.md` y en el catálogo de partes |
| 3 | El recurso conserva procedencia | `Procedencia` del fragmento · `DD-15` |
| 4 | El recurso está autorizado | La tabla de publicación por obra · `EQ-013` |
| 5 | El recurso es servible aquí | 1 + 2 + 4, en este despliegue |
| 6 | El recurso fue retirado | Decisión posterior que lo saca del flujo |

**Nunca se colapsan.** Un PDF presente y no autorizado y un PDF autorizado y
ausente son dos hechos opuestos: el primero es una puerta que funciona, el
segundo un despliegue incompleto. Confundirlos en un `404` genérico borraría la
única distinción que la puerta de publicación existe para conservar.

Por qué el permiso es un dato y no una constante
-------------------------------------------------
Porque la autorización puede concederse o retirarse sin cambiar este contrato.
El permiso se lee de `FUENTES.md`, donde queda registrada la decisión aprobada;
la autenticación institucional se comprueba por separado en las rutas HTTP.


"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable

#: Forma de la clave de obra: tres mayúsculas, igual que en `puertos/corpus.py`.
#: Se repite la expresión y no se importa a propósito: son dos contratos
#: distintos y atarlos haría que cambiar uno moviera el otro sin quererlo.
_CLAVE_DE_OBRA = re.compile(r"^[A-Z]{3}$")

#: Forma del identificador de fragmento tal como lo escriben los archivos de
#: `contenido/corpus/fragmentos/`: `F-` y tres dígitos.
_IDENTIFICADOR_DE_FRAGMENTO = re.compile(r"^F-\d{3}$")

#: Forma del identificador de parte: la clave de obra, dos puntos y el nombre
#: que el catálogo le da. Sólo minúsculas, dígitos y guiones en la segunda
#: mitad, que es lo que viaja por una URL sin escapar.
_IDENTIFICADOR_DE_PARTE = re.compile(r"^[A-Z]{3}:[a-z0-9][a-z0-9-]{0,63}$")

#: Nombre de archivo admisible dentro del directorio de una obra. **Lista
#: blanca y no lista negra**: se declara lo que se acepta —minúscula inicial,
#: dígitos, guion, guion bajo, punto y una de dos extensiones— en vez de
#: enumerar lo que se rechaza. Una lista negra de `..`, barras, dos puntos y
#: unidades de Windows deja fuera la siguiente forma que nadie previó; ésta no
#: admite ninguna, incluidas las mayúsculas y todo lo que no sea ASCII.
_NOMBRE_SIMPLE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}\.(md|pdf)$")


class Canal(StrEnum):
    """Las cuatro superficies que una obra puede exponer, y se autorizan aparte.

    `FUENTES.md` lleva **tres** columnas —PDF completo, Markdown continuo y
    fragmentos citados— porque son las tres que el equipo evalúa. `PDF_DIVIDIDO`
    es la cuarta y **no tiene columna propia**: se resuelve con el permiso del
    PDF completo, porque publicar todas las partes de una obra es publicar la
    obra. Inventarle una columna más permisiva sería abrir por la puerta de
    atrás lo que la de delante conserva cerrado.
    """

    FRAGMENTO = "fragmento"
    MARKDOWN_CONTINUO = "markdown_continuo"
    PDF_DIVIDIDO = "pdf_dividido"
    PDF_COMPLETO = "pdf_completo"


class Permiso(StrEnum):
    """Estado de autorización de un canal para una obra concreta.

    Sólo `PERMITIDO` habilita. `PENDIENTE` y `BLOQUEADO` no se distinguen por
    lo que dejan hacer —ninguno deja— sino por lo que le dicen al equipo: uno
    es un expediente sin terminar y el otro una decisión ya tomada.
    """

    PERMITIDO = "permitido"
    PENDIENTE = "pendiente"
    BLOQUEADO = "bloqueado"
    RETIRADO = "retirado"
    FUERA_DEL_CORPUS = "fuera_del_corpus"

    @property
    def habilita(self) -> bool:
        return self is Permiso.PERMITIDO


class MotivoIndisponible(StrEnum):
    """Por qué no se puede servir algo. **Uno por causa, nunca un genérico.**

    El encargo de Fase 5 los pide distinguibles, y la razón es operativa: el
    equipo tiene que poder leer un registro y saber si le falta evidencia, le
    falta un archivo o le sobra una petición manipulada. Los tres producen hoy
    la misma pantalla para el estudiante y tres acciones distintas para quien
    opera.
    """

    #: No hay ningún fragmento con ese identificador. Incluye `F-179` y `F-180`,
    #: que **no existen** aunque caigan dentro del rango `F-001`–`F-273`.
    FRAGMENTO_INEXISTENTE = "fragmento_inexistente"
    #: El identificador tiene forma válida pero no está en el catálogo. Es lo
    #: que responde una clave inventada o una parte que ninguna obra declara.
    RECURSO_NO_CATALOGADO = "recurso_no_catalogado"
    #: La obra existe y el canal pedido no está autorizado para ella.
    OBRA_NO_AUTORIZADA = "obra_no_autorizada"
    #: Catalogado y autorizado, pero el archivo no está en este entorno. Es el
    #: caso de un despliegue incompleto al que no llegaron las copias
    #: institucionales catalogadas.
    ARCHIVO_AUSENTE = "archivo_ausente"
    #: La página impresa no se puede llevar a una página interna porque el
    #: desfase de esa obra no está medido. **No se estima**: hoy aplica a `PIS`,
    #: que no tiene PDF completo en el lote institucional.
    PAGINA_SIN_MAPEO = "pagina_sin_mapeo"
    #: Todo lo demás está bien y aun así el entorno no puede servirlo.
    RECURSO_NO_SERVIBLE = "recurso_no_servible"
    #: Estuvo disponible y una decisión posterior lo sacó del flujo. Se
    #: distingue de `OBRA_NO_AUTORIZADA` porque el historial puede conservar la
    #: evidencia de que se consultó, y esa evidencia no se borra.
    RECURSO_RETIRADO = "recurso_retirado"


class Indisponible(Exception):
    """Lo pedido no se puede servir, y el motivo es parte del contrato."""

    def __init__(self, motivo: MotivoIndisponible, detalle: str = "") -> None:
        super().__init__(detalle or motivo.value)
        self.motivo = motivo
        self.detalle = detalle


@dataclass(frozen=True)
class Disponibilidad:
    """Qué se puede hacer con un canal de una obra, y por qué.

    Los tres campos responden a tres preguntas que se contestan por separado y
    que sólo juntas autorizan a servir:

    - `permiso` — ¿el equipo lo autorizó? Sale de `FUENTES.md`.
    - `catalogado` — ¿el sistema sabe qué archivo es? Sale del catálogo.
    - `archivo_presente` — ¿está en este disco? Se comprueba al servir.
    """

    canal: Canal
    permiso: Permiso
    catalogado: bool = False
    archivo_presente: bool = False

    @property
    def servible(self) -> bool:
        """Las tres condiciones a la vez. Cualquier ausencia bloquea."""
        return self.permiso.habilita and self.catalogado and self.archivo_presente

    def motivo(self) -> MotivoIndisponible | None:
        """La causa **más específica** por la que no se puede servir.

        El orden importa y no es alfabético: se responde primero lo que el
        equipo puede arreglar con una decisión —el permiso— y sólo después lo
        que depende del despliegue. Al revés, una obra sin autorizar cuyo
        archivo tampoco esté presente contestaría «archivo ausente», y alguien
        copiaría el PDF creyendo que eso la habilita.
        """
        if self.permiso is Permiso.RETIRADO:
            return MotivoIndisponible.RECURSO_RETIRADO
        if not self.permiso.habilita:
            return MotivoIndisponible.OBRA_NO_AUTORIZADA
        if not self.catalogado:
            return MotivoIndisponible.RECURSO_NO_CATALOGADO
        if not self.archivo_presente:
            return MotivoIndisponible.ARCHIVO_AUSENTE
        return None


@dataclass(frozen=True)
class Obra:
    """Una obra del catálogo, con lo que se puede decir de ella en público.

    Los datos bibliográficos —autoría, título, páginas del archivo— **sí se
    pueden mostrar aunque la obra no esté autorizada**: `FUENTES.md` lo dice
    expresamente (*«Los metadatos bibliográficos y la explicación de
    procedencia sí pueden mostrarse»*). Lo que la autorización gobierna es el
    contenido, no la ficha.
    """

    clave: str
    titulo: str
    #: Autoría tal como la escribe la ficha de `FUENTES.md`, sin normalizar.
    autoria: str = ""
    #: Cuántas páginas declara el archivo, cuando la ficha lo dice. `None` es
    #: «no consta», y no se sustituye por cero.
    paginas_del_archivo: int | None = None
    #: Enlace externo que la ficha conserva. `FUENTES.md` los marca casi todos
    #: «por verificar», y ese matiz viaja con el dato en `referencia_verificada`.
    referencia_externa: str = ""
    referencia_verificada: bool = False
    #: Disponibilidad por canal. Las claves ausentes se leen como bloqueadas.
    disponibilidad: dict[Canal, Disponibilidad] = field(default_factory=dict)

    def validar(self) -> list[str]:
        fallos = []
        if not _CLAVE_DE_OBRA.match(self.clave or ""):
            fallos.append(f"clave de obra inválida «{self.clave}»: son tres mayúsculas")
        if not self.titulo.strip():
            fallos.append(f"{self.clave}: sin título legible")
        return fallos

    def permiso_de(self, canal: Canal) -> Permiso:
        """El permiso de un canal. **Ausente significa bloqueado.**

        Es la `regla de fallo seguro` de `FUENTES.md` §5 aplicada al tipo: una
        obra que el catálogo no menciona para un canal no queda «sin decidir»,
        queda sin autorizar. Cualquier otro valor por defecto publicaría por
        descuido.
        """
        vista = self.disponibilidad.get(canal)
        return vista.permiso if vista else Permiso.BLOQUEADO


@dataclass(frozen=True)
class Parte:
    """Un trozo de obra: su transcripción Markdown y su PDF dividido.

    Una parte **no es un capítulo del libro** sino la unidad en que el equipo
    troceó la obra al transcribirla, y por eso su nombre sale del catálogo y no
    de una convención adivinada. Lo que sí es del libro es el rango de páginas
    impresas que cubre, y ése es el dato con el que el resolutor trabaja.

    ⚠️ `pagina_impresa_inicial` es la **primera página impresa contenida en la
    parte**, no la primera hoja del archivo. La diferencia entre las dos es
    justamente lo que `Resolutor` calcula, y suponer que coinciden es el error
    que el encargo de Fase 5 prohíbe por su nombre.
    """

    identificador: str
    obra: str
    titulo: str
    pagina_impresa_inicial: int
    pagina_impresa_final: int
    #: Nombre del archivo Markdown **dentro** del directorio de la obra. Nunca
    #: una ruta: el adaptador la compone, y por eso no puede traer `..`.
    archivo_markdown: str = ""
    #: Ídem para el PDF dividido.
    archivo_pdf: str = ""

    def validar(self) -> list[str]:
        fallos = []
        if not _IDENTIFICADOR_DE_PARTE.match(self.identificador or ""):
            fallos.append(f"identificador de parte inválido «{self.identificador}»")
        if not _CLAVE_DE_OBRA.match(self.obra or ""):
            fallos.append(f"{self.identificador}: clave de obra inválida «{self.obra}»")
        elif not self.identificador.startswith(f"{self.obra}:"):
            fallos.append(
                f"{self.identificador}: el identificador no empieza por su obra «{self.obra}»"
            )
        if self.pagina_impresa_inicial < 1:
            fallos.append(f"{self.identificador}: página inicial inválida")
        if self.pagina_impresa_final < self.pagina_impresa_inicial:
            fallos.append(
                f"{self.identificador}: rango invertido "
                f"({self.pagina_impresa_inicial}–{self.pagina_impresa_final})"
            )
        for campo, valor in (("markdown", self.archivo_markdown), ("pdf", self.archivo_pdf)):
            if valor and not _NOMBRE_SIMPLE.match(valor):
                fallos.append(
                    f"{self.identificador}: nombre de archivo {campo} no admisible «{valor}»"
                )
        return fallos

    def contiene(self, pagina_impresa: int) -> bool:
        return self.pagina_impresa_inicial <= pagina_impresa <= self.pagina_impresa_final


@dataclass(frozen=True)
class Localizacion:
    """Dónde está un pasaje: en la obra, en la parte y en el archivo.

    Es el resultado del resolutor y lleva **las tres coordenadas a la vez**
    porque las tres se muestran y ninguna se deduce de otra en la interfaz.

    ⚠️ `exacta` no adorna. `DD-21` admitió que las obras no imprimen el número
    en todas sus páginas, de modo que la mayoría de los fragmentos cita un
    **rango** y no una página. Presentar «página 146» cuando el dato es «entre
    la 146 y la 173» sería exactamente la afirmación que `DD-21` evitó guardar.
    """

    obra: str
    parte: str
    pagina_impresa: int
    pagina_interna_en_parte: int
    #: Hoja dentro del PDF completo de la obra, cuando su desfase está medido.
    #: `None` cuando no lo está — `PIS` hoy. **No se estima.**
    pagina_interna_en_obra: int | None = None
    #: Final del rango citado, cuando la procedencia declara uno.
    pagina_impresa_hasta: int | None = None

    @property
    def exacta(self) -> bool:
        return self.pagina_impresa_hasta is None


@runtime_checkable
class PuertoBiblioteca(Protocol):
    """Lo que el borde puede pedirle a la biblioteca. **Sólo por identificador.**

    Ninguna firma acepta una ruta, un nombre de archivo ni una URL. No es una
    convención: es la barrera. El encargo de Fase 5 prohíbe que el cliente
    elija el archivo, y la única forma de garantizarlo es que el tipo no
    permita expresarlo.
    """

    def obra(self, clave: str) -> Obra:
        """La obra de esa clave. `Indisponible` si no está catalogada."""
        ...

    def obras(self) -> tuple[Obra, ...]:
        """Todas las obras del catálogo, en orden estable."""
        ...

    def parte(self, identificador: str) -> Parte:
        """La parte de ese identificador. `Indisponible` si no existe."""
        ...

    def partes_de(self, clave: str) -> tuple[Parte, ...]:
        """Las partes de una obra, ordenadas por página impresa inicial."""
        ...

    def localizar(
        self, clave: str, pagina_impresa: int, pagina_hasta: int | None = None
    ) -> Localizacion:
        """Lleva una página impresa a su parte y a su página interna."""
        ...

    def disponibilidad(self, clave: str, canal: Canal) -> Disponibilidad:
        """Qué se puede hacer con ese canal de esa obra, aquí y ahora."""
        ...


def clave_de_obra_valida(clave: str) -> bool:
    """Si una cadena tiene forma de clave de obra. No dice si existe."""
    return bool(_CLAVE_DE_OBRA.match(clave or ""))


def identificador_de_fragmento_valido(identificador: str) -> bool:
    """Si una cadena tiene forma de identificador de fragmento.

    **Forma, no existencia.** `F-179` la tiene y no existe, y ésa es justamente
    la pareja de casos que el encargo pide no confundir: rechazar por forma es
    una petición mal escrita; no encontrarlo es `FRAGMENTO_INEXISTENTE`.
    """
    return bool(_IDENTIFICADOR_DE_FRAGMENTO.match(identificador or ""))


def identificador_de_parte_valido(identificador: str) -> bool:
    """Si una cadena tiene forma de identificador de parte."""
    return bool(_IDENTIFICADOR_DE_PARTE.match(identificador or ""))


def nombre_de_archivo_admisible(nombre: str) -> bool:
    """Si un nombre puede componer una ruta dentro del directorio de una obra."""
    return bool(_NOMBRE_SIMPLE.match(nombre or ""))
