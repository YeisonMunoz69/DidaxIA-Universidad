from __future__ import annotations

import io

from PIL import Image, ImageOps, UnidentifiedImageError

LIMITE_ENTRADA_BYTES = 5 * 1024 * 1024
LIMITE_SALIDA_BYTES = 3 * 1024 * 1024
LADO_MAXIMO = 1920


class CapturaNoAdmitida(ValueError):
    pass

def _rgb_sobre_blanco(original: Image.Image) -> Image.Image:
    orientada = ImageOps.exif_transpose(original)
    if "A" not in orientada.getbands() and "transparency" not in orientada.info:
        return orientada.convert("RGB")
    capa = orientada.convert("RGBA")
    fondo = Image.new("RGBA", capa.size, "white")
    fondo.alpha_composite(capa)
    return fondo.convert("RGB")

def normalizar_captura(entrada: bytes, *, tipo: str | None = None) -> bytes:
    if not entrada:
        raise CapturaNoAdmitida("selecciona una captura")
    if len(entrada) > LIMITE_ENTRADA_BYTES:
        raise CapturaNoAdmitida("la captura supera el límite de 5 MB")
    try:
        with Image.open(io.BytesIO(entrada)) as original:
            formatos = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
            if original.format not in formatos or (tipo and formatos[original.format] != tipo):
                raise CapturaNoAdmitida("el formato de la captura no corresponde a PNG, JPEG o WebP")
            if getattr(original, "n_frames", 1) != 1:
                raise CapturaNoAdmitida("la captura debe ser una imagen estática")
            if original.width * original.height > 30_000_000:
                raise CapturaNoAdmitida("la captura tiene demasiados píxeles")
            original.load()
            imagen = _rgb_sobre_blanco(original)
            imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.Resampling.LANCZOS)
            for calidad in (84, 72, 60):
                salida = io.BytesIO()
                imagen.save(salida, format="WEBP", quality=calidad, method=6)
                cuerpo = salida.getvalue()
                if len(cuerpo) <= LIMITE_SALIDA_BYTES:
                    return cuerpo
    except CapturaNoAdmitida:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        Image.DecompressionBombError,
    ):
        raise CapturaNoAdmitida(
            "el archivo no es una imagen JPEG, PNG o WebP válida"
        ) from None
    raise CapturaNoAdmitida("la captura no puede reducirse al límite de 3 MB")
