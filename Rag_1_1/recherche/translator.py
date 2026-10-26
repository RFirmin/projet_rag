from groq import Groq


def detect_language(text: str) -> str:
    """Détection simple basée sur des mots fréquents français."""
    french_markers = [
        "comment",
        "qu'est-ce",
        "pourquoi",
        "quel",
        "quelle",
        "est-ce",
        "que ",
        "qui ",
        "où ",
        "quand",
        "combien",
        "le ",
        "la ",
        "les ",
        "des ",
        "une ",
        "un ",
        "et ",
        "dans",
        "pour",
        "avec",
        "sur",
        "par",
    ]
    text_lower = " " + text.lower() + " "

    for marker in french_markers:
        if marker in text_lower:
            return "fr"

    return "en"


def translate_to_english(
    text: str,
    groq_client: Groq,
    model: str = "openai/gpt-oss-20b",
) -> str:
    """Traduit un texte en anglais via Groq."""

    MAX_TRANSLATE_CHARS = 1000

    if not text.strip():
        return text

    if detect_language(text) == "en":
        return text

    # la traduction peut retourner une chaine vide en cas de longueur de longueur elevee du texte
    # pour gerer cela on prevoit une limite pour eliminer ce scenario
    if len(text) > MAX_TRANSLATE_CHARS:
        print(f" ⚠️ Texte trop long ({len(text)} caractères), traduction partielle")
        text = text[:MAX_TRANSLATE_CHARS]

    print(f"  🌐 Traduction FR → EN...")

    prompt = (
        "Translate the following text to English. "
        "Return ONLY the translation, without explanation, quotes, or preamble.\n\n"
        f"Text: {text}"
    )

    try:
        response = groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0,
        )

        translation = response.choices[0].message.content.strip()
        translation = translation.strip('"').strip("'").strip()

        # Fallback si traduction vide
        if not translation:
            print("  ⚠️ Traduction vide, utilisation du texte original")
            return text

        return translation

    except Exception as e:
        print(f"  ⚠️ Erreur de traduction : {e}")
        return text
