import numpy as np

MODEL_NAME = "BAAI/bge-small-en-v1.5"


class Embedder:
    def __init__(self, model_name: str = MODEL_NAME):
        from fastembed import TextEmbedding

        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return _normalize(np.asarray(list(self._model.embed(texts)), dtype=np.float32))

    def embed_query(self, query: str) -> np.ndarray:
        [vector] = list(self._model.query_embed([query]))
        return _normalize(np.asarray(vector, dtype=np.float32))


def _normalize(vectors: np.ndarray) -> np.ndarray:
    return vectors / np.linalg.norm(vectors, axis=-1, keepdims=True)
