import gc
import logging
import os

from pypdf import PdfReader
import pdfplumber
from pdf2image import convert_from_path
import pytesseract

logger = logging.getLogger(__name__)

# Lower DPI = smaller images = much less RAM. 150 is good for OCR accuracy.
OCR_DPI = 150


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

    def _poppler_kwargs(self) -> dict:
        kwargs = {}
        raw_path = (os.environ.get("POPPLER_PATH") or "").strip().strip('"').strip("'")
        if raw_path:
            kwargs["poppler_path"] = os.path.normpath(raw_path)
        return kwargs

    def ocr_to_blocks(self, file_path: str):
        """OCR a scanned PDF one page at a time to keep memory low."""
        reader = PdfReader(self.file_path)
        total_pages = len(reader.pages)
        logger.info("OCR: %d pages at %d DPI (processing one at a time)", total_pages, OCR_DPI)

        poppler_kwargs = self._poppler_kwargs()
        blocks = []

        for page_index in range(total_pages):
            page_num = page_index + 1  # 1-based for pdf2image
            logger.info("OCR: page %d/%d", page_num, total_pages)

            images = convert_from_path(
                self.file_path,
                dpi=OCR_DPI,
                first_page=page_num,
                last_page=page_num,
                **poppler_kwargs,
            )
            image = images[0]

            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

            for i, text in enumerate(data["text"]):
                if text.strip():
                    blocks.append({
                        "text": text,
                        "x0": data["left"][i],
                        "top": data["top"][i],
                        "x1": data["left"][i] + data["width"][i],
                        "bottom": data["top"][i] + data["height"][i],
                        "page": page_index,
                    })

            # Free the image immediately so only one page is in memory at a time
            del image, images, data
            gc.collect()

        logger.info("OCR: done, %d blocks extracted", len(blocks))
        return blocks

    def extract_data(self):
        if self.is_scanned(self.file_path):
            blocks = self.ocr_to_blocks(self.file_path)
        else:
            blocks = self.extract_layout(self.file_path)

        tables = self.extract_tables()

        return {
            "blocks": blocks,
            "tables": tables,
        }
    