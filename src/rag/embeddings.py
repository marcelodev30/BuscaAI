class Embedder:
    """Uma instância por processo (criada no lifespan), mas os pesos do modelo
    só são carregados no primeiro uso: são alguns GB e nem todo processo que
    sobe a aplicação vai indexar algo."""

    def __init__(self, model_name: str, batch_size: int):
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors = self._load().encode(
            texts, batch_size=self.batch_size, normalize_embeddings=True, show_progress_bar=False
        )
        return [vector.tolist() for vector in vectors]
