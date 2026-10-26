from typing import List, Tuple

from docx import Document


def extract_word(docx_path: str) -> Tuple[str, List[Tuple[int, int]]]:
    """Extrait un fichier Word en markdown."""
    full_text = ""
    paragraph_map = []

    doc = Document(docx_path)
    paragraph_count = 0

    for para in doc.paragraphs:
        if not para.text.strip():
            continue

        paragraph_count += 1
        paragraph_map.append((len(full_text), paragraph_count))

        style = para.style.name if para.style else ""
        text = para.text.strip()

        if style.startswith("Heading 1") or style == "Title":
            full_text += f"# {text}\n\n"
        elif style.startswith("Heading 2"):
            full_text += f"## {text}\n\n"
        elif style.startswith("Heading 3"):
            full_text += f"### {text}\n\n"
        elif style.startswith("Heading"):
            full_text += f"#### {text}\n\n"
        elif "List" in style:
            full_text += f"- {text}\n"
        else:
            full_text += f"{text}\n\n"

    # Tableaux
    for table in doc.tables:
        paragraph_count += 1
        paragraph_map.append((len(full_text), paragraph_count))
        full_text += _table_to_markdown(table) + "\n\n"

    return full_text, paragraph_map


def _table_to_markdown(table) -> str:
    """Convertit un tableau Word en markdown."""
    rows = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        rows.append(cells)

    if not rows:
        return ""

    md = "| " + " | ".join(rows[0]) + " |\n"
    md += "|" + "|".join(["---"] * len(rows[0])) + "|\n"

    for row in rows[1:]:
        md += "| " + " | ".join(row) + " |\n"

    return md
