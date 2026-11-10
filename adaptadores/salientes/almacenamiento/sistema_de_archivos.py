from __future__ import annotations

import contextlib
import os
import re
import secrets
import stat
import tempfile
from pathlib import Path

from dominio.puertos.almacenamiento_privado import (
    AlmacenamientoNoDisponible,
    DocumentoAusente,
    DocumentoPendienteDeConfirmacion,
)


VARIABLE_RUTA = "ALMACENAMIENTO_PRIVADO_RUTA"


PROVISIONALES = "provisionales"
CONFIRMADOS = "confirmados"


SUFIJO = ".bin"


PREFIJO = "c1-"


BYTES_DE_AZAR = 16


_REFERENCIA = re.compile(rf"^{re.escape(PREFIJO)}[0-9a-f]{{{BYTES_DE_AZAR * 2}}}$")


_ARCHIVO = re.compile(
    rf"^{re.escape(PREFIJO)}[0-9a-f]{{{BYTES_DE_AZAR * 2}}}{re.escape(SUFIJO)}$"
)


PREFIJO_TEMPORAL = ".parcial-"
SUFIJO_TEMPORAL = ".tmp"


MODO_DIRECTORIO = 0o700
MODO_ARCHIVO = 0o600


INTENTOS_DE_NOMBRE = 3


class ConfiguracionInvalida(ValueError):
    pass

def _ruta_contenida(candidata: Path, raiz_resuelta: str) -> bool:
    try:
        resuelta = os.path.realpath(candidata)
    except OSError:
        return False
    if resuelta == raiz_resuelta:
        return True
    try:
        return os.path.commonpath([resuelta, raiz_resuelta]) == raiz_resuelta
    except ValueError:

        return False

def _es_archivo_propio(ruta: Path, raiz_resuelta: str) -> bool:
    try:
        info = ruta.lstat()
    except OSError:
        return False
    if not stat.S_ISREG(info.st_mode):
        return False
    return _ruta_contenida(ruta, raiz_resuelta)

def _permisos(ruta: Path, modo: int) -> None:
    with contextlib.suppress(OSError):
        os.chmod(ruta, modo)

