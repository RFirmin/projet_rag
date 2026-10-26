from pathlib import Path
from typing import List, Tuple


def detect_file_type(file_path: str) -> str:
    """Détecte le type de fichier par son extension."""
    ext = Path(file_path).suffix.lower()

    mapping = {
        ".pdf": "pdf",
        ".xlsx": "excel",
        ".xls": "excel",
        ".docx": "word",
        ".doc": "word",
        ".csv": "csv",
        ".txt": "text",
        ".md": "text",
    }

    return mapping.get(ext, "unknown")


def extract_to_markdown(file_path: str) -> Tuple[str, List[Tuple[int, int]]]:
    """
    Point d'entrée unifié : détecte le type et route vers le bon extracteur.

    Returns:
        (markdown_complet, page_map)
        page_map = [(position_caractère, numéro_page_ou_feuille), ...]
    """
    file_type = detect_file_type(file_path)

    print(f"📄 Type détecté : {file_type} ({Path(file_path).name})")

    # if file_type == "pdf":
    #     from .extractor_pdf import extract_pdf
    #     return extract_pdf(file_path)

    if file_type == "pdf":
        from .extractor_pdf import extract_pdf_with_progression

        return extract_pdf_with_progression(file_path)

    elif file_type == "excel":
        from .extractor_excel import extract_excel

        return extract_excel(file_path)

    elif file_type == "word":
        from .extractor_word import extract_word

        return extract_word(file_path)

    elif file_type == "csv":
        from .extractor_csv import extract_csv

        return extract_csv(file_path)

    elif file_type == "text":
        from .extractor_text import extract_text

        return extract_text(file_path)

    else:
        raise ValueError(f"Type de fichier non supporté : {file_path}")
