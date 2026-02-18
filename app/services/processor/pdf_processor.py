import os

from pypdf import PdfReader
import pdfplumber
from pdf2image import convert_from_path
import pytesseract

class PDFProcessor:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def is_scanned(self, file_path: str) -> bool:
        reader = PdfReader(file_path)
        return not any(page.extract_text() for page in reader.pages)

    def extract_layout(self, file_path: str):
        blocks = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                for word in page.extract_words():
                    word["page"] = page_num
                    blocks.append(word)
        return blocks
    
    def extract_tables(self):
        tables = []
        with pdfplumber.open(self.file_path) as pdf:
            for page in pdf.pages:
                tables += page.extract_tables()
        return tables

    def ocr_to_blocks(self, file_path: str):
        kwargs = {}
        raw_path = (os.environ.get("POPPLER_PATH") or "").strip().strip('"').strip("'")
        if raw_path:
            # Normalize so forward slashes and backslashes work on Windows
            kwargs["poppler_path"] = os.path.normpath(raw_path)
        pages = convert_from_path(self.file_path, **kwargs)
        blocks = []

        for page_index, image in enumerate(pages):
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

            for i, text in enumerate(data["text"]):
                if text.strip():
                    blocks.append({
                        "text": text,
                        "x0": data["left"][i],
                        "top": data["top"][i],
                        "x1": data["left"][i] + data["width"][i],
                        "bottom": data["top"][i] + data["height"][i],
                        "page": page_index
                    })

        return blocks


    def extract_data(self):
        if self.is_scanned(self.file_path):
            blocks = self.ocr_to_blocks(self.file_path)
        else:
            blocks = self.extract_layout(self.file_path)

        tables = self.extract_tables()

        return {
            "blocks": blocks,
            "tables": tables
        }
    