class AlmacenamientoEnSistemaDeArchivos:

    def __init__(self, raiz: Path | str) -> None:
        raiz = Path(raiz)
        if not raiz.is_absolute():
            raise ConfiguracionInvalida(
                "la raíz de la custodia privada tiene que ser una ruta absoluta"
            )
        if not raiz.is_dir():
            raise ConfiguracionInvalida(
                "la raíz de la custodia privada no existe o no es un directorio; "
                "no se crea sola"
            )
        self._raiz = raiz

        self._raiz_resuelta = os.path.realpath(raiz)
        self._provisionales = raiz / PROVISIONALES
        self._confirmados = raiz / CONFIRMADOS
        self._preparar()

    def _preparar(self) -> None:
        for directorio in (self._provisionales, self._confirmados):
            try:
                directorio.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise ConfiguracionInvalida(
                    "no se pudieron preparar los directorios de la custodia privada "
                    f"({exc.__class__.__name__})"
                ) from None
            _permisos(directorio, MODO_DIRECTORIO)
        try:
            descriptor, temporal = tempfile.mkstemp(
                dir=self._provisionales, prefix=PREFIJO_TEMPORAL, suffix=SUFIJO_TEMPORAL
            )
        except OSError as exc:
            raise ConfiguracionInvalida(
                "la raíz de la custodia privada no admite escritura "
                f"({exc.__class__.__name__})"
            ) from None
        os.close(descriptor)
        os.unlink(temporal)

    def _ruta(self, referencia: str, directorio: Path) -> Path | None:
        if not isinstance(referencia, str) or not _REFERENCIA.match(referencia):
            return None
        ruta = directorio / f"{referencia}{SUFIJO}"
        if not _ruta_contenida(ruta, self._raiz_resuelta):
            return None
        return ruta

    def reservar(self, contenido: bytes, *, sujeto_google: str, intento: int) -> str:
        del sujeto_google, intento
        try:
            descriptor, temporal = tempfile.mkstemp(
                dir=self._provisionales, prefix=PREFIJO_TEMPORAL, suffix=SUFIJO_TEMPORAL
            )
        except OSError:
            raise AlmacenamientoNoDisponible(
                "la custodia privada no admite escribir la reserva"
            ) from None

        ruta_temporal = Path(temporal)
        try:
            with os.fdopen(descriptor, "wb") as archivo:
                archivo.write(contenido)
                archivo.flush()

                os.fsync(archivo.fileno())
            _permisos(ruta_temporal, MODO_ARCHIVO)
            referencia = self._reclamar(ruta_temporal)
        except OSError:
            self._descartar_temporal(ruta_temporal)
            raise AlmacenamientoNoDisponible(
                "no se pudo completar la reserva en la custodia privada"
            ) from None
        except BaseException:

            self._descartar_temporal(ruta_temporal)
            raise
        self._sincronizar_directorio(self._provisionales)
        return referencia

    def _reclamar(self, ruta_temporal: Path) -> str:
        ultimo: OSError | None = None
        for _ in range(INTENTOS_DE_NOMBRE):
            referencia = f"{PREFIJO}{secrets.token_hex(BYTES_DE_AZAR)}"
            destino = self._provisionales / f"{referencia}{SUFIJO}"
            try:
                os.link(ruta_temporal, destino)
            except FileExistsError as exc:

                ultimo = exc
                continue
            except OSError as exc:

                raise AlmacenamientoNoDisponible(
                    "la custodia privada no admite reclamar un nombre de forma "
                    "atómica; no se acepta la evidencia en vez de arriesgar un "
                    "reemplazo"
                ) from exc
            os.unlink(ruta_temporal)
            return referencia
        raise AlmacenamientoNoDisponible(
            "no se pudo reservar un nombre libre en la custodia privada"
        ) from ultimo

    def _descartar_temporal(self, ruta: Path) -> None:
        nombre = ruta.name
        if not (nombre.startswith(PREFIJO_TEMPORAL) and nombre.endswith(SUFIJO_TEMPORAL)):
            return
        if not _ruta_contenida(ruta, self._raiz_resuelta):
            return
        with contextlib.suppress(OSError):
            os.unlink(ruta)

    def _sincronizar_directorio(self, directorio: Path) -> None:
        try:
            descriptor = os.open(directorio, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(descriptor)
        except OSError:
            pass
        finally:
            os.close(descriptor)

    def confirmar(self, referencia: str) -> None:
        origen = self._ruta(referencia, self._provisionales)
        destino = self._ruta(referencia, self._confirmados)
        if origen is None or destino is None:
            raise DocumentoAusente(
                "no hay ninguna reserva en la custodia privada bajo esa referencia"
            )

        confirmado = _es_archivo_propio(destino, self._raiz_resuelta)
        provisional = _es_archivo_propio(origen, self._raiz_resuelta)
        if confirmado and not provisional:
            return
        if confirmado and provisional:
            raise AlmacenamientoNoDisponible(
                "la custodia privada tiene esa referencia a la vez como reserva y "
                "como evidencia confirmada: hace falta reconciliarla"
            )
        if not provisional:

            if _es_archivo_propio(destino, self._raiz_resuelta):
                return
            raise DocumentoAusente(
                "no hay ninguna reserva en la custodia privada bajo esa referencia"
            )

        try:
            os.rename(origen, destino)
        except FileNotFoundError:

            if _es_archivo_propio(destino, self._raiz_resuelta):
                return
            raise DocumentoAusente(
                "no hay ninguna reserva en la custodia privada bajo esa referencia"
            ) from None
        except OSError:
            if _es_archivo_propio(destino, self._raiz_resuelta):
                return
            raise AlmacenamientoNoDisponible(
                "no se pudo promover la reserva a evidencia confirmada"
            ) from None
        self._sincronizar_directorio(self._confirmados)

    def retirar(self, referencia: str) -> bool:
        ruta = self._ruta(referencia, self._provisionales)
        if ruta is None:
            return False
        if not _es_archivo_propio(ruta, self._raiz_resuelta):

            return False
        try:
            os.unlink(ruta)
        except FileNotFoundError:
            return False
        except OSError:
            raise AlmacenamientoNoDisponible(
                "no se pudo retirar la reserva de la custodia privada"
            ) from None
        return True

    def recuperar(self, referencia: str) -> bytes:
        confirmado = self._ruta(referencia, self._confirmados)
        provisional = self._ruta(referencia, self._provisionales)
        if confirmado is None or provisional is None:
            raise DocumentoAusente(
                "la custodia privada no tiene ningún archivo bajo esa referencia"
            )
        if _es_archivo_propio(confirmado, self._raiz_resuelta):
            try:
                return confirmado.read_bytes()
            except OSError:
                raise AlmacenamientoNoDisponible(
                    "no se pudo leer el archivo de la custodia privada"
                ) from None
        if _es_archivo_propio(provisional, self._raiz_resuelta):
            raise DocumentoPendienteDeConfirmacion(
                "la carga sigue siendo provisional: no se confirmó ni se retiró"
            )
        raise DocumentoAusente(
            "la custodia privada no tiene ningún archivo bajo esa referencia"
        )

    def pendientes(self) -> tuple[str, ...]:
        try:
            entradas = list(os.scandir(self._provisionales))
        except OSError:
            raise AlmacenamientoNoDisponible(
                "no se pudo enumerar las reservas de la custodia privada"
            ) from None
        referencias = []
        for entrada in entradas:
            if not _ARCHIVO.match(entrada.name):
                continue
            if not entrada.is_file(follow_symlinks=False):
                continue
            if not _ruta_contenida(Path(entrada.path), self._raiz_resuelta):
                continue
            referencias.append(entrada.name[: -len(SUFIJO)])
        return tuple(sorted(referencias))

    def esta_configurado(self) -> bool:
        return True

    def estado_publicable(self) -> dict:
        try:
            disponible = self._provisionales.is_dir() and self._confirmados.is_dir()
        except OSError:
            disponible = False
        cuerpo = {
            "configurado": True,
            "tipo": "sistema_de_archivos",
            "disponible": disponible,
        }
        try:
            cuerpo["reservas_pendientes"] = len(self.pendientes())
        except AlmacenamientoNoDisponible:
            cuerpo["disponible"] = False
        return cuerpo

def desde_entorno(entorno: dict | None = None) -> AlmacenamientoEnSistemaDeArchivos | None:
    entorno = os.environ if entorno is None else entorno
    bruto = (entorno.get(VARIABLE_RUTA) or "").strip()
    if not bruto:
        return None
    return AlmacenamientoEnSistemaDeArchivos(Path(bruto))
