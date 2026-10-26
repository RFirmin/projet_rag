import re
from typing import Dict, List


class ChunkEnricher:
    """Ajoute des métadonnées aux chunks pour plus de contexte."""

    def __init__(self, enrichments: List[str] = None):
        self.enrichments = enrichments or ["source", "page"]

    def enrich(
        self,
        chunk_text: str,
        chunk_page: int,
        source_name: str,
        all_chunks: List[str] = None,
        chunk_index: int = None,
        metadata: Dict = None,
    ) -> str:
        prefix = []

        if "source" in self.enrichments:
            prefix.append(f"[Document: {source_name}]")

        if metadata:
            if metadata.get("title"):
                prefix.append(f"[Titre: {metadata['title']}]")
            if metadata.get("author"):
                prefix.append(f"[Auteur: {metadata['author']}]")

        if "chapter" in self.enrichments:
            chapter = self._detect_chapter(chunk_text, all_chunks, chunk_index)
            if chapter:
                prefix.append(f"[{chapter}]")

        if "page" in self.enrichments:
            prefix.append(f"[Page {chunk_page}]")

        if "summary" in self.enrichments:
            summary = self._summarize(chunk_text)
            prefix.append(f"[Résumé: {summary}]")

        if "keywords" in self.enrichments:
            kw = self._extract_keywords(chunk_text)
            if kw:
                prefix.append(f"[Thèmes: {', '.join(kw)}]")

        if "questions" in self.enrichments:
            qs = self._generate_questions(chunk_text)
            if qs:
                prefix.append(f"[Questions: {' | '.join(qs)}]")

        if "context" in self.enrichments and all_chunks and chunk_index is not None:
            ctx = self._get_context(all_chunks, chunk_index)
            if ctx:
                prefix.append(f"[Contexte: {ctx}]")

        prefix_str = " ".join(prefix)
        return f"{prefix_str}\n\n{chunk_text}" if prefix_str else chunk_text

    def _detect_chapter(self, text, all_chunks, idx):
        patterns = [
            r"(?:Chapitre|Chapter|CHAPITRE)\s+(\d+[:\s\-].*?)(?:\n|$)",
            r"(?:Section|Partie)\s+(\d+[:\s\-].*?)(?:\n|$)",
            r"^#+\s+(.+)$",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if m:
                return f"Chapitre: {m.group(0).strip()}"

        if all_chunks and idx is not None:
            for i in range(idx - 1, max(idx - 4, -1), -1):
                if i >= 0:
                    for pattern in patterns:
                        m = re.search(
                            pattern, all_chunks[i], re.IGNORECASE | re.MULTILINE
                        )
                        if m:
                            return f"Chapitre: {m.group(0).strip()}"
        return None

    def _summarize(self, text, max_words=15):
        sentences = re.split(r"[.!?]+", text)
        words = sentences[0].strip().split()
        if len(words) > max_words:
            return " ".join(words[:max_words]) + "..."
        return sentences[0].strip()

    def _extract_keywords(self, text, max_kw=5):
        stopwords = {
            "dans",
            "pour",
            "avec",
            "plus",
            "leur",
            "être",
            "avoir",
            "cette",
            "comme",
            "tout",
            "bien",
            "peut",
            "sont",
            "aux",
            "pas",
            "sur",
            "qui",
            "que",
            "par",
            "est",
            "une",
            "les",
            "des",
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
        }
        words = re.findall(r"\b[a-zA-ZÀ-ÿ]{4,}\b", text.lower())
        freq = {}
        for w in words:
            if w not in stopwords:
                freq[w] = freq.get(w, 0) + 1
        return [
            w
            for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:max_kw]
        ]

    def _generate_questions(self, text):
        qs = []
        m = re.search(r"(\w+(?:\s\w+){0,5})\s+(?:est|sont)\s(.+?)(?:\.|$)", text)
        if m:
            qs.append(f"Qu'est-ce que {m.group(1)} ?")
        if re.search(r"(?:car|parce que|grâce à|en raison de)", text):
            qs.append("Pourquoi ?")
        if re.search(r"(?:comment|méthode|façon|manière)", text):
            qs.append("Comment faire ?")
        return qs[:3]

    def _get_context(self, all_chunks, idx, chars=200):
        if idx > 0 and idx - 1 < len(all_chunks):
            return all_chunks[idx - 1][-chars:].strip()
        return None
