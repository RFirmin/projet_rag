import re
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _is_markdown_table_separator(line: str) -> bool:
    """Vérifie si une ligne est un séparateur de tableau markdown."""
    stripped = line.strip()
    return stripped.startswith("|") and "---" in stripped and stripped.endswith("|")


def _split_table_row(line: str) -> list:
    """Découpe une ligne de tableau markdown en cellules."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _markdown_to_reportlab_text(text: str) -> str:
    """Convertit le markdown inline basique en balises ReportLab."""
    # Échapper les caractères spéciaux de ReportLab
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Convertir **gras** en <b>gras</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Convertir *italique* en <i>italique</i>
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    return text


def markdown_to_pdf_bytes(markdown_content: str, title: str = "Document") -> bytes:
    """
    Convertit une chaîne Markdown en PDF (sous forme de bytes).

    Args:
        markdown_content: Le contenu Markdown à convertir
        title: Le titre du document

    Returns:
        Les bytes du fichier PDF généré
    """
    buffer = BytesIO()

    # Configuration des styles
    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=5,
    )
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        spaceAfter=10,
    )
    heading1_style = ParagraphStyle(
        "ReportHeading1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        spaceBefore=10,
        spaceAfter=6,
    )
    heading2_style = ParagraphStyle(
        "ReportHeading2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        spaceBefore=7,
        spaceAfter=4,
    )
    table_header_style = ParagraphStyle(
        "ReportTableHeader",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
    )
    table_cell_style = ParagraphStyle(
        "ReportTableCell",
        parent=body_style,
        fontSize=8.5,
        leading=11,
    )

    # Création du document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    story = []
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 10))

    # État pour le parsing
    list_items = []
    list_type = "bullet"  # ou "ordered"
    table_rows = []
    in_code_block = False
    code_lines = []

    def flush_list():
        nonlocal list_items
        if list_items:
            story.append(
                ListFlowable(
                    [
                        ListItem(
                            Paragraph(_markdown_to_reportlab_text(item), body_style)
                        )
                        for item in list_items
                    ],
                    bulletType=list_type,
                    bulletFontName="Helvetica",
                    bulletFontSize=7 if list_type == "bullet" else 9,
                    leftIndent=16,
                    bulletIndent=4,
                    itemSpace=3,
                )
            )
            story.append(Spacer(1, 6))
            list_items = []

    def flush_table():
        nonlocal table_rows
        if not table_rows:
            return

        # Ignorer le séparateur (2e ligne)
        if len(table_rows) >= 2 and _is_markdown_table_separator(table_rows[1]):
            rows = [table_rows[0], *table_rows[2:]]
            data = []
            for row_index, row in enumerate(rows):
                style = table_header_style if row_index == 0 else table_cell_style
                data.append(
                    [
                        Paragraph(_markdown_to_reportlab_text(cell), style)
                        for cell in _split_table_row(row)
                    ]
                )

            if data:
                col_count = max(len(row) for row in data)
                for row in data:
                    row.extend(
                        [
                            Paragraph("", table_cell_style)
                            for _ in range(col_count - len(row))
                        ]
                    )

                table = Table(data, repeatRows=1)
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                            (
                                "GRID",
                                (0, 0),
                                (-1, -1),
                                0.35,
                                colors.HexColor("#cbd5e1"),
                            ),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 4),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                            ("TOPPADDING", (0, 0), (-1, -1), 3),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ]
                    )
                )
                story.append(table)
                story.append(Spacer(1, 8))
        table_rows = []

    # Parser ligne par ligne
    for line in markdown_content.split("\n"):
        stripped = line.strip()

        # Blocs de code
        if stripped.startswith("```"):
            if in_code_block:
                # Fin du bloc
                story.append(
                    Paragraph(
                        f'<font face="Courier">{chr(10).join(code_lines)}</font>',
                        body_style,
                    )
                )
                story.append(Spacer(1, 6))
                code_lines = []
                in_code_block = False
            else:
                flush_list()
                flush_table()
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        # Lignes vides
        if not stripped:
            flush_list()
            flush_table()
            continue

        # Tableaux
        if stripped.startswith("|"):
            flush_list()
            table_rows.append(stripped)
            continue
        else:
            if table_rows:
                flush_table()

        # Titres
        if stripped.startswith("#"):
            flush_list()
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped.lstrip("#").strip()
            if level == 1:
                story.append(Paragraph(text, heading1_style))
            elif level == 2:
                story.append(Paragraph(text, heading2_style))
            else:
                story.append(Paragraph(text, body_style))
            continue

        # Listes
        if stripped.startswith("- ") or stripped.startswith("* "):
            list_items.append(stripped[2:])
            list_type = "bullet"
            continue
        elif re.match(r"^\d+\.\s", stripped):
            list_items.append(re.sub(r"^\d+\.\s", "", stripped))
            list_type = "ordered"
            continue
        else:
            if list_items:
                flush_list()

        # Paragraphe normal
        story.append(Paragraph(_markdown_to_reportlab_text(stripped), body_style))

    # Nettoyage final
    flush_list()
    flush_table()

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def convert_md_file_to_pdf(input_md_path: str, output_pdf_path: str, title: str = None):
    """Convertit un fichier Markdown en PDF."""
    with open(input_md_path, "r", encoding="utf-8") as f:
        content = f.read()

    if title is None:
        title = Path(input_md_path).stem

    pdf_bytes = markdown_to_pdf_bytes(content, title)

    with open(output_pdf_path, "wb") as f:
        f.write(pdf_bytes)

    print(f"✅ PDF généré : {output_pdf_path}")


if __name__ == "__main__":
    # Exemple d'utilisation
    convert_md_file_to_pdf(
        input_md_path="books_to_index/guide_canal_plus.md",
        output_pdf_path="books_to_index/guide_canal_plus.pdf",
        title="Guide des Chaînes Canal+",
    )
