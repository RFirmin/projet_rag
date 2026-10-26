import re
from typing import List, Tuple


class RecursiveTextSplitter:
    """Découpe un texte en chunks de taille contrôlée avec chevauchement."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", "! ", "? ", ";", ", ", " ", ""]

    def split_text(self, text: str) -> List[str]:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" +", " ", text)
        return self._split_recursive(text, self.separators)

    def _split_recursive(self, text: str, separators: List[str]) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        separator = separators[0]
        remaining = separators[1:]

        if separator == "":
            return self._merge_splits(list(text), "")

        splits = text.split(separator)
        if len(splits) == 1:
            return self._split_recursive(text, remaining)

        return self._merge_splits(splits, separator)

    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        chunks = []
        current = []
        current_len = 0
        sep_len = len(separator)

        for split in splits:
            split_len = len(split)

            if split_len > self.chunk_size:
                if current:
                    chunks.append(separator.join(current))
                    current, current_len = [], 0
                chunks.extend(self._split_recursive(split, self.separators[1:]))
                continue

            added = split_len + (sep_len if current else 0)

            if current_len + added > self.chunk_size:
                chunks.append(separator.join(current))

                overlap, overlap_len = [], 0
                for past in reversed(current):
                    past_len = len(past) + sep_len
                    if overlap_len + past_len > self.chunk_overlap:
                        break
                    overlap.insert(0, past)
                    overlap_len += past_len

                current, current_len = overlap, overlap_len

            current.append(split)
            current_len += added

        if current:
            chunks.append(separator.join(current))

        return [c for c in chunks if c.strip()]


def assign_pages_to_chunks(
    chunks: List[str], full_text: str, page_map: List[Tuple[int, int]]
) -> List[Tuple[str, int]]:
    """Attribue un numéro de page à chaque chunk."""
    result = []
    current_pos = 0

    for chunk in chunks:
        chunk_start = full_text.find(chunk, current_pos)
        if chunk_start == -1:
            chunk_start = current_pos

        page_num = 1
        for pos, page in page_map:
            if pos <= chunk_start:
                page_num = page
            else:
                break

        result.append((chunk, page_num))
        current_pos = chunk_start + len(chunk)

    return result
