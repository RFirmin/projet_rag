import json
from pathlib import Path
from typing import Dict, List


def save_index(
    chunks_data: List[Dict], output_path: str = "chunks_index_all_3.json"
) -> None:
    """Sauvegarde les chunks enrichis et leurs vecteurs sur disque."""
    output_file = Path(output_path)

    data_to_save = []
    for chunk in chunks_data:
        data_to_save.append(
            {
                "content": chunk["content"],
                "page": chunk.get("page", 1),
                "source": chunk.get("source", "unknown"),
                "title": chunk.get("title", chunk.get("source", "unknown")),
                "author": chunk.get("author", "Unknown"),
                "file_type": chunk.get("file_type", "unknown"),
                "chunk_index": chunk.get("chunk_index", 0),
                "global_index": chunk.get("global_index", 0),
                "vector": (
                    chunk["vector"]
                    if isinstance(chunk["vector"], list)
                    else chunk["vector"].tolist()
                ),
            }
        )

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(data_to_save)} chunks sauvegardés dans {output_path}")
    print(f"   Taille : {output_file.stat().st_size / (1024*1024):.2f} Mo")


def load_index(input_path: str = "chunks_index_all_3.json") -> List[Dict]:
    """Charge les chunks depuis le disque."""
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Fichier introuvable : {input_path}")

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = []
    for item in data:
        chunks.append(
            {
                "content": item["content"],
                "page": item["page"],
                "source": item["source"],
                "title": item.get("title", item["source"]),
                "author": item.get("author", "Unknown"),
                "file_type": item.get("file_type", "unknown"),
                "chunk_index": item.get("chunk_index", 0),
                "global_index": item.get("global_index", 0),
                "vector": item["vector"],
            }
        )

    print(f"✅ {len(chunks)} chunks chargés depuis {input_path}")
    return chunks
