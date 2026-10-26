import time
from typing import List, Tuple

import pymupdf
import pymupdf4llm
import typer


def extract_pdf(pdf_path: str) -> Tuple[str, List[Tuple[int, int]]]:
    """Extrait un PDF en markdown avec table des pages."""
    full_text = ""
    page_map = []

    with pymupdf.open(pdf_path) as doc:
        total_pages = doc.page_count

        for page_num in range(total_pages):
            page_text = pymupdf4llm.to_markdown(pdf_path, pages=[page_num])

            if page_text.strip():
                page_map.append((len(full_text), page_num + 1))
                full_text += page_text + "\n\n"

            if (page_num + 1) % 10 == 0 or (page_num + 1) == total_pages:
                print(f"   Page {page_num + 1}/{total_pages}")

    return full_text, page_map


def extract_pdf_with_progression(pdf_path: str) -> Tuple[str, List[Tuple[int, int]]]:
    """Extrait un PDF en markdown avec table des pages en affichant la barre de progression."""
    full_text = ""
    page_map = []

    with pymupdf.open(pdf_path) as doc:
        total_pages = doc.page_count

        with typer.progressbar(
            range(total_pages), label="Extraction des pages"
        ) as progress:
            for page_num in progress:
                time.sleep(0.1)  # Simuler un délai pour la progression

                page_text = pymupdf4llm.to_markdown(pdf_path, pages=[page_num])

                if page_text.strip():
                    page_map.append((len(full_text), page_num + 1))
                    full_text += page_text + "\n\n"

                if (page_num + 1) % 10 == 0 or (page_num + 1) == total_pages:
                    print(f"   Page {page_num + 1}/{total_pages}")

    return full_text, page_map
