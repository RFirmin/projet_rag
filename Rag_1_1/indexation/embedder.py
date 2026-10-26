from typing import List

from sentence_transformers import SentenceTransformer


class Embedder:
    """Génère des embeddings sémantiques."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", local_only: bool = True):
        self.model = SentenceTransformer(model_name, local_files_only=local_only)
        self.dimensions = self.model[0].auto_model.config.hidden_size

    def embed_one(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()

    def embed_batch(
        self, texts: List[str], show_progress: bool = True
    ) -> List[List[float]]:
        return self.model.encode(
            texts, show_progress_bar=show_progress, batch_size=32
        ).tolist()
