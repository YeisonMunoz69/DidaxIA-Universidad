"""
codificador.py — El codificador real, sobre intfloat/multilingual-e5-base
==========================================================================

Cierra lo que faltaba del incremento 2: el `Codificador` que `indice.py` declara
como contrato pero solo tenía un doble de juguete. Con esto el índice sobre
PostgreSQL (`indice_postgres.py`) codifica de verdad, y no con similitud léxica.

`ADR-002` fijó el **modelo por medición** —E01 lo validó— y `06-Guia-de-Reutilizacion.md`
§3 marca `intfloat/multilingual-e5-base` como *lo que no se toca* de
`kb/vector_store.py`. La dimensión, 768, sale del `hidden_size` de la ficha del
modelo y está fijada en el esquema; aquí se referencia `DIMENSION` de `indice.py`
para que las dos no puedan divergir.

Por qué vive detrás del contrato `Codificador` y no dentro del índice
--------------------------------------------------------------------
El contrato de `indice.py` ya lo dice: el modelo real arrastra media biblioteca
de aprendizaje automático —`sentence-transformers`, y con ella `torch`—, y
meterlo en el adaptador de índice obligaría a instalarla para probar una
consulta SQL. Por eso `sentence_transformers` se importa **dentro** del
constructor: este módulo se puede leer e inspeccionar sin nada instalado, y solo
quien vaya a codificar de verdad paga la dependencia. Es el mismo patrón con el
que `indice_postgres.py` importa `psycopg`.

Sobre los prefijos de e5, que es donde es fácil equivocarse
-----------------------------------------------------------
Los modelos e5 recomiendan anteponer `query:` a las consultas y `passage:` a los
documentos. **El contrato `Codificador` tiene un solo método** `codificar`, que
`indice_postgres.py` usa igual para guardar fragmentos y para consultar, de modo
que no hay forma de distinguir uno de otro aquí, ni debe haberla: E01 —la
medición que valida la calidad— corrió sobre el índice del prototipo, que
codificaba consulta y pasaje **del mismo modo, sin prefijos**. Añadir prefijos
aquí divergiría de lo que E01 midió. Se codifica simétrico, sin prefijo, que es
lo coherente con el contrato y con la medición.

La normalización no cambia el orden bajo coseno —`indice_postgres` mide con
`vector_cosine_ops`—, así que dejar los vectores de norma uno es inocuo para el
ranking y más limpio para el almacén.
"""

from __future__ import annotations

from adaptadores.salientes.recuperacion.indice import DIMENSION

#: El modelo que E01 validó. No se cambia sin repetir esa medición: es lo que
#: `06-Guia-de-Reutilizacion.md` §3 marca como intocable.
MODELO = "intfloat/multilingual-e5-base"


class CodificadorE5:
    """Implementa el contrato `Codificador` de `indice.py`.

    Carga el modelo al construirse; una instancia se reutiliza para todas las
    codificaciones, que es lo que evita pagar la carga —segundos— en cada
    llamada.
    """

    def __init__(self, modelo: str = MODELO) -> None:
        # Importado aquí a propósito: ver la cabecera. Sin esto, el módulo no se
        # podría importar sin `sentence-transformers` instalado, y sus pruebas
        # dejarían de saltarse solas.
        from sentence_transformers import SentenceTransformer

        self._modelo = SentenceTransformer(modelo)

    def codificar(self, textos: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """Una representación densa por texto, en el mismo orden.

        Devuelve `()` ante una entrada vacía sin llamar al modelo: no hay nada
        que codificar y el modelo tampoco lo agradecería.
        """
        if not textos:
            return ()

        vectores = self._modelo.encode(
            list(textos),
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return tuple(tuple(float(x) for x in fila) for fila in vectores)

    @property
    def dimension(self) -> int:
        """La longitud que este codificador promete, para comprobarla temprano.

        Es `DIMENSION` de `indice.py` —la del esquema—: si el modelo devolviera
        otra, el índice lo detecta antes de ir a la base, pero tener el número
        aquí deja el contrato explícito.
        """
        return DIMENSION
