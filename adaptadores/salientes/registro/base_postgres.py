from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from adaptadores.salientes.conexion import conectar
from dominio.modelo.identidad import CategoriaDeEdad, categoria_de_edad
from dominio.puertos.almacen import (
    AlcanceIncorrecto,
    AlmacenNoConfigurado,
    AlmacenNoDisponible,
    DatoNoAdmitido,
    ErrorDeAlmacen,
    EscrituraRechazada,
    PerfilSinEdad,
    ReferenciaDesconocida,
    VersionNoVigente,
)
from dominio.puertos.gobierno import SupresionEnCurso

if TYPE_CHECKING:
    from collections.abc import Iterator

_INTEGRIDAD_REFERENCIAL = "23503"
_RECHAZOS = {
    "23505": "ya existe un registro con esa clave",
    "23514": "un valor no cumple una restricción del esquema",
    "23502": "falta un valor obligatorio",
    "22001": "un valor excede la longitud admitida",
}


_SIN_ESQUEMA = {"42P01", "42703"}


def _psycopg() -> Any:
    import psycopg

    return psycopg

def _traducir(error: Any) -> ErrorDeAlmacen:
    codigo = getattr(error, "sqlstate", None) or ""
    if not codigo and isinstance(error, _psycopg().DataError):

        return DatoNoAdmitido("el valor no es representable en la base")
    if codigo == _INTEGRIDAD_REFERENCIAL:
        return ReferenciaDesconocida(
            f"la escritura nombra algo que no existe (SQLSTATE {codigo})"
        )
    if codigo in _RECHAZOS:
        return EscrituraRechazada(f"{_RECHAZOS[codigo]} (SQLSTATE {codigo})")
    if codigo in _SIN_ESQUEMA:
        return AlmacenNoConfigurado(
            f"la base no tiene el esquema de la migración 11 (SQLSTATE {codigo})"
        )
    detalle = f" (SQLSTATE {codigo})" if codigo else ""
    return AlmacenNoDisponible(f"la base no pudo atender la operación{detalle}")

@contextmanager
def traducir_fallo() -> Iterator[None]:
    psycopg = _psycopg()
    try:
        yield
    except ErrorDeAlmacen:

        raise
    except psycopg.Error as error:
        raise _traducir(error) from None

class RepositorioPostgres:

    def __init__(self, cadena_de_conexion: str) -> None:
        self._cadena = cadena_de_conexion

    @contextmanager
    def _conexion(self) -> Iterator[Any]:
        if not self._cadena:
            raise AlmacenNoConfigurado(
                "este repositorio no recibió cadena de conexión: la composición "
                "no lo cableó a ninguna base"
            )
        psycopg = _psycopg()
        try:
            with conectar(self._cadena) as cnx:
                yield cnx
        except ErrorDeAlmacen:

            raise
        except psycopg.Error as error:
            raise _traducir(error) from None

    @contextmanager
    def _escritura(self) -> Iterator[Any]:
        with self._conexion() as cnx, cnx.transaction():
            yield cnx

SQL_VERSION_REQUERIDA = "SELECT didaxia_version_requerida(%s)"


_TABLAS_DE_EVENTOS = frozenset({"consentimiento_evento", "asentimiento_evento"})


def exigir_persona(cur: Any, sujeto_google: str) -> int | None:
    cur.execute(
        "SELECT edad_declarada FROM persona WHERE sujeto_google = %s FOR UPDATE",
        (sujeto_google,),
    )
    fila = cur.fetchone()
    if fila is None:
        raise ReferenciaDesconocida("esa persona no está registrada")
    return fila[0]

FILTRO_PERSONA_SIN_SUPRESION_SQL = """NOT EXISTS (
    SELECT 1 FROM solicitud_supresion s
    WHERE s.sujeto_google = p.sujeto_google AND s.estado = 'solicitada')"""

def exigir_sin_supresion(cur: Any, sujeto_google: str) -> None:
    cur.execute(
        "SELECT 1 FROM solicitud_supresion "
        "WHERE sujeto_google = %s AND estado = 'solicitada' "
        "LIMIT 1",
        (sujeto_google,),
    )
    if cur.fetchone() is not None:
        raise SupresionEnCurso(
            "hay un trámite de supresión en curso: mientras dure no se registra "
            "ningún tratamiento nuevo"
        )

def exigir_persona_activa(cur: Any, sujeto_google: str) -> int | None:
    edad = exigir_persona(cur, sujeto_google)
    exigir_sin_supresion(cur, sujeto_google)
    return edad

