"""
Pipeline RAG complet.
Orchestre l'indexation et la recherche/génération.
"""

import logging
from pathlib import Path
from typing import Dict, Generator, List, Optional

# Génération
from .generation.generator import generate_answer, generate_answer_stream
from .indexation.enricher import ChunkEnricher

# Indexation
from .indexation.extractor import extract_to_markdown
from .indexation.splitter import RecursiveTextSplitter, assign_pages_to_chunks
from .indexation.storage import save_index
from .recherche.aggregator import aggregate_chunks_by_entity
from .recherche.image_extractor import extract_text_with_all_methods
from .recherche.prompt_builder import build_prompt

# Recherche
from .recherche.translator import translate_to_english

# Ressources
from .resources import PipelineResources

# Historique

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Pipeline RAG unifié.

    Usage :
        pipeline = RAGPipeline()

        # Indexation (une fois)
        pipeline.index_documents([
            {"file_path": "books/livre.pdf", "metadata": {...}},
        ])

        # Question (répétée)
        result = pipeline.ask("Comment fonctionne une liste ?")
    """

    def __init__(self, index_path: str = "chunks_index_all_3.json"):
        logger.info(f"Initialisation du pipeline avec index : {index_path}")
        self.index_path = index_path
        self.resources = PipelineResources.get_instance(index_path)
        logger.info(f"Pipeline prêt : {len(self.resources.chunks)} chunks")

    # ============================================================
    # INDEXATION
    # ============================================================

    def index_documents(
        self,
        file_configs: List[Dict],
        output_path: Optional[str] = None,
    ) -> List[Dict]:
        """
        Indexe une liste de documents de types variés.

        Args:
            file_configs: Liste de configs :
                [
                    {
                        "file_path": "books/livre.pdf",
                        "metadata": {"title": "...", "author": "..."},
                        "chunk_size": 1000,      # optionnel
                        "chunk_overlap": 200,    # optionnel
                        "enrichments": [...]     # optionnel
                    },
                ]
            output_path: Chemin de sauvegarde (défaut: self.index_path)

        Returns:
            Liste complète des chunks indexés
        """
        output_path = output_path or self.index_path
        all_chunks = []

        print("=" * 60)
        print(f"INDEXATION ({len(file_configs)} documents)")
        print("=" * 60)

        for config in file_configs:
            try:
                chunks = self._index_single_document(config)
                all_chunks.extend(chunks)
            except Exception as e:
                print(f"❌ Erreur sur {config['file_path']} : {e}")
                continue

        # Index global
        for i, chunk in enumerate(all_chunks):
            chunk["global_index"] = i

        # Sauvegarde
        save_index(all_chunks, output_path)

        # Résumé
        self._print_index_summary(all_chunks)

        return all_chunks

    def _index_single_document(self, config: Dict) -> List[Dict]:
        """Indexe un seul document."""
        file_path = config["file_path"]
        metadata = config.get("metadata", {})
        source_name = Path(file_path).name

        # Adapter les paramètres selon le type
        from .indexation.extractor import detect_file_type

        file_type = detect_file_type(file_path)

        chunk_size = config.get("chunk_size") or (
            1500 if file_type == "excel" else 1000
        )
        chunk_overlap = config.get("chunk_overlap") or (
            300 if file_type == "excel" else 200
        )
        enrichments = config.get("enrichments") or self._default_enrichments(file_type)

        print(f"\n📖 {source_name} ({file_type})")

        # 1. Extraction
        full_text, page_map = extract_to_markdown(file_path)

        # 2. Découpage
        splitter = RecursiveTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        raw_chunks = splitter.split_text(full_text)
        chunks_with_pages = assign_pages_to_chunks(raw_chunks, full_text, page_map)

        # 3. Enrichissement
        enricher = ChunkEnricher(enrichments=enrichments)
        all_texts = [c[0] for c in chunks_with_pages]

        enriched = []
        for idx, (chunk_text, page_num) in enumerate(chunks_with_pages):
            enriched_text = enricher.enrich(
                chunk_text=chunk_text,
                chunk_page=page_num,
                source_name=source_name,
                all_chunks=all_texts,
                chunk_index=idx,
                metadata=metadata,
            )
            enriched.append(
                {
                    "content": enriched_text,
                    "page": page_num,
                    "source": source_name,
                    "title": metadata.get("title", source_name),
                    "author": metadata.get("author", "Unknown"),
                    "file_type": file_type,
                    "chunk_index": idx,
                }
            )

        # 4. Embedding
        embedder = self.resources.embedder
        vectors = embedder.embed_batch(
            [c["content"] for c in enriched], show_progress=False
        )

        for i, chunk in enumerate(enriched):
            chunk["vector"] = vectors[i]

        print(f"   → {len(enriched)} chunks indexés")
        return enriched

    def _default_enrichments(self, file_type: str) -> List[str]:
        """Retourne les enrichissements par défaut selon le type."""
        if file_type == "excel":
            return ["source", "page", "keywords"]
        elif file_type == "csv":
            return ["source", "keywords"]
        else:
            return ["source", "page", "chapter", "summary", "keywords"]

    # ============================================================
    # RECHERCHE & GÉNÉRATION
    # ============================================================

    def ask(
        self,
        question: str,
        image_file=None,
        top_k: int = 5,
        retrieve_n: int = 20,
        seuil_rerank: Optional[float] = 0.3,
        min_chunks: int = 3,
        translate: bool = True,
        filter_by_source: Optional[str] = None,
        # conversation_history: Optional[str] = None,
    ) -> Dict:
        """
        Répond à une question en utilisant le pipeline RAG complet.

        Args:
            question: La question de l'utilisateur
            image_file: Image optionnelle (chemin, bytes, UploadedFile)
            top_k: Nombre de chunks après reranking
            retrieve_n: Nombre de chunks avant reranking
            seuil_rerank: Seuil de pertinence (None = pas de filtrage)
            min_chunks: Nombre minimum de chunks garantis
            translate: Traduire la question en anglais
            filter_by_source: Filtrer sur un document spécifique

        Returns:
            {
                "answer": str,
                "sources": List[Dict],
                "image_text": str (si image fournie),
                "original_question": str
            }
        """
        logger.info(f"Question reçue : {question[:100]}")
        # Récupérer les ressources
        resources = self.resources
        chunks = resources.chunks
        embedder = resources.embedder
        reranker = resources.reranker
        groq_client = resources.groq_client

        original_question = question
        image_text = None

        # 1. Extraction d'image (si fournie)
        if image_file is not None:
            print(f"\n📷 Extraction du texte de l'image...")
            results = extract_text_with_all_methods(image_file)
            image_text = results["best_text"]

            # Limiter la taille
            if len(image_text) > 2000:
                image_text = image_text[:2000]

            # Fusionner avec la question
            question = (
                f"{question}\n\n"
                f"[Texte extrait de l'image fournie par l'utilisateur :]\n"
                f"{image_text}"
            )

        # 2. Traduction
        if translate:
            question_for_search = translate_to_english(question, groq_client)
        else:
            question_for_search = question

        # 3. Filtrage par source (optionnel)
        if filter_by_source:
            chunks = [c for c in chunks if c["source"] == filter_by_source]

        # 4. Embedding de la question
        q_vector = embedder.embed_one(question_for_search)

        # 5. Recherche cosine
        for chunk in chunks:
            chunk["similarity"] = self._cosine_similarity(q_vector, chunk["vector"])

        sorted_chunks = sorted(chunks, key=lambda x: x["similarity"], reverse=True)
        candidates = sorted_chunks[:retrieve_n]
        logger.debug(f"Recherche cosine terminée : {len(candidates)} candidats")

        # 6. Reranking
        reranked = reranker.rerank(
            question=question_for_search,
            chunks=candidates,
            top_k=top_k,
            seuil=seuil_rerank,
            min_chunks=min_chunks,
        )
        logger.debug(f"Reranking terminé : {len(reranked)} chunks retenus")

        # 7. NOUVEAU : Agréger les chunks si nécessaire
        # reranked = aggregate_chunks_by_entity(reranked, original_question)

        # 7. Prompt
        prompt = build_prompt(
            original_question,
            reranked,
            # conversation_history=conversation_history,
        )

        # 8. Génération
        answer = generate_answer(prompt, groq_client)
        logger.info(f"Réponse générée : {len(answer)} caractères")

        # 9. Résultat
        result = {
            "answer": answer,
            "sources": reranked,
            "original_question": original_question,
        }
        if image_text:
            result["image_text"] = image_text

        return result

    @staticmethod
    def _cosine_similarity(a, b) -> float:
        """Similarité cosine entre deux vecteurs."""
        import numpy as np

        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    # ============================================================
    # UTILITAIRES
    # ============================================================

    def _print_index_summary(self, all_chunks: List[Dict]) -> None:
        """Affiche un résumé de l'indexation."""
        print(f"\n{'='*60}")
        print(f"RÉSUMÉ")
        print(f"{'='*60}")

        sources = {}
        for chunk in all_chunks:
            source = chunk["source"]
            if source not in sources:
                sources[source] = {
                    "count": 0,
                    "title": chunk.get("title", source),
                    "type": chunk.get("file_type", "unknown"),
                }
            sources[source]["count"] += 1

        for source, info in sources.items():
            print(f"  📚 {info['title']}")
            print(f"     Type   : {info['type']}")
            print(f"     Chunks : {info['count']}")

        print(f"\n  Total : {len(all_chunks)} chunks")

    def reload_index(self) -> None:
        """Recharge l'index depuis le disque."""
        self.resources.reload_index()

    def get_stats(self) -> Dict:
        """Retourne des statistiques sur l'index."""
        return {
            "total_chunks": len(self.resources.chunks),
            "sources": list(set(c["source"] for c in self.resources.chunks)),
        }

    # Cette facon est plus propre que celle en bas, les 2 font le meme travail
    # mais une approche est plus clean que l'autre
    def ask_with_memory(self, question, memory, **kwargs):
        # 1. Ajouter la question à la mémoire
        memory.add_user(question)

        # 2. Récupérer l'historique (sans la question actuelle)
        #    On utilise les messages AVANT l'ajout de la question actuelle
        history_context = memory.get_context()

        # 3. Calculer le nombre de messages d'historique (hors question actuelle)
        history_count = max(0, len(memory) - 1)

        # 4. Appeler ask() avec la question pure + l'historique séparé
        result = self.ask(
            question=question,  # ← question pure
            conversation_history=history_context,  # ← historique séparé
            **kwargs,
        )

        # 5. Ajouter la réponse à la mémoire
        memory.add_assistant(result["answer"], sources=result["sources"])

        # 6. Enrichir le résultat
        result["history_used"] = history_count

        return result

    # def ask_with_memory(
    #         self,
    #         question: str,
    #         memory: ConversationMemory,
    #         image_file=None,
    #         top_k: int = 5,
    #         retrieve_n: int = 20,
    #         seuil_rerank: Optional[float] = 0.3,
    #         min_chunks: int = 3,
    #         translate: bool = True,
    #         filter_by_source: Optional[str] = None,
    # ) -> Dict:
    #     """
    #     Répond à une question en tenant compte de l'historique de conversation.

    #     Args:
    #         question: La question de l'utilisateur
    #         memory: L'instance ConversationMemory partagée
    #         ... (autres args identiques à ask())

    #     Returns:
    #         {
    #             "answer": str,
    #             "sources": List[Dict],
    #             "original_question": str,
    #             "history_used": int  # nombre de messages d'historique utilisés
    #         }
    #     """

    #     # 1. Ajouter la question a la memoire
    #     memory.add_user(question)

    #     # 2. Recuperez l'historique formate
    #     history_context = memory.get_context()
    #     history_count = len(memory)

    #     # Ce debug est utilise pour se rassurer du type de history_count a cause d'une erreur qui a ete
    #     # generee lors du renvoit de la reponse dans la console
    #     print(f"  🔍 DEBUG history_count = {history_count} (type: {type(history_count)})")

    #     # 3. Appeler la methode ask() mais en enrichissant la question avec l'historique
    #     if history_context and history_count > 1:
    #         # il y'a un historique (au moins la question precedente)
    #         enrichid_question = (
    #             f"Historique de la conversation :\n"
    #             f"{history_context}\n\n"
    #             f"---\n\n"
    #             f"Nouvelle question : {question}"
    #         )
    #     else:
    #         enrichid_question = question

    #     # 4. Appeler le pipeline standard
    #     result = self.ask(
    #         question=enrichid_question,
    #         image_file=image_file,
    #         top_k=top_k,
    #         retrieve_n=retrieve_n,
    #         seuil_rerank=seuil_rerank,
    #         min_chunks=min_chunks,
    #         translate=translate,
    #         filter_by_source=filter_by_source,
    #     )

    #     # 5. Ajouter la reponse a la memoire
    #     memory.add_assistant(result["answer"], sources=result["sources"])

    #     # 6. Enrichir le resultat
    #     # result["history_used"] = history_context - 1 # -1 car on a déjà ajouté la question
    #     # commenter la ligne du haut a permis de resoudre le probleme du retour de la reponse dans la console
    #     result["history_used"] = max(0, int(history_count) - 1) if history_count else 0

    #     return result

    def ask_stream(
        self,
        question: str,
        image_file=None,
        top_k: int = 5,
        retrieve_n: int = 20,
        seuil_rerank: float = 0.3,
        min_chunks: int = 3,
        translate: bool = True,
        filter_by_source: str = None,
        conversation_history: str = None,
    ) -> Generator[str, None, None]:
        """
        Version streaming de ask().
        Yields des morceaux de texte au fur et à mesure.

        Note : Cette méthode ne retourne PAS les sources.
        Pour les sources, utilisez ask() classique.
        """
        import numpy as np

        resources = self.resources
        chunks = resources.chunks
        embedder = resources.embedder
        reranker = resources.reranker
        groq_client = resources.groq_client

        original_question = question

        # Traduction
        if translate:
            question_for_search = translate_to_english(question, groq_client)
        else:
            question_for_search = question

        # Filtrage
        if filter_by_source:
            chunks = [c for c in chunks if c["source"] == filter_by_source]

        # Embedding + cosine
        q_vector = embedder.embed_one(question_for_search)

        for chunk in chunks:
            chunk["similarity"] = float(
                np.dot(q_vector, chunk["vector"])
                / (np.linalg.norm(q_vector) * np.linalg.norm(chunk["vector"]))
            )

        sorted_chunks = sorted(chunks, key=lambda x: x["similarity"], reverse=True)
        candidates = sorted_chunks[:retrieve_n]

        # Reranking
        reranked = reranker.rerank(
            question=question_for_search,
            chunks=candidates,
            top_k=top_k,
            seuil=seuil_rerank,
            min_chunks=min_chunks,
        )

        # Agrégation
        reranked = aggregate_chunks_by_entity(reranked, original_question)

        # Prompt
        prompt = build_prompt(
            original_question,
            reranked,
            conversation_history=conversation_history,
        )

        # Streaming
        yield from generate_answer_stream(prompt, groq_client)
