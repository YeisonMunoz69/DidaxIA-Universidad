"""
catalogo.py — La biblioteca de fuentes, leída de los archivos del corpus
=========================================================================

Implementa `PuertoBiblioteca` sobre tres archivos que ya existen y uno nuevo:

| Archivo | Qué aporta |
|---|---|
| `contenido/corpus/FUENTES.md` | las obras, su ficha y **el permiso por canal** |
| `contenido/corpus/PARTES.md` | el desfase de paginación y las partes |
| `contenido/corpus/fragmentos/` | los fragmentos y su procedencia |
| `contenido/corpus/_obras-md/` | los archivos, **cuando el entorno los tiene** |

Por qué el permiso se lee y no se escribe en el código
-------------------------------------------------------
`FUENTES.md` §«Cómo se diligencia realmente» paso 6 dice que la decisión
aprobada se sincroniza en su tabla de estado. Leerla de ahí es lo que hace que
autorizar una obra sea **editar un documento del equipo** y no desplegar
software. Hoy esa tabla bloquea las seis obras en los tres canales, y este
adaptador lo refleja tal cual.

La regla de fallo seguro, escrita como código
----------------------------------------------
`FUENTES.md` §5 la enuncia: *«ante duda de atribución, extensión, continuidad o
licencia, el fragmento queda deshabilitado»*. Aquí se traduce en tres reglas sin
excepción:

1. Sólo 🟢 autoriza. Cualquier otro símbolo, texto o celda vacía **bloquea**.
2. Una obra ausente de la tabla queda bloqueada en todos sus canales.
3. Un archivo de catálogo ilegible **no degrada a permisivo**: deja el catálogo
   sin obras, que es lo más restrictivo posible.


"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from adaptadores.salientes.corpus.cargador import FragmentoLeido, leer_todos
from dominio.puertos.biblioteca import (
    Canal,
    Disponibilidad,
    Indisponible,
    Localizacion,
    MotivoIndisponible,
    Obra,
    Parte,
    Permiso,
    clave_de_obra_valida,
    identificador_de_fragmento_valido,
    identificador_de_parte_valido,
    nombre_de_archivo_admisible,
)

#: Encabezado de ficha de obra: `### \`LOP\` · López Erazo`. La misma expresión
#: que usa `cargador.claves_de_obra()`, ampliada para quedarse también con el
#: nombre corto que va detrás del punto medio.
_FICHA_DE_OBRA = re.compile(r"^###\s+`([A-Z]{3})`\s*(?:·\s*(.+?))?\s*$", re.M)

#: Cualquier encabezado Markdown. Cierra la ficha anterior.
#:
#: 🐛 **Corregido el 2026-09-03, y el fallo era silencioso.** La primera versión
#: cortaba cada ficha en el siguiente `###`, de modo que la última —`PIS`— se
#: extendía hasta el final del archivo y recogía la fila `**Obra**` de la
#: sección §Obras consultadas. Resultado: `PIS` se presentaba como *«Swokowski,
#: Cálculo con Geometría Analítica»* con 244 páginas. Nada fallaba; sólo la
#: ficha mentía, que es la peor forma de fallar en un archivo de procedencia.
_ENCABEZADO = re.compile(r"^#{1,6}\s+\S", re.M)

#: Fila de la tabla de estado de publicación. Cinco celdas, la primera con la
#: clave entre acentos graves.
_FILA_DE_PERMISO = re.compile(
    r"^\|\s*`([A-Z]{3})`\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|\s*$", re.M
)

#: Fila `| **Obra** | … |` de la ficha, que lleva la referencia bibliográfica.
_FILA_DE_CAMPO = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|\s*$", re.M)

#: «571 páginas», «1 380 páginas», «244 hojas». El separador de millares puede
#: ser un espacio fino, así que se admite cualquier espacio en blanco.
_PAGINAS = re.compile(r"(\d[\d\s  ]*)\s*(?:páginas|paginas|hojas)")

#: Fila de la tabla de archivo del PDF completo de `PARTES.md`.
_FILA_DE_PDF_COMPLETO = re.compile(r"^\|\s*`([A-Z]{3})`\s*\|\s*([^|]*?)\s*\|\s*$", re.M)

#: Fila de la tabla de desfase de `PARTES.md`.
_FILA_DE_DESFASE = re.compile(r"^\|\s*`([A-Z]{3})`\s*\|\s*([^|]*?)\s*\|([^|]*)\|\s*$", re.M)

#: Fila de la tabla de partes de `PARTES.md`. Siete celdas.
_FILA_DE_PARTE = re.compile(
    r"^\|\s*([A-Za-z]{3}:[a-z0-9-]+)\s*\|\s*([A-Z]{3})\s*\|\s*([^|]*?)\s*"
    r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*$",
    re.M,
)

#: El único símbolo que autoriza. Se compara por presencia y no por igualdad de
#: la celda entera porque las celdas llevan además una explicación en prosa.
_AUTORIZA = "\U0001f7e2"  # 🟢

#: Los que explícitamente no autorizan. Están enumerados para poder distinguir
#: «pendiente» de «bloqueado» en el informe; ninguno habilita.
_PENDIENTE = "\U0001f7e1"  # 🟡
_BLOQUEA = "⛔"  # ⛔


def _permiso_de_celda(celda: str) -> Permiso:
    """Traduce una celda de la tabla de publicación a un `Permiso`.

    **Nada que no lleve 🟢 autoriza**, ni siquiera una celda que diga
    «autorizado» en palabras: la tabla es de símbolos y añadir una segunda vía
    de lectura convertiría un descuido de redacción en una publicación.
    """
    texto = celda.strip().lower()
    # Los símbolos primero, y en este orden. La celda de `LOP` dice
    # «⛔ pendiente (aval docente)»: lleva el símbolo que bloquea y la palabra
    # que matiza por qué. Leer la palabra antes que el símbolo invertiría la
    # frase. Ninguna de las dos lecturas autoriza, pero el informe del equipo
    # tiene que decir lo que la tabla dice.
    if _AUTORIZA in celda:
        return Permiso.PERMITIDO
    if _BLOQUEA in celda:
        if "fuera del corpus" in texto:
            return Permiso.FUERA_DEL_CORPUS
        if "retirar" in texto or "retirado" in texto:
            return Permiso.RETIRADO
        return Permiso.BLOQUEADO
    if _PENDIENTE in celda:
        return Permiso.PENDIENTE
    # Sin símbolo reconocible se lee la prosa, y sigue sin poder autorizar.
    if "fuera del corpus" in texto:
        return Permiso.FUERA_DEL_CORPUS
    if "retirar" in texto or "retirado" in texto:
        return Permiso.RETIRADO
    if "pendiente" in texto:
        return Permiso.PENDIENTE
    # Celda vacía, símbolo desconocido o texto libre. La regla de fallo seguro
    # manda: lo que no se entiende no se publica.
    return Permiso.BLOQUEADO


@dataclass(frozen=True)
class FichaDeFragmento:
    """Un fragmento con todo lo que hace falta para presentarlo honestamente.

    Reúne cuatro cosas que viven en sitios distintos y que la interfaz muestra
    juntas: el fragmento, su obra, dónde está y qué se puede abrir. Se compone
    aquí y no en el borde HTTP para que la ruta no tenga que saber de dónde
    sale cada mitad.
    """

    fragmento: FragmentoLeido
    obra: Obra
    #: `None` cuando la obra no tiene partes catalogadas o la página no cae en
    #: ninguna. **No es un fallo del fragmento**: es que el sistema todavía no
    #: sabe dónde abrir el archivo, y decirlo es mejor que abrir cualquier hoja.
    localizacion: Localizacion | None = None
    motivo_sin_localizacion: MotivoIndisponible | None = None


@dataclass(frozen=True)
class InformeDelCatalogo:
    """Lo que la construcción del catálogo encontró y lo que no pudo leer.

    Se devuelve junto al catálogo en vez de registrarse por un logger: quien lo
    construye —`/api/salud`, la herramienta de inventario, una prueba— decide
    qué hacer con cada fallo, y ninguno se pierde por no estar mirando.
    """

    obras: int = 0
    partes: int = 0
    fragmentos: int = 0
    fallos: tuple[str, ...] = ()
    #: Obras declaradas en `FUENTES.md` que la tabla de publicación no menciona.
    #: Quedan bloqueadas, y se nombran para que el hueco se vea.
    sin_fila_de_permiso: tuple[str, ...] = ()
    #: Si el directorio de transcripciones existe en este entorno.
    obras_md_presente: bool = False


@dataclass(frozen=True)
class DatosDelCatalogo:
    """Lo leído de los archivos, en un solo objeto.

    Existe para que `CatalogoDeFuentes` no reciba siete argumentos sueltos.
    No es una bolsa de utilidades: son las cinco tablas que forman el
    catálogo, y viajan juntas porque se leen juntas y se usan juntas.
    """

    obras: dict[str, Obra]
    partes: dict[str, Parte]
    desfases: dict[str, int | None]
    pdf_completo: dict[str, str]
    fragmentos: dict[str, FragmentoLeido]


class CatalogoDeFuentes:
    """`PuertoBiblioteca` sobre los archivos del corpus. **Sólo lectura.**

    Se construye una vez y se consulta muchas: leer `FUENTES.md` en cada
    petición sería releer 29 KB para responder un enlace. Lo que sí se comprueba
    en cada petición es la **presencia del archivo**, porque un despliegue puede
    montar el volumen de obras después de arrancar y lo contrario —cachear un
    «no está»— dejaría la biblioteca apagada hasta el siguiente reinicio.
    """

    def __init__(
        self, raiz_corpus: Path, datos: DatosDelCatalogo, informe: InformeDelCatalogo
    ) -> None:
        self._raiz = Path(raiz_corpus)
        self._obras = dict(datos.obras)
        self._partes = dict(datos.partes)
        self._desfases = dict(datos.desfases)
        self._pdf_completo = dict(datos.pdf_completo)
        self._fragmentos = dict(datos.fragmentos)
        self.informe = informe

    # ── construcción ────────────────────────────────────────────────────────

    @classmethod
    def desde_directorio(cls, raiz_corpus: Path) -> CatalogoDeFuentes:
        """Lee `FUENTES.md`, `PARTES.md` y `fragmentos/` de un directorio.

        Nunca levanta: un corpus ausente produce un catálogo vacío y un informe
        que lo explica. El tutor tiene que poder conversar sin biblioteca, igual
        que hoy conversa sin banco de conceptos.
        """
        raiz = Path(raiz_corpus)
        fallos: list[str] = []

        obras, sin_fila = _leer_obras(raiz / "FUENTES.md", fallos)
        partes, desfases, pdf_completo = _leer_partes(raiz / "PARTES.md", obras.keys(), fallos)
        fragmentos = _leer_fragmentos(raiz / "fragmentos", obras.keys(), fallos)

        obras_md = raiz / "_obras-md"
        informe = InformeDelCatalogo(
            obras=len(obras),
            partes=len(partes),
            fragmentos=len(fragmentos),
            fallos=tuple(fallos),
            sin_fila_de_permiso=tuple(sorted(sin_fila)),
            obras_md_presente=obras_md.is_dir(),
        )
        return cls(
            raiz,
            DatosDelCatalogo(obras, partes, desfases, pdf_completo, fragmentos),
            informe,
        )

    # ── obras ───────────────────────────────────────────────────────────────

    def obras(self) -> tuple[Obra, ...]:
        return tuple(self._obras[c] for c in sorted(self._obras))

    def obra(self, clave: str) -> Obra:
        # ⚠️ Los mensajes de `Indisponible` **viajan al cliente** dentro del
        # campo `diagnostico`, así que no nombran ningún archivo. Decir «no
        # está en FUENTES.md» parece inocente —es un documento versionado— pero
        # enseña la organización del servidor a quien sondea, y el operador no
        # gana nada: sabe de sobra dónde está su catálogo.
        if not clave_de_obra_valida(clave):
            raise Indisponible(
                MotivoIndisponible.RECURSO_NO_CATALOGADO,
                f"«{clave}» no tiene forma de clave de obra",
            )
        obra = self._obras.get(clave)
        if obra is None:
            raise Indisponible(
                MotivoIndisponible.RECURSO_NO_CATALOGADO,
                f"la obra «{clave}» no está en el catálogo de obras",
            )
        return obra

    # ── partes ──────────────────────────────────────────────────────────────

    def parte(self, identificador: str) -> Parte:
        if not identificador_de_parte_valido(identificador):
            raise Indisponible(
                MotivoIndisponible.RECURSO_NO_CATALOGADO,
                f"«{identificador}» no tiene forma de identificador de parte",
            )
        parte = self._partes.get(identificador)
        if parte is None:
            raise Indisponible(
                MotivoIndisponible.RECURSO_NO_CATALOGADO,
                f"la parte «{identificador}» no está en el catálogo de partes",
            )
        return parte

    def partes_de(self, clave: str) -> tuple[Parte, ...]:
        self.obra(clave)  # valida la clave y que la obra exista
        return tuple(
            sorted(
                (p for p in self._partes.values() if p.obra == clave),
                key=lambda p: (p.pagina_impresa_inicial, p.identificador),
            )
        )

    # ── resolutor · página impresa → parte → página interna ─────────────────

    def localizar(
        self, clave: str, pagina_impresa: int, pagina_hasta: int | None = None
    ) -> Localizacion:
        """Lleva una página impresa a su parte y a su hoja dentro del archivo.

        Dos cálculos distintos y ninguno supuesto:

        - **dentro de la parte**, la hoja es `impresa − inicial de la parte + 1`.
          Aquí impresa e interna **nunca** coinciden salvo que la parte empiece
          en la página 1 de la obra, y ése es el caso raro.
        - **dentro del PDF completo**, la hoja es `impresa + desfase`, y sólo
          si el desfase de esa obra está medido. `PIS` no lo está —y tampoco
          tiene PDF completo—, por eso
          devuelve `None` en vez de un número plausible.
        """
        self.obra(clave)
        if pagina_impresa < 1:
            raise Indisponible(
                MotivoIndisponible.PAGINA_SIN_MAPEO,
                f"la numeración empieza en 1 y llegó {pagina_impresa}",
            )

        partes = self.partes_de(clave)
        if not partes:
            # Distinto de que la página no caiga en ninguna parte: aquí no hay
            # ninguna que consultar. Al equipo le falta catalogar; al operador,
            # nada. Confundirlos mandaría a medir un desfase que sí está medido.
            raise Indisponible(
                MotivoIndisponible.RECURSO_NO_CATALOGADO,
                f"«{clave}» no tiene ninguna parte catalogada",
            )

        for parte in partes:
            if parte.contiene(pagina_impresa):
                return Localizacion(
                    obra=clave,
                    parte=parte.identificador,
                    pagina_impresa=pagina_impresa,
                    pagina_interna_en_parte=(pagina_impresa - parte.pagina_impresa_inicial + 1),
                    pagina_interna_en_obra=self._pagina_en_obra(clave, pagina_impresa),
                    pagina_impresa_hasta=pagina_hasta,
                )

        raise Indisponible(
            MotivoIndisponible.PAGINA_SIN_MAPEO,
            f"ninguna parte catalogada de «{clave}» contiene la página impresa {pagina_impresa}",
        )

    def desfase_medido(self, clave: str) -> bool:
        """Si el desfase de paginación de esa obra está medido.

        Existe para que quien audite no tenga que leer el mapa interno ni
        inferirlo de una localización que puede fallar por otra causa. `PIS`
        responde `False` y es el dato, no un fallo.
        """
        return self._desfases.get(clave) is not None

    def _pagina_en_obra(self, clave: str, pagina_impresa: int) -> int | None:
        """La hoja del PDF completo, o `None` si el desfase no está medido."""
        desfase = self._desfases.get(clave)
        if desfase is None:
            return None
        interna = pagina_impresa + desfase
        return interna if interna >= 1 else None

    # ── permisos y disponibilidad ───────────────────────────────────────────

    def disponibilidad(self, clave: str, canal: Canal) -> Disponibilidad:
        """Permiso, catálogo y presencia del archivo, resueltos juntos."""
        obra = self.obra(clave)
        permiso = obra.permiso_de(canal)

        if canal is Canal.FRAGMENTO:
            # Un fragmento no tiene archivo propio en `_obras-md/`: su texto
            # está versionado en `fragmentos/`. Catalogado y presente son lo
            # mismo aquí, y lo decide que la obra tenga fragmentos leídos.
            hay = any(f.fragmento.procedencia.obra == clave for f in self._fragmentos.values())
            return Disponibilidad(canal, permiso, catalogado=hay, archivo_presente=hay)

        partes = self.partes_de(clave)
        if canal is Canal.PDF_COMPLETO:
            # 🐛 **Corregido en la revisión de 5A.** La primera versión componía
            # el nombre como `{clave}.pdf`. Era una invención: los ejemplares se
            # llaman `[Purcell,Varberg,Rigdon]Calculo.pdf` y cosas así, y
            # `FUENTES.md` avisa además de que el de `SPI` conviene renombrarlo.
            # Un nombre inventado hacía que el canal dijera «no está el archivo»
            # cuando la verdad es «nadie ha catalogado cuál es». Y `catalogado`
            # quedaba fijo en `False`, de modo que el PDF completo **no habría
            # podido servirse nunca**, ni autorizado ni presente.
            ruta = self.ruta_del_pdf_completo(clave)
            return Disponibilidad(
                canal,
                permiso,
                catalogado=bool(self._pdf_completo.get(clave)),
                archivo_presente=ruta is not None,
            )

        catalogado = any(
            p.archivo_markdown if canal is Canal.MARKDOWN_CONTINUO else p.archivo_pdf
            for p in partes
        )
        presente = any(self.ruta_de_parte(p, canal) is not None for p in partes)
        return Disponibilidad(canal, permiso, catalogado=catalogado, archivo_presente=presente)

    def ruta_del_pdf_completo(self, clave: str) -> Path | None:
        """El PDF completo de una obra, o `None` si no lo hay catalogado o presente.

        Pasa por la misma lista blanca de nombres y la misma comprobación de
        contención que `ruta_de_parte`: un catálogo editado a mano no puede
        sacar una ruta del directorio de obras.
        """
        nombre = self._pdf_completo.get(clave, "")
        if not nombre or not nombre_de_archivo_admisible(nombre):
            return None
        if not clave_de_obra_valida(clave):
            return None
        base = (self._raiz / "_obras").resolve()
        ruta = (base / nombre).resolve()
        if not ruta.is_file() or base not in ruta.parents:
            return None
        return ruta

    def ruta_de_parte(self, parte: Parte, canal: Canal) -> Path | None:
        """La ruta interna del archivo de una parte, o `None` si no la hay.

        **Uno de los dos únicos sitios que componen una ruta de obra**; el otro
        es `ruta_del_pdf_completo`, y hace las mismas tres comprobaciones. Son
        dos y no uno porque el PDF completo no cuelga de ninguna parte: vive en
        la raíz del directorio de obras.

        Vuelve a validar el nombre aunque `Parte.validar()` ya lo hiciera: un
        catálogo cargado sin validar, una prueba que construya un `Parte` a mano
        o un `PARTES.md` editado a mano no pueden abrir un archivo de fuera.
        """
        nombre = parte.archivo_markdown if canal is Canal.MARKDOWN_CONTINUO else parte.archivo_pdf
        if not nombre or not nombre_de_archivo_admisible(nombre):
            return None
        if not clave_de_obra_valida(parte.obra):
            return None

        carpeta = "_obras-md" if canal is Canal.MARKDOWN_CONTINUO else "_obras"
        base = (self._raiz / carpeta / parte.obra).resolve()
        ruta = (base / nombre).resolve()

        # Cinturón y tirantes. La lista blanca del nombre ya impide `..`, pero
        # un enlace simbólico o una unión de Windows **dentro** del directorio
        # de la obra puede apuntar fuera, y eso el nombre no lo dice. `resolve()`
        # los sigue; esta comprobación mira dónde acabaron.
        if not ruta.is_file() or base not in ruta.parents:
            return None
        return ruta

    # ── fragmentos ──────────────────────────────────────────────────────────

    def fragmentos(self) -> tuple[FragmentoLeido, ...]:
        return tuple(self._fragmentos[i] for i in sorted(self._fragmentos))

    def titulo_de_fragmento(self, identificador: str) -> str:
        """Un rótulo legible del fragmento, o su identificador si no se conoce.

        Lo usa el contrato del turno para que «Material del curso» diga
        *«López Erazo, páginas 146–173»* y no *«F-252»*. **No inventa nada**:
        los archivos del corpus no declaran título, así que se compone con obra
        y página, que es como se cita un pasaje en cualquier trabajo.

        No levanta. Un fragmento desconocido devuelve su propio identificador:
        el turno no puede romperse por un rótulo.
        """
        leido = self._fragmentos.get(identificador)
        if leido is None:
            return identificador
        obra = self._obras.get(leido.fragmento.procedencia.obra)
        nombre = (obra.autoria if obra else "") or leido.fragmento.procedencia.obra
        procedencia = leido.fragmento.procedencia
        if procedencia.exacta:
            return f"{nombre}, página {procedencia.pagina}"
        return f"{nombre}, páginas {procedencia.pagina}–{procedencia.pagina_hasta}"

    def ficha_de_fragmento(self, identificador: str) -> FichaDeFragmento:
        """El fragmento, su obra y dónde está. `Indisponible` si no existe.

        ⚠️ **No aplica el permiso.** Devolver la ficha y decidir si su texto
        puede mostrarse son dos cosas, y el borde HTTP hace la segunda. Mezclarlas
        aquí impediría lo que `FUENTES.md` sí autoriza: enseñar los metadatos
        bibliográficos y la procedencia de una obra que todavía no se publica.
        """
        if not identificador_de_fragmento_valido(identificador):
            raise Indisponible(
                MotivoIndisponible.FRAGMENTO_INEXISTENTE,
                f"«{identificador}» no tiene forma de identificador de fragmento",
            )
        leido = self._fragmentos.get(identificador)
        if leido is None:
            # `F-179` y `F-180` llegan aquí: forma válida, dentro del rango, y
            # no existen. El rango nunca se materializa.
            raise Indisponible(
                MotivoIndisponible.FRAGMENTO_INEXISTENTE,
                f"no hay ningún fragmento «{identificador}»",
            )

        procedencia = leido.fragmento.procedencia
        obra = self.obra(procedencia.obra)
        try:
            localizacion = self.localizar(
                procedencia.obra, procedencia.pagina, procedencia.pagina_hasta
            )
            motivo = None
        except Indisponible as exc:
            localizacion, motivo = None, exc.motivo
        return FichaDeFragmento(leido, obra, localizacion, motivo)


# ── lectura de los archivos ─────────────────────────────────────────────────


def _leer_obras(ruta: Path, fallos: list[str]) -> tuple[dict[str, Obra], set[str]]:
    """Las obras de `FUENTES.md`, con su permiso por canal."""
    if not ruta.is_file():
        fallos.append(f"no existe {ruta}")
        return {}, set()

    texto = ruta.read_text(encoding="utf-8")
    permisos = _leer_tabla_de_permisos(texto)
    fichas = _fichas_por_clave(texto)

    obras: dict[str, Obra] = {}
    sin_fila: set[str] = set()
    for clave, (nombre, cuerpo) in fichas.items():
        campos = dict(_FILA_DE_CAMPO.findall(cuerpo))
        titulo = campos.get("Obra", "").strip() or nombre or clave
        if clave not in permisos:
            sin_fila.add(clave)
            # Se cuenta como fallo del catálogo y no sólo como aviso: si la
            # tabla de publicación cambia de forma, TODAS las obras caen aquí y
            # la biblioteca se apaga entera. Es lo correcto —fallo seguro— pero
            # el operador tiene que verlo en `/api/salud`, no descubrirlo
            # porque la pantalla está vacía.
            fallos.append(
                f"la obra «{clave}» no tiene fila en la tabla de publicación: "
                f"queda bloqueada en todos sus canales"
            )
        disponibilidad = {
            canal: Disponibilidad(canal, permisos.get(clave, {}).get(canal, Permiso.BLOQUEADO))
            for canal in Canal
        }
        obra = Obra(
            clave=clave,
            titulo=titulo,
            autoria=nombre,
            paginas_del_archivo=_paginas_de(campos.get("Archivo", "")),
            # `FUENTES.md` marca todas sus referencias externas «por verificar»,
            # y §3 de la puerta de publicación exige comprobar edición,
            # estabilidad y procedencia antes de enlazarlas. Mientras eso no
            # ocurra no viaja ninguna: publicar un enlace sin verificar sería
            # afirmar algo sobre un ejemplar ajeno.
            referencia_externa="",
            referencia_verificada=False,
            disponibilidad=disponibilidad,
        )
        fallos.extend(obra.validar())
        obras[clave] = obra
    return obras, sin_fila


def _fichas_por_clave(texto: str) -> dict[str, tuple[str, str]]:
    """Nombre corto y cuerpo de cada ficha `### \\`XXX\\` · Nombre`.

    Las obras consultadas llevan `####` a propósito —`FUENTES.md` lo explica—
    y por eso esta expresión sólo recoge `###`: `SWO` no entra al catálogo y
    ninguna ruta puede servirla.
    """
    fichas: dict[str, tuple[str, str]] = {}
    for m in _FICHA_DE_OBRA.finditer(texto):
        siguiente = _ENCABEZADO.search(texto, m.end())
        fin = siguiente.start() if siguiente else len(texto)
        fichas[m.group(1)] = ((m.group(2) or "").strip(), texto[m.end() : fin])
    return fichas


def _leer_tabla_de_permisos(texto: str) -> dict[str, dict[Canal, Permiso]]:
    """La tabla §Estado conservador, traducida a permisos por canal.

    El PDF dividido **no tiene columna** y hereda el permiso del PDF completo.
    Está escrito aquí y no en el documento porque es una consecuencia del
    razonamiento —publicar todas las partes es publicar la obra—, no una
    decisión nueva que el equipo tenga que tomar.
    """
    tabla: dict[str, dict[Canal, Permiso]] = {}
    for clave, pdf, markdown, fragmentos, _referencia in _FILA_DE_PERMISO.findall(texto):
        completo = _permiso_de_celda(pdf)
        tabla[clave] = {
            Canal.PDF_COMPLETO: completo,
            Canal.PDF_DIVIDIDO: completo,
            Canal.MARKDOWN_CONTINUO: _permiso_de_celda(markdown),
            Canal.FRAGMENTO: _permiso_de_celda(fragmentos),
        }
    return tabla


def _paginas_de(celda: str) -> int | None:
    """El número de páginas que declara la fila `**Archivo**`, si lo declara."""
    m = _PAGINAS.search(celda)
    if not m:
        return None
    try:
        return int(re.sub(r"[\s  ]", "", m.group(1)))
    except ValueError:  # pragma: no cover — la expresión ya garantiza dígitos
        return None


def _leer_partes(
    ruta: Path, claves: object, fallos: list[str]
) -> tuple[dict[str, Parte], dict[str, int | None], dict[str, str]]:
    """Las tres tablas de `PARTES.md`. Cada una la lee su propia función.

    Un desfase «sin medir» se guarda como `None` y **no como cero**. Es la
    diferencia entre «la hoja es la página» y «nadie lo ha comprobado», y es
    justo la que el encargo prohíbe borrar.
    """
    conocidas = set(claves)
    if not ruta.is_file():
        fallos.append(f"no existe {ruta}: sin partes catalogadas ni desfases medidos")
        return {}, {}, {}

    texto = ruta.read_text(encoding="utf-8")
    return (
        _leer_tabla_de_partes(texto, conocidas, fallos),
        _leer_tabla_de_desfases(texto, conocidas, fallos),
        _leer_tabla_de_pdf_completo(texto, conocidas, fallos),
    )


def _leer_tabla_de_desfases(
    texto: str, conocidas: set[str], fallos: list[str]
) -> dict[str, int | None]:
    desfases: dict[str, int | None] = {}
    for clave, valor, _evidencia in _FILA_DE_DESFASE.findall(
        _seccion(texto, "Desfase de paginación")
    ):
        if clave not in conocidas:
            fallos.append(
                f"PARTES.md declara desfase de «{clave}», que no es una obra del catálogo"
            )
            continue
        limpio = valor.strip().lower()
        if limpio in {"sin medir", "sin_medir", "—", "-", ""}:
            desfases[clave] = None
            continue
        try:
            desfases[clave] = int(limpio.replace("+", ""))
        except ValueError:
            fallos.append(f"PARTES.md: desfase no numérico de «{clave}»: {valor.strip()!r}")
            desfases[clave] = None
    return desfases


def _leer_tabla_de_pdf_completo(
    texto: str, conocidas: set[str], fallos: list[str]
) -> dict[str, str]:
    pdf_completo: dict[str, str] = {}
    for clave, valor in _FILA_DE_PDF_COMPLETO.findall(_seccion(texto, "Archivo del PDF completo")):
        if clave not in conocidas:
            continue
        nombre = _celda_de_archivo(valor)
        if nombre and not nombre_de_archivo_admisible(nombre):
            fallos.append(f"PARTES.md: nombre de PDF completo no admisible de «{clave}»")
            continue
        pdf_completo[clave] = nombre
    return pdf_completo


def _leer_tabla_de_partes(texto: str, conocidas: set[str], fallos: list[str]) -> dict[str, Parte]:
    partes: dict[str, Parte] = {}
    for identificador, obra, titulo, inicial, final, markdown, pdf in _FILA_DE_PARTE.findall(
        _seccion(texto, "Partes por obra")
    ):
        if obra not in conocidas:
            fallos.append(f"PARTES.md: la parte «{identificador}» cita una obra desconocida")
            continue
        parte = Parte(
            identificador=identificador,
            obra=obra,
            titulo=titulo.strip(),
            pagina_impresa_inicial=int(inicial),
            pagina_impresa_final=int(final),
            archivo_markdown=_celda_de_archivo(markdown),
            archivo_pdf=_celda_de_archivo(pdf),
        )
        problemas = parte.validar()
        if problemas:
            fallos.extend(f"PARTES.md: {p}" for p in problemas)
            continue
        if parte.identificador in partes:
            fallos.append(f"PARTES.md: parte repetida «{parte.identificador}»")
            continue
        partes[parte.identificador] = parte
    return partes


def _seccion(texto: str, titulo: str) -> str:
    """El trozo del documento que va desde un encabezado hasta el siguiente.

    Sin esto, las dos tablas de dos columnas de `PARTES.md` —desfase y PDF
    completo— se leerían la una a la otra: sus filas tienen la misma forma.
    """
    inicio = texto.find(titulo)
    if inicio < 0:
        return ""
    siguiente = _ENCABEZADO.search(texto, inicio + len(titulo))
    return texto[inicio : siguiente.start() if siguiente else len(texto)]


def _celda_de_archivo(celda: str) -> str:
    """El nombre de archivo de una celda, sin acentos graves ni guiones vacíos."""
    limpio = celda.strip().strip("`").strip()
    return "" if limpio in {"—", "-", "n/a"} else limpio


def _leer_fragmentos(
    directorio: Path, claves: object, fallos: list[str]
) -> dict[str, FragmentoLeido]:
    """Los fragmentos del disco, indexados por identificador."""
    conocidas = set(claves)
    lectura = leer_todos(directorio)
    fallos.extend(lectura.fallos)

    indice: dict[str, FragmentoLeido] = {}
    for leido in lectura.leidos:
        identificador = leido.fragmento.identificador
        if identificador in indice:
            fallos.append(f"identificador repetido «{identificador}» en {leido.archivo}")
            continue
        if conocidas and leido.fragmento.procedencia.obra not in conocidas:
            fallos.append(
                f"{leido.archivo}: la obra «{leido.fragmento.procedencia.obra}» "
                f"no está en FUENTES.md"
            )
            continue
        indice[identificador] = leido
    return indice
