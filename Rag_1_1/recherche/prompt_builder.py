from typing import List, Optional


def build_prompt(
    question: str,
    chunks: List[dict],
    conversation_history: Optional[str] = None,
) -> dict:
    """Construit le prompt système et utilisateur pour le LLM."""

    context_parts = []
    for chunk in chunks:
        context_parts.append(chunk["content"])

    context = "\n\n---\n\n".join(context_parts)

    # system_prompt = (
    #     "Vous êtes un assistant documentaire précis et fiable. "
    #     "Répondez UNIQUEMENT en vous basant sur le contexte fourni ci-dessous. "
    #     "Si la réponse n'est pas dans le contexte, dites-le clairement. "
    #     "Ne mentionnez pas les noms de fichiers ou numéros de page dans votre réponse. "
    #     "Soyez concis et allez à l'essentiel. "
    #     "Si les informations sont incomplètes ou ambiguës, précisez-le."
    #     "Répondez TOUJOURS dans la langue de la question."

    #     "Réponds toujours par des phrases complètes, pas par des listes brutes. "
    #     "Par exemple : 'Les numéros associés à CRTV sont le 1, le 501 et le 920.' "
    #     "au lieu de '1, 501, 920'."
    #     "- Si la question porte sur des numéros, codes ou identifiants, "
    #     "  citez TOUS dans une phrase : 'Les numéros sont X, Y et Z.'\n"
    # )

    system_prompt = (
        "Vous êtes un assistant documentaire précis et fiable. "
        "Répondez UNIQUEMENT en vous basant sur le contexte fourni ci-dessous. "
        "Si la réponse n'est pas dans le contexte, dites-le clairement. "
        "Ne mentionnez pas les noms de fichiers ou numéros de page dans votre réponse. "
        "\n\n"
        "RÈGLES DE RÉPONSE (à appliquer systématiquement) :\n"
        "\n"
        "1. AGRÉGATION : Si une information apparaît à plusieurs endroits "
        "   dans le contexte (plusieurs numéros pour une même chaîne, "
        "   plusieurs occurrences d'une même entité, plusieurs valeurs "
        "   pour un même attribut), tu DOIS toutes les mentionner. "
        "   Ne choisis JAMAIS une seule valeur arbitrairement.\n"
        "\n"
        "2. FORME : Réponds toujours par des phrases complètes et naturelles. "
        "   Ne renvoie jamais une liste brute sans introduction.\n"
        "\n"
        "3. EXHAUSTIVITÉ : Si tu trouves plusieurs valeurs, cite-les toutes. "
        "   Par exemple : 'Les numéros sont le 1 et le 501.' "
        "   et non pas seulement '501'.\n"
        "\n"
        "4. EXEMPLES :\n"
        "   ❌ Mauvais : '501'\n"
        "   ✅ Bon : 'Les numéros associés à CRTV sont le 1 et le 501.'\n"
        "   ❌ Mauvais : '1, 2, 3'\n"
        "   ✅ Bon : 'Les numéros sont le 1, le 2 et le 3.'\n"
        "\n"
        "5. Si l'information n'est pas dans le contexte, dis : "
        "   'Je ne trouve pas cette information dans les documents disponibles.'"
    )

    # Construire le prompt utilisateur
    user_parts = []

    if conversation_history:
        user_parts.append(f"Historique de la conversation :\n{conversation_history}")

    user_parts.append(f"Contexte documentaire :\n{context}")
    user_parts.append(f"Question : {question}")
    user_parts.append("Reponse :")

    user_prompt = "\n\n".join(user_parts)

    return {
        "system": system_prompt,
        "user": user_prompt,
    }
