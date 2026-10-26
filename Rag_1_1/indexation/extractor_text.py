from typing import List, Tuple


def extract_text(txt_path: str) -> Tuple[str, List[Tuple[int, int]]]:
    """Extrait un fichier texte brut."""
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            with open(txt_path, "r", encoding=encoding) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Impossible de lire {txt_path}")

    sheet_map = [(0, 1)]
    return content, sheet_map
