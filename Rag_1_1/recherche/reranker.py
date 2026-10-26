from typing import List

import numpy as np
from sentence_transformers import CrossEncoder


class CrossEncoderReranker:
    """
    Réordonne les chunks par pertinence avec un cross-encoder.
    Supporte les modèles logits (ms-marco) et normalisés (BGE).
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        print(f"🔧 Chargement du reranker : {model_name}")
        self.model = CrossEncoder(model_name, local_files_only=True)
        self.model_name = model_name
        self.is_bge = "bge" in model_name.lower()

    def rerank(
        self,
        question: str,
        chunks: List[dict],
        top_k: int = 5,
        seuil: float = None,
        min_chunks: int = 3,
    ) -> List[dict]:
        """Réordonne les chunks et retourne les top_k les plus pertinents."""
        if len(chunks) <= top_k:
            for chunk in chunks:
                chunk["rerank_score"] = 1.0
                chunk["rerank_raw"] = 1.0
            return chunks

        pairs = [(question, chunk["content"]) for chunk in chunks]
        scores_raw = self.model.predict(pairs)

        # Normalisation conditionnelle
        if self.is_bge:
            scores = np.array(scores_raw)
        else:
            scores = 1.0 / (1.0 + np.exp(-np.array(scores_raw)))

        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = float(scores[i])
            chunk["rerank_raw"] = float(scores_raw[i])

        reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)

        # Filtrage par seuil
        if seuil is not None:
            chunks_filtres = [c for c in reranked if c.get("rerank_score", 0) >= seuil]

            if len(chunks_filtres) < min_chunks:
                chunks_filtres = reranked[:min_chunks]

            reranked = chunks_filtres

        return reranked[:top_k]
