import base64
import binascii
import io
import warnings

from PIL import Image

FORMATOS = {'image/png': 'PNG', 'image/jpeg': 'JPEG', 'image/webp': 'WEBP'}
MAX_BYTES = 1_500_000
MAX_TOTAL = 8_000_000


def validar_imagenes_encuesta(contenido, *, publicable=False):
    from dominio.modelo.recursos import RecursoInvalido, texto

    total = 0
    paginas = contenido.get('paginas', [])
    bloques = [(n, i, b) for n, p in enumerate(paginas, 1) if isinstance(p, dict)
               for i, b in enumerate([p, *p.get('preguntas', [])])]
    for pagina, pregunta, bloque in bloques:
        if not isinstance(bloque, dict):
            continue
        texto(bloque.get('transcripcion', ''), 10000)
        imagenes = bloque.get('imagenes', [])
        if not isinstance(imagenes, list) or len(imagenes) > 4:
            raise RecursoInvalido('Usa hasta cuatro imÃ¡genes por pÃ¡gina o pregunta.')
        for numero, imagen in enumerate(imagenes, 1):
            if not isinstance(imagen, dict):
                raise RecursoInvalido('Imagen de encuesta no vÃ¡lida.')
            descripcion = texto(imagen.get('alt', ''), 500)
            if publicable and not descripcion:
                ubicacion = f'página {pagina}' + (f', pregunta {pregunta}' if pregunta else '')
                raise RecursoInvalido(f'Antes de publicar, completa la descripción accesible de la imagen {numero} en {ubicacion}.')
            texto(imagen.get('pie', ''), 1000)
            src = imagen.get('src')
            if not isinstance(src, str) or len(src) > MAX_BYTES * 4 // 3 + 100:
                raise RecursoInvalido('Cada imagen admite hasta 1,5 MB.')
            cabecera, separador, valor = src.partition(',')
            mime = cabecera.removeprefix('data:').removesuffix(';base64')
            if not separador or cabecera != f'data:{mime};base64' or mime not in FORMATOS:
                raise RecursoInvalido('Usa imÃ¡genes PNG, JPEG o WebP incrustadas.')
            try:
                datos = base64.b64decode(valor, validate=True)
                if not datos or len(datos) > MAX_BYTES:
                    raise ValueError('tamaÃ±o')
                with warnings.catch_warnings():
                    warnings.simplefilter('error', Image.DecompressionBombWarning)
                    with Image.open(io.BytesIO(datos)) as raster:
                        if (raster.format != FORMATOS[mime] or raster.width > 6000 or raster.height > 6000
                                or raster.width * raster.height > 16_000_000 or getattr(raster, 'is_animated', False)):
                            raise ValueError('formato o dimensiones')
                        raster.verify()
            except (ValueError, OSError, binascii.Error, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
                raise RecursoInvalido('La imagen estÃ¡ daÃ±ada, animada o supera las dimensiones permitidas.') from exc
            total += len(datos)
            if total > MAX_TOTAL:
                raise RecursoInvalido('Las imÃ¡genes de la encuesta superan 8 MB. Reduce su tamaÃ±o.')
