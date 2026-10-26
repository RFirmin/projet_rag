"""
Agrège les chunks avant envoi au LLM.
Détecte les entités répétées et regroupe leurs valeurs.
"""

import re
from typing import Dict, List


def aggregate_chunks_by_entity(
    chunks: List[Dict],
    question: str,
) -> List[Dict]:
    """
    Détecte les entités répétées dans les chunks et les regroupe.

    Exemple :
        Chunk 1 : |1|CRTV|...
        Chunk 2 : |501|CRTV|...

    Devient :
        [ENTITÉ AGRÉGÉE] CRTV : 1, 501

    Args:
        chunks: Liste des chunks (avec "content")
        question: La question de l'utilisateur

    Returns:
        Liste de chunks avec un chunk d'agrégation ajouté en tête
    """
    # Détecter les entités mentionnées dans la question
    # (mots en majuscules, termes entre guillemets, etc.)
    entities = _extract_entities_from_question(question)

    if not entities:
        return chunks

    # Pour chaque entité, chercher toutes les lignes qui la mentionnent
    aggregated = {}

    for entity in entities:
        entity_upper = entity.upper()
        values = []

        for chunk in chunks:
            content = chunk["content"]

            # Chercher les lignes contenant l'entité
            for line in content.split("\n"):
                if entity_upper in line.upper():
                    values.append(
                        {
                            "line": line.strip(),
                            "page": chunk.get("page", "?"),
                            "source": chunk.get("source", "?"),
                        }
                    )

        if values:
            aggregated[entity] = values

    # Si aucune agrégation trouvée, retourner les chunks originaux
    if not aggregated:
        return chunks

    # Construire un chunk d'agrégation
    agg_text = "=== AGRÉGATION DES OCCURRENCES ===\n\n"

    for entity, values in aggregated.items():
        agg_text += f"Entité : {entity}\n"
        agg_text += f"Nombre d'occurrences : {len(values)}\n"
        agg_text += "Toutes les lignes trouvées :\n"

        for i, v in enumerate(values, 1):
            agg_text += f"  {i}. {v['line']}\n"

        agg_text += "\n"

    agg_text += "=== FIN DE L'AGRÉGATION ===\n"

    # Créer un chunk synthétique
    aggregation_chunk = {
        "content": agg_text,
        "page": chunks[0].get("page", "?") if chunks else "?",
        "source": chunks[0].get("source", "?") if chunks else "?",
        "title": chunks[0].get("title", "?") if chunks else "?",
        "similarity": 1.0,  # score max pour qu'il soit prioritaire
        "rerank_score": 1.0,
        "is_aggregation": True,
    }

    # Placer le chunk d'agrégation EN PREMIER
    return [aggregation_chunk] + chunks


def _extract_entities_from_question(question: str) -> List[str]:
    """
    Extrait les entités probables de la question.

    Cherche :
    - Les mots en MAJUSCULES (ex: CRTV)
    - Les termes entre guillemets (ex: "CRTV")
    - Les noms propres après "de", "du", "la", "le"
    """
    entities = []

    # Mots en majuscules (2+ lettres)
    entities.extend(re.findall(r"\b[A-Z][A-Z0-9]+\b", question))

    # Termes entre guillemets
    entities.extend(re.findall(r'"([^"]+)"', question))
    entities.extend(re.findall(r"«\s*([^»]+)\s*»", question))

    # Après "de la", "du", "de"
    entities.extend(re.findall(r"(?:de la|du|de)\s+([A-Z][a-zA-Z]+)", question))

    # Nettoyer et dédupliquer
    entities = [e.strip() for e in entities if len(e.strip()) >= 2]

    return list(set(entities))
