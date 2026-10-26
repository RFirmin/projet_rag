"""
Ressources partagées du pipeline RAG.
Chargées une seule fois et réutilisées.
"""

import os

from dotenv import load_dotenv
from groq import Groq

from .indexation.embedder import Embedder
from .indexation.storage import load_index
from .recherche.reranker import CrossEncoderReranker

load_dotenv()


class PipelineResources:
    """
    Singleton qui charge les ressources lourdes une seule fois.
    """

    _instance = None

    def __init__(self, index_path: str = "chunks_index_all_3.json"):
        print("🚀 Chargement des ressources du pipeline...")

        print("   📚 Chargement de l'index...")
        self.chunks = load_index(index_path)
        self.index_path = index_path

        print("   🔢 Chargement de l'embedder...")
        self.embedder = Embedder("all-MiniLM-L6-v2", local_only=True)

        print("   🎯 Chargement du reranker...")
        self.reranker = CrossEncoderReranker("BAAI/bge-reranker-base")

        print("   🤖 Initialisation du client Groq...")
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        print("✅ Ressources prêtes.\n")

    @classmethod
    def get_instance(cls, index_path: str = "chunks_index_all_3.json"):
        if cls._instance is None:
            cls._instance = cls(index_path)
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def reload_index(self):
        """Recharge uniquement l'index (après une nouvelle indexation)."""
        print("🔄 Rechargement de l'index...")
        self.chunks = load_index(self.index_path)
        print(f"✅ {len(self.chunks)} chunks rechargés.")
