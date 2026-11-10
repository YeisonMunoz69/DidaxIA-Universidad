from __future__ import annotations

from adaptadores.salientes.recuperacion.indice import DIMENSION


MODELO = "intfloat/multilingual-e5-base"


class CodificadorE5:

    def __init__(self, modelo: str = MODELO) -> None:
        from sentence_transformers import SentenceTransformer

        self._modelo = SentenceTransformer(modelo)

    def codificar(self, textos: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
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
        return DIMENSION
