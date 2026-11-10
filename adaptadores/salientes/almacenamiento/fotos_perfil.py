"""Custodia privada y normalización de fotografías de perfil.

La referencia que llega a PostgreSQL no es una ruta. Los bytes viven fuera del
árbol del repositorio y sólo este adaptador sabe resolverlos. Antes de guardar,
Pillow vuelve a codificar la imagen: se descartan EXIF, perfiles incrustados y
el formato original, y se obtiene un WebP cuadrado de 512 px.
"""

from __future__ import annotations

import io
import os
import re
import secrets
from contextlib import suppress
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

LIMITE_ENTRADA_BYTES = 4 * 1024 * 1024
LADO_SALIDA = 512
_REFERENCIA = re.compile(r"^foto-[0-9a-f]{32}$")


class FotoNoAdmitida(ValueError):
    """El archivo recibido no es una fotografía segura y procesable."""


class AlmacenFotosPerfil:
    """Archivos WebP privados bajo una raíz inyectada por la composición."""

    def __init__(self, raiz: str | Path) -> None:
        self._raiz = Path(raiz).resolve() if str(raiz).strip() else None

    @classmethod
    def desde_entorno(cls) -> AlmacenFotosPerfil:
        return cls(os.environ.get("FOTOS_PERFIL_RUTA", ""))

    @property
    def configurado(self) -> bool:
        if self._raiz is None:
            return False
        prueba = self._raiz / f".comprobacion-{secrets.token_hex(8)}"
        try:
            self._raiz.mkdir(parents=True, exist_ok=True)
            prueba.touch(exist_ok=False)
        except OSError:
            return False
        finally:
            prueba.unlink(missing_ok=True)
        return True

    def guardar(self, entrada: bytes) -> str:
        if not self.configurado:
            raise OSError("la custodia de fotos no está disponible")
        cuerpo = normalizar(entrada)
        referencia = f"foto-{secrets.token_hex(16)}"
        destino = self._ruta(referencia)
        temporal = destino.with_suffix(".tmp")
        try:
            with temporal.open("xb") as archivo:
                archivo.write(cuerpo)
                archivo.flush()
                os.fsync(archivo.fileno())
            with suppress(OSError):
                temporal.chmod(0o600)
            temporal.replace(destino)
        finally:
            temporal.unlink(missing_ok=True)
        return referencia

    def recuperar(self, referencia: str) -> bytes | None:
        try:
            return self._ruta(referencia).read_bytes()
        except FileNotFoundError:
            return None

    def retirar(self, referencia: str) -> bool:
        ruta = self._ruta(referencia)
        try:
            ruta.unlink()
        except FileNotFoundError:
            return False
        return True

    def _ruta(self, referencia: str) -> Path:
        if self._raiz is None:
            raise OSError("la custodia de fotos no está configurada")
        if not _REFERENCIA.fullmatch(referencia or ""):
            raise FotoNoAdmitida("la referencia de foto no es válida")
        return self._raiz / f"{referencia}.webp"


def normalizar(entrada: bytes) -> bytes:
    """Decodifica una imagen estática y devuelve un WebP cuadrado sin metadata."""
    if not entrada:
        raise FotoNoAdmitida("selecciona una imagen")
    if len(entrada) > LIMITE_ENTRADA_BYTES:
        raise FotoNoAdmitida("la imagen supera el límite de 4 MB")
    try:
        with Image.open(io.BytesIO(entrada)) as original:
            if getattr(original, "n_frames", 1) != 1:
                raise FotoNoAdmitida("la foto debe ser una imagen estática")
            if original.width * original.height > 25_000_000:
                raise FotoNoAdmitida("la imagen tiene demasiados píxeles")
            original.load()
            orientada = ImageOps.exif_transpose(original)
            rgb = orientada.convert("RGB")
            cuadrada = ImageOps.fit(
                rgb,
                (LADO_SALIDA, LADO_SALIDA),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
            salida = io.BytesIO()
            cuadrada.save(salida, format="WEBP", quality=88, method=6)
            return salida.getvalue()
    except FotoNoAdmitida:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        Image.DecompressionBombError,
    ):
        raise FotoNoAdmitida("el archivo no es una imagen JPEG, PNG o WebP válida") from None
