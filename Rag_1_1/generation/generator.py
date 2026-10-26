import re
from typing import Generator

from groq import Groq


def clean_response(text: str) -> str:
    """
    Supprime la section de raisonnement interne des modèles.
    Stratégie : si une balise de fin est détectée, garder ce qui suit.
    """
    if not text:
        return text

    closing_patterns = [
        r"</think>",
        r"</thinking>",
        r"</\s*think>",
        r"\[/thinking\]",
    ]

    for pattern in closing_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            after = text[match.end() :].strip()
            if after:
                return after

    # Fallback : si <think> sans fermeture (tronqué)
    opening = re.search(r"<\s*think\s*>", text, flags=re.IGNORECASE)
    if opening:
        before = text[: opening.start()].strip()
        if before:
            return before
        return (
            "(Réponse non disponible : le modèle a épuisé son quota avant de répondre.)"
        )

    return text.strip()


def generate_answer(
    prompt: dict,
    groq_client: Groq,
    model: str = "qwen/qwen3.8-27b",
    temperature: float = 0.3,
    max_tokens: int = None,
) -> str:
    """Génère une réponse via le LLM Groq avec fallback multi-modèles."""

    models_config = {
        "openai/gpt-oss-120b": {"max_tokens": 1500},
        "openai/gpt-oss-20b": {"max_tokens": 1024},
        "qwen/qwen3.8-27b": {"max_tokens": 900},
        "qwen/qwen3.6-27b": {"max_tokens": 900},
        "allam-2-7b": {"max_tokens": 1024},
    }

    models_to_test = [model] + [m for m in models_config.keys() if m != model]

    seen = set()
    unique_models = []
    for m in models_to_test:
        if m not in seen:
            seen.add(m)
            unique_models.append(m)

    last_error = None

    for model_name in unique_models:
        try:
            model_config = models_config.get(model_name, {"max_tokens": 1024})
            actual_max = max_tokens if max_tokens else model_config["max_tokens"]

            response = groq_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]},
                ],
                temperature=temperature,
                max_tokens=actual_max,
            )

            raw_answer = response.choices[0].message.content
            # clean_answer = clean_response(raw_answer)

            print(f"✅ Réponse générée avec {model_name} (max_tokens={actual_max})")
            return raw_answer

        except Exception as e:
            print(f"❌ Erreur avec {model_name} : {e}")
            last_error = e
            continue

    raise Exception(f"Aucun modèle Groq n'a fonctionné. Dernière erreur : {last_error}")


def generate_answer_stream(
    prompt: dict,
    groq_client: Groq,
    model: str = "openai/gpt-oss-120b",
    temperature: float = 0.3,
    max_tokens: int = None,
) -> Generator[str, None, None]:
    """
    Genere une reponse en streaming (mot par mot).

    Yields:
        Des morceaux de texte (chunks) au fur et a mesure de la generation.
    """
    models_config = {
        "openai/gpt-oss-120b": {"max_tokens": 1500},
        "openai/gpt-oss-20b": {"max_tokens": 1024},
        "qwen/qwen3.6-27b": {"max_tokens": 900},
        "qwen/qwen3.8-27b": {"max_tokens": 900},
        "allam-2-7b": {"max_tokens": 1024},
    }

    models_to_test = [model] + [m for m in models_config.keys() if m != model]

    seen = set()
    unique_models = []
    for m in models_to_test:
        if m not in seen:
            seen.add(m)
            unique_models.append(m)

    last_error = None

    for model_name in unique_models:
        try:
            model_config = models_config.get(model_name, {"max_tokens": 1024})
            actual_max = max_tokens if max_tokens else model_config["max_tokens"]

            # Appel avec stream=True
            stream = groq_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]},
                ],
                temperature=temperature,
                max_tokens=actual_max,
                stream=True,  # ← Active le streaming
            )

            print(f"✅ Streaming démarré avec {model_name}")

            # Buffer pour gérer les balises <think>
            buffer = ""
            in_think_block = False
            think_buffer = ""

            for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                if not delta.content:
                    continue

                content = delta.content

                # Détection de <think>
                if "<think>" in content or "<thinking>" in content:
                    in_think_block = True
                    think_buffer = ""
                    # Garder ce qui vient avant la balise
                    before = content.split("<think>")[0].split("<thinking>")[0]
                    if before:
                        yield before
                    continue

                if in_think_block:
                    think_buffer += content
                    # Vérifier si on sort du bloc
                    if "</think>" in think_buffer or "</thinking>" in think_buffer:
                        in_think_block = False
                        # Garder ce qui vient après
                        after = re.split(
                            r"</think(?:ing)?>", think_buffer, flags=re.IGNORECASE
                        )[-1]
                        if after:
                            yield after
                        think_buffer = ""
                    continue

                # Cas normal
                yield content

            print(f"✅ Streaming terminé avec {model_name}")
            return

        except Exception as e:
            print(f"❌ Erreur streaming avec {model_name} : {e}")
            last_error = e
            continue

    raise Exception(f"Aucun modèle Groq n'a fonctionné. Dernière erreur : {last_error}")
