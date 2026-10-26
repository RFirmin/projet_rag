import cv2
import easyocr
import numpy as np
from PIL import Image

reader = easyocr.Reader(["fr", "en"], gpu=False)


def load_image_to_array(image_file) -> np.ndarray:
    """Convertit n'importe quel format d'entrée en array numpy RGB."""
    if isinstance(image_file, np.ndarray):
        return image_file

    if isinstance(image_file, Image.Image):
        return np.array(image_file.convert("RGB"))

    if isinstance(image_file, str):
        img = Image.open(image_file).convert("RGB")
        return np.array(img)

    if hasattr(image_file, "read"):
        image_file.seek(0)
        img = Image.open(image_file).convert("RGB")
        return np.array(img)

    if isinstance(image_file, bytes):
        from io import BytesIO

        img = Image.open(BytesIO(image_file)).convert("RGB")
        return np.array(img)

    raise ValueError(f"Format d'image non supporté : {type(image_file)}")


def preprocess(img_array: np.ndarray, method: str = "original") -> np.ndarray:
    """Applique un prétraitement à l'image pour améliorer l'OCR."""
    if method == "original":
        return img_array

    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    if method == "grayscale":
        return gray
    elif method == "clahe":
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)
    elif method == "threshold":
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
    elif method == "inverted":
        return cv2.bitwise_not(gray)
    else:
        raise ValueError(f"Méthode inconnue : {method}")


def extract_text_from_image(image_file, preprocessing: str = "original") -> str:
    """Extrait le texte d'une image avec une méthode de prétraitement."""
    img_array = load_image_to_array(image_file)
    processed = preprocess(img_array, preprocessing)
    results = reader.readtext(processed, detail=0)
    return " ".join(results)


def extract_text_with_all_methods(image_file) -> dict:
    """Essaie toutes les méthodes de prétraitement et retourne les résultats."""
    img_array = load_image_to_array(image_file)

    methods = ["original", "grayscale", "clahe", "threshold", "inverted"]
    results = {}

    for method in methods:
        processed = preprocess(img_array, method)
        text_parts = reader.readtext(processed, detail=0)
        results[method] = " ".join(text_parts)

    best = max(results.items(), key=lambda x: len(x[1]))
    results["best_method"] = best[0]
    results["best_text"] = best[1]

    return results
