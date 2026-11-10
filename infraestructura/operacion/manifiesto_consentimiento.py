"""
manifiesto_consentimiento.py — Qué se va a publicar, leído de fuera del repositorio
=====================================================================================

Por qué el texto real NO vive en este árbol · `§8.8`
---------------------------------------------------------
Tres motivos, y ninguno es de comodidad:

1. **Un texto en el código es un texto que alguien edita.** El documento de
   consentimiento es la prueba de qué se autorizó; que viva en un archivo `.py`
   lo pone al alcance de un `sed` distraído y de un conflicto de fusión.
2. Los textos institucionales incluyen datos de contacto y se administran fuera de Git.
3. **No está aprobado.** `infraestructura/demostracion/semilla.py` lo dice del
   suyo y sigue valiendo: escribir aquí un texto que se pareciera al definitivo
   haría que a la siguiente sesión alguien lo citara como si lo fuera.

Así que el contenido llega en archivos externos y este módulo sólo sabe leer un
**manifiesto** que los enumera y valida.

Qué valida, y por qué falla cerrado
---------------------------------------
Todo lo que puede comprobarse sin saber qué dice el documento: que el JSON tiene
la forma esperada, que los alcances son del enumerado, que las finalidades son
del catálogo cerrado, que las fechas son fechas con zona, que cada archivo
existe **dentro de la carpeta de textos** y que el cuerpo no viene vacío.

Lo que **no** valida es si el texto es verdadero, completo o suficiente. Eso lo
decide una persona, y por eso la herramienta que usa este módulo va en
`--dry-run` por defecto: lo que este archivo puede afirmar es que el paquete
está bien formado, no que sea correcto publicarlo.

⚠️ **La ruta de cada texto se resuelve DENTRO de la carpeta declarada**, y se
comprueba con `commonpath` después de `resolve()`. Un manifiesto es un archivo
de entrada; sin esa comprobación, `"archivo": "../../../etc/passwd"` habría
publicado como documento de consentimiento lo que hubiera ahí. Es la misma
disciplina que `infraestructura/respaldo/custodia.py` aplica a los miembros de
un `tar`, y por el mismo motivo: el formato lleva nombres dentro.

Forma del manifiesto
------------------------
```json
{
  "formato": 1,
  "versiones": [
    {
      "codigo": "titular-2026-09",
      "alcance": "titular",
      "archivo": "titular-2026-09.md",
      "vigente_desde": "2026-09-15T00:00:00-05:00",
      "vigente_hasta": null,
      "finalidades": ["autenticacion_y_seguridad", "..."]
    }
  ]
}
```


"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from dominio.modelo.consentimiento import Alcance, ConsentimientoInvalido, Finalidad
from dominio.modelo.instantanea_consentimiento import (
    InstantaneaDeVersion,
    PublicacionDeVersion,
)

#: Versión del formato. Se comprueba: un manifiesto de otro formato no se
#: interpreta a la fuerza, por la misma razón que el manifiesto de custodia.
FORMATO = 1


class ManifiestoInvalido(RuntimeError):
    """El paquete no está bien formado y no se publica nada.

    Los mensajes nombran **qué** falta y en qué entrada, nunca el contenido del
    documento: un fallo de esta herramienta acaba en una consola y en un informe.
    """


def _texto(entrada: dict, campo: str, posicion: int) -> str:
    valor = entrada.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise ManifiestoInvalido(f"versión #{posicion}: falta «{campo}» o está vacío")
    return valor.strip()


def _momento(entrada: dict, campo: str, posicion: int, *, obligatorio: bool) -> datetime | None:
    crudo = entrada.get(campo)
    if crudo is None:
        if obligatorio:
            raise ManifiestoInvalido(f"versión #{posicion}: falta «{campo}»")
        return None
    if not isinstance(crudo, str):
        raise ManifiestoInvalido(f"versión #{posicion}: «{campo}» tiene que ser texto ISO-8601")
    try:
        momento = datetime.fromisoformat(crudo)
    except ValueError as exc:
        raise ManifiestoInvalido(
            f"versión #{posicion}: «{campo}» no es una fecha ISO-8601"
        ) from exc
    if momento.tzinfo is None:
        # Sin zona, «desde cuándo rige» depende de dónde se ejecute la
        # herramienta. Una vigencia que cambia con el equipo no es una vigencia.
        raise ManifiestoInvalido(
            f"versión #{posicion}: «{campo}» tiene que declarar zona horaria"
        )
    return momento


def _ruta_dentro(carpeta: Path, nombre: str, posicion: int) -> Path:
    """La ruta del texto, comprobando que no se sale de la carpeta declarada.

    ⚠️ Es la barrera de recorrido de rutas. Se resuelve primero y se compara
    con `commonpath` —no con `startswith`, que aceptaría una carpeta hermana
    cuyo nombre empiece igual—, exactamente como hace la custodia.
    """
    raiz = carpeta.resolve()
    candidata = (raiz / nombre).resolve()
    try:
        dentro = os.path.commonpath([str(candidata), str(raiz)]) == str(raiz)
    except ValueError:  # unidades distintas en Windows
        dentro = False
    if not dentro:
        raise ManifiestoInvalido(
            f"versión #{posicion}: «archivo» apunta fuera de la carpeta de textos"
        )
    if not candidata.is_file():
        raise ManifiestoInvalido(
            f"versión #{posicion}: no existe el archivo declarado en «archivo»"
        )
    return candidata


def _alcance_de(entrada: dict, posicion: int) -> Alcance:
    try:
        return Alcance(_texto(entrada, "alcance", posicion))
    except ValueError as exc:
        raise ManifiestoInvalido(
            f"versión #{posicion}: «alcance» no es uno de "
            f"{', '.join(a.value for a in Alcance)}"
        ) from exc


def _finalidades_de(entrada: dict, posicion: int) -> frozenset[Finalidad]:
    crudas = entrada.get("finalidades")
    if not isinstance(crudas, list) or not crudas:
        raise ManifiestoInvalido(f"versión #{posicion}: «finalidades» no puede faltar")
    try:
        return frozenset(Finalidad(f) for f in crudas)
    except ValueError as exc:
        raise ManifiestoInvalido(
            f"versión #{posicion}: hay una finalidad que no es del catálogo cerrado"
        ) from exc


def _cuerpo_de(entrada: dict, textos: Path, posicion: int) -> str:
    """El documento, leído en binario y decodificado explícitamente.

    `read_text()` usa la codificación del sistema, y en Windows eso no es
    UTF-8. Un documento leído con la codificación equivocada produce otra
    huella, y entonces lo publicado no sería lo aprobado.
    """
    ruta = _ruta_dentro(Path(textos), _texto(entrada, "archivo", posicion), posicion)
    try:
        return ruta.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ManifiestoInvalido(
            f"versión #{posicion}: el archivo no se pudo leer como UTF-8"
        ) from exc


def _publicacion_de(entrada: dict, textos: Path, posicion: int) -> PublicacionDeVersion:
    """Una entrada del manifiesto, ya validada y con su cuerpo leído."""
    if not isinstance(entrada, dict):
        raise ManifiestoInvalido(f"versión #{posicion}: cada versión es un objeto")
    try:
        return PublicacionDeVersion(
            instantanea=InstantaneaDeVersion(
                codigo=_texto(entrada, "codigo", posicion),
                alcance=_alcance_de(entrada, posicion),
                cuerpo=_cuerpo_de(entrada, textos, posicion),
            ),
            finalidades=_finalidades_de(entrada, posicion),
            vigente_desde=_momento(entrada, "vigente_desde", posicion, obligatorio=True),
            vigente_hasta=_momento(entrada, "vigente_hasta", posicion, obligatorio=False),
        )
    except ConsentimientoInvalido as exc:
        # El dominio ya sabe decir qué falla —finalidades obligatorias, cuerpo
        # vacío, vigencia al revés—. Se traduce el tipo para que quien ejecuta
        # vea un solo error de manifiesto, y se conserva el mensaje, que es el
        # útil.
        raise ManifiestoInvalido(f"versión #{posicion}: {exc}") from exc


def _entradas_del(manifiesto: Path) -> list:
    """Las entradas del JSON, tras comprobar la forma del documento entero."""
    if not manifiesto.is_file():
        raise ManifiestoInvalido("no existe el manifiesto")
    try:
        datos = json.loads(manifiesto.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifiestoInvalido("el manifiesto no es JSON válido") from exc
    if not isinstance(datos, dict):
        raise ManifiestoInvalido("el manifiesto tiene que ser un objeto JSON")
    if datos.get("formato") != FORMATO:
        raise ManifiestoInvalido(
            f"formato de manifiesto desconocido; esta herramienta lee el {FORMATO}"
        )
    crudas = datos.get("versiones")
    if not isinstance(crudas, list) or not crudas:
        raise ManifiestoInvalido("el manifiesto no declara ninguna versión")
    return crudas


def leer(manifiesto: Path, textos: Path) -> tuple[PublicacionDeVersion, ...]:
    """Las publicaciones que el manifiesto describe, ya validadas.

    No escribe nada y no habla con ninguna base: se puede llamar en `--dry-run`
    y obtener exactamente lo mismo que se publicaría, incluidas las huellas.
    """
    if not Path(textos).is_dir():
        raise ManifiestoInvalido("la carpeta de textos no existe o no es un directorio")

    publicaciones: list[PublicacionDeVersion] = []
    vistos: set[str] = set()
    for posicion, entrada in enumerate(_entradas_del(Path(manifiesto)), start=1):
        publicacion = _publicacion_de(entrada, Path(textos), posicion)
        if publicacion.codigo in vistos:
            # Dos entradas con el mismo código publicarían la segunda encima de
            # la primera o —peor— dependería del orden. Se detiene.
            raise ManifiestoInvalido(f"el código «{publicacion.codigo}» aparece dos veces")
        vistos.add(publicacion.codigo)
        publicaciones.append(publicacion)

    return tuple(publicaciones)