def bloquear_y_exigir_sin_supresion(cur: Any, sujeto_google: str) -> None:
    cur.execute(
        "SELECT 1 FROM persona WHERE sujeto_google = %s FOR UPDATE",
        (sujeto_google,),
    )
    if cur.fetchone() is None:

        exigir_sin_supresion(cur, sujeto_google)
        return
    exigir_sin_supresion(cur, sujeto_google)

def exigir_categoria_de_edad(edad: int | None) -> CategoriaDeEdad:
    categoria = categoria_de_edad(edad)
    if categoria is CategoriaDeEdad.NO_DECLARADA:

        raise PerfilSinEdad(
            "no se registra un acto de consentimiento sin edad declarada"
        )
    return categoria

def version_requerida_de(cur: Any, alcance: str) -> str | None:
    cur.execute(SQL_VERSION_REQUERIDA, (alcance,))
    fila = cur.fetchone()
    return fila[0] if fila else None

def exigir_version_requerida(cur: Any, codigo: str, alcance: str) -> None:
    cur.execute(
        """
        SELECT alcance,
               vigente_desde <= now() AS ya_empezo,
               (vigente_hasta IS NULL OR now() < vigente_hasta) AS no_vencio
          FROM consentimiento_version
         WHERE codigo = %s
         FOR SHARE
        """,
        (codigo,),
    )
    fila = cur.fetchone()
    if fila is None:
        raise ReferenciaDesconocida("esa versión de consentimiento no existe")
    alcance_real, ya_empezo, no_vencio = fila
    if alcance_real != alcance:
        raise AlcanceIncorrecto(
            f"esa versión es de alcance {alcance_real!r} y aquí hace falta {alcance!r}"
        )
    if not ya_empezo:
        raise VersionNoVigente("esa versión todavía no está vigente")
    if not no_vencio:
        raise VersionNoVigente("esa versión ya está vencida")

    requerida = version_requerida_de(cur, alcance)
    if requerida is None:
        raise VersionNoVigente(
            f"no hay ninguna versión requerida del alcance {alcance!r}: la última "
            "que comenzó ya venció"
        )
    if requerida != codigo:

        raise VersionNoVigente(
            f"esa versión fue desplazada por una posterior del alcance {alcance!r}"
        )

def exigir_tabla_de_eventos(tabla: str) -> str:
    if tabla not in _TABLAS_DE_EVENTOS:
        raise EscrituraRechazada(f"{tabla!r} no es una tabla de eventos de esta frontera")
    return tabla

def ultimo_acto(cur: Any, tabla: str, sujeto: str, columnas: tuple[str, ...]) -> tuple | None:
    proyeccion = ", ".join(columnas)
    cur.execute(
        f"""
        SELECT {proyeccion} FROM {exigir_tabla_de_eventos(tabla)}
         WHERE sujeto_google = %s
         ORDER BY momento DESC, id DESC
         LIMIT 1
        """,
        (sujeto,),
    )
    return cur.fetchone()

def version_de_la_concesion_de(cur: Any, tabla: str, sujeto: str) -> str | None:
    cur.execute(
        f"""
        SELECT version FROM {exigir_tabla_de_eventos(tabla)}
         WHERE sujeto_google = %s AND estado = 'otorgado'
         ORDER BY momento DESC, id DESC
         LIMIT 1
        """,
        (sujeto,),
    )
    fila = cur.fetchone()
    return fila[0] if fila else None

_DEVUELVE_DE = {
    "consentimiento_evento": ("id", "momento", "categoria_edad"),
    "asentimiento_evento": ("id", "momento"),
}


def insertar_acto(
    cur: Any,
    tabla: str,
    *,
    sujeto: str,
    version: str,
    estado: str,
    comprobante: str,
) -> tuple:

    columnas = ", ".join(_DEVUELVE_DE[exigir_tabla_de_eventos(tabla)])
    cur.execute(
        f"""
        INSERT INTO {tabla}
            (sujeto_google, version, estado, comprobante)
        VALUES (%s, %s, %s, %s)
        RETURNING {columnas}
        """,
        (sujeto, version, estado, comprobante),
    )
    return cur.fetchone()

def huella_de_version(cur: Any, codigo: str) -> str:
    cur.execute(
        "SELECT huella_contenido FROM consentimiento_version WHERE codigo = %s",
        (codigo,),
    )
    fila = cur.fetchone()
    if fila is None:
        raise ReferenciaDesconocida("esa versión de consentimiento no existe")
    return fila[0]

def exigir_version_de_la_concesion(cur: Any, tabla: str, sujeto: str, codigo: str) -> None:
    otorgada = version_de_la_concesion_de(cur, tabla, sujeto)
    if otorgada is None:
        raise EscrituraRechazada("no hay ninguna concesión otorgada que revocar")
    if otorgada != codigo:
        raise EscrituraRechazada(
            "una revocación sólo retira la concesión efectivamente otorgada"
        )
