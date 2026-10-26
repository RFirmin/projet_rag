####################################################################
######################### Version 3.0 ##############################
################ elle realise l'indexation du flux #################
############### en prenant en compte plusieurs types################
############ de document (PDF, Excel, Word, CSV, TXT) ##############
####################################################################

from pathlib import Path
from typing import Dict, List

from embedder import Embedder
from enricher import ChunkEnricher
from extractor import detect_file_type
from extractor_pdf import extract_pdf_with_progression
from splitter import RecursiveTextSplitter, assign_pages_to_chunks
from storage import save_index


def index_document_to_memory(
    file_path: str,
    metadata: Dict = None,
    chunk_size: int = None,
    chunk_overlap: int = None,
    enrichments: List[str] = None,
) -> List[Dict]:
    """
    Indexe un document (PDF, Excel, Word, CSV, TXT) et retourne les chunks vectorisés.

    Les paramètres de chunking sont adaptés automatiquement au type de fichier.
    """
    source_name = Path(file_path).name
    file_type = detect_file_type(file_path)
    metadata = metadata or {}

    # Ajustement automatique des paramètres selon le type
    if file_type == "excel":
        # Les tableaux ont besoin de chunks plus grands pour garder l'en-tête
        chunk_size = chunk_size or 1500
        chunk_overlap = chunk_overlap or 300
        # Enrichissements adaptés aux Excel
        enrichments = enrichments or ["source", "page", "keywords"]
    elif file_type == "csv":
        chunk_size = chunk_size or 1500
        chunk_overlap = chunk_overlap or 300
        enrichments = enrichments or ["source", "keywords"]
    else:
        # PDF, Word, TXT → paramètres standard
        chunk_size = chunk_size or 1000
        chunk_overlap = chunk_overlap or 200
        enrichments = enrichments or [
            "source",
            "page",
            "chapter",
            "summary",
            "keywords",
        ]

    print(f"\n  📖 Traitement de : {source_name}")
    print(f"     Type : {file_type}")
    print(f"     Chunk size : {chunk_size} | Overlap : {chunk_overlap}")

    # 1. Extraction unifiée
    print(f"    1. Extraction...")
    full_text, page_map = extract_pdf_with_progression(file_path)
    print(f"       → {len(full_text)} caractères extraits")

    # 2. Découpage
    print(f"    2. Découpage en chunks...")
    splitter = RecursiveTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    raw_chunks = splitter.split_text(full_text)
    chunks_with_pages = assign_pages_to_chunks(raw_chunks, full_text, page_map)
    print(f"       → {len(chunks_with_pages)} chunks créés")

    # 3. Enrichissement
    print(f"    3. Enrichissement...")
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
    print(f"    4. Vectorisation...")
    embedder = Embedder("all-MiniLM-L6-v2", local_only=True)
    vectors = embedder.embed_batch(
        [c["content"] for c in enriched], show_progress=False
    )

    for i, chunk in enumerate(enriched):
        chunk["vector"] = vectors[i]

    print(f"       → {len(vectors)} vecteurs générés")

    return enriched


def index_multiple_documents(
    file_configs: List[Dict],
    output_path: str = "chunks_index_all_3.json",
) -> List[Dict]:
    """
    Indexe plusieurs documents et les fusionne dans un seul fichier d'index.

    Args:
        file_configs: Liste de dictionnaires :
            [
                {
                    "file_path": "books_to_index/livre1.pdf",
                    "metadata": {"title": "...", "author": "..."},
                },
                ...
            ]
        output_path: Chemin du fichier de sortie fusionné

    Returns:
        Liste complète des chunks indexés
    """
    all_chunks = []

    print("=" * 60)
    print(f"INDEXATION MULTI-DOCUMENTS ({len(file_configs)} fichiers)")
    print("=" * 60)

    for config in file_configs:
        file_path = config["file_path"]
        metadata = config.get("metadata", {})
        chunk_size = config.get("chunk_size", 1000)
        chunk_overlap = config.get("chunk_overlap", 200)
        enrichments = config.get("enrichments", None)

        try:
            chunks = index_document_to_memory(
                file_path=file_path,
                metadata=metadata,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                enrichments=enrichments,
            )
            all_chunks.extend(chunks)

        except Exception as e:
            print(f"  ❌ Erreur sur {file_path} : {e}")
            continue

    # Réindexer les chunk_index globalement
    for i, chunk in enumerate(all_chunks):
        chunk["global_index"] = i

    # Sauvegarde
    print(f"\n{'='*60}")
    print(f"SAUVEGARDE")
    print(f"{'='*60}")
    save_index(all_chunks, output_path)

    # Résumé par document
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
        print(f"     Fichier : {source}")
        print(f"     Type    : {info['type']}")
        print(f"     Chunks  : {info['count']}")

    print(f"\n  Total : {len(all_chunks)} chunks")
    print(f"  Fichier : {output_path}")

    return all_chunks


# ============================================================
# UTILISATION
# ============================================================

if __name__ == "__main__":
    file_configs = [
        {
            "file_path": "books_to_index/Deep Dive Python - Techniques and Best Practices for Developers (True PDF).pdf",
            "metadata": {
                "title": "Deep Dive Python",
                "author": "Adarsh Divakaran",
            },
        },
        {
            "file_path": "books_to_index/Algorithms Illuminated (Part 1) - The Basics -- Tim Roughgarden -- ( WeLib.org ).pdf",
            "metadata": {
                "title": "Algorithms Illuminated - Part 1",
                "author": "Tim Roughgarden",
            },
        },
        {
            "file_path": "books_to_index/TABLEAU FORMULE&CHAINES CANAL+.xlsx",
            "metadata": {
                "title": "Tableau Formules & Chaînes Canal+",
                "author": "Canal+",
            },
        },
        {
            "file_path": "books_to_index/guide_canal_plus.pdf",
            "metadata": {
                "title": "Guide Canal+",
                "author": "Canal+",
            },
        },
        {
            "file_path": "books_to_index/Enregistrement DOCUMENTAIRE CANAL.pdf",
            "metadata": {
                "title": "Enregistrement DOCUMENTAIRE CANAL",
                "author": "Canal+",
            },
        },
        {
            "file_path": "books_to_index/INFO_DES_CHAINES_CANAL_PLUS_COMPLETE (1).pdf",
            "metadata": {
                "title": "INFO DES CHAINES CANAL PLUS COMPLETE",
                "author": "Canal+",
            },
        },
        {
            "file_path": "books_to_index/MODULE DE FORMATION FUJISAT 2026.pdf",
            "metadata": {
                "title": "MODULE DE FORMATION FUJISAT 2026",
                "author": "Canal+",
            },
        },
    ]

    all_chunks = index_multiple_documents(
        file_configs=file_configs,
        output_path="chunks_index_all_3.json",
    )

    print(f"\n✅ Indexation terminée : {len(all_chunks)} chunks au total")
