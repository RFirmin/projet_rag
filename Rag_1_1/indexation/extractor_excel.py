from typing import List, Tuple

import pandas as pd


def extract_excel(excel_path: str) -> Tuple[str, List[Tuple[int, int]]]:
    """
    Extrait un Excel en markdown structuré.
    Chaque feuille devient une section markdown.
    """
    full_text = ""
    sheet_map = []

    xls = pd.ExcelFile(excel_path)
    sheet_names = xls.sheet_names

    print(f"   Nombre de feuilles : {len(sheet_names)}")

    for sheet_index, sheet_name in enumerate(sheet_names, start=1):
        df = pd.read_excel(xls, sheet_name=sheet_name)

        if df.empty:
            print(f"   Feuille '{sheet_name}' vide, ignorée")
            continue

        # Nettoyer les noms de colonnes (Unnamed → Col_N)
        df.columns = [
            f"Col_{i}" if str(c).startswith("Unnamed") else c
            for i, c in enumerate(df.columns)
        ]

        sheet_map.append((len(full_text), sheet_index))

        sheet_md = f"# Feuille : {sheet_name}\n\n"
        sheet_md += f"*{len(df)} lignes × {len(df.columns)} colonnes*\n\n"

        try:
            table_md = df.to_markdown(index=False)
            sheet_md += table_md + "\n\n"
        except Exception as e:
            print(f"   ⚠️ Fallback CSV pour '{sheet_name}' : {e}")
            sheet_md += "```\n" + df.to_csv(index=False) + "```\n\n"

        sheet_md += "---\n\n"
        full_text += sheet_md

        print(f"   Feuille '{sheet_name}' : {len(df)} lignes")

    return full_text, sheet_map
