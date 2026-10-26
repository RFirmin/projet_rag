from pathlib import Path
from typing import List, Tuple

import pandas as pd


def extract_csv(csv_path: str) -> Tuple[str, List[Tuple[int, int]]]:
    """Extrait un CSV en markdown."""
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(csv_path, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Impossible de lire {csv_path}")

    full_text = f"# Fichier : {Path(csv_path).name}\n\n"
    full_text += f"*{len(df)} lignes × {len(df.columns)} colonnes*\n\n"

    try:
        full_text += df.to_markdown(index=False)
    except Exception:
        full_text += "```\n" + df.to_csv(index=False) + "```"

    sheet_map = [(0, 1)]
    return full_text, sheet_map
