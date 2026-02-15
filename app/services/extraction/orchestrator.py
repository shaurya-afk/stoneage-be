from app.services.extraction.formatter import DocumentFormatter
from app.services.extraction.llm import LLMProcessor
from app.services.processor.pdf_processor import PDFProcessor
from app.utils.excel import ExcelGenerator


class ExtractionOrchestrator:
    def __init__(self, file_path: str):
        self.pdf_processor = PDFProcessor(file_path)
        self.formatter = DocumentFormatter()
        self.llm_processor = LLMProcessor()
        self.excel_generator = ExcelGenerator()

    @property
    def llm_model(self) -> str:
        return self.llm_processor.model

    def extract_data(
        self,
        document_type: str = "invoice",
        fields: list[str] | None = None,
    ):
        fields = fields or ["invoice_number", "invoice_date", "total_amount"]
        data = self.pdf_processor.extract_data()
        text, hints = self.formatter.format_document(data["blocks"])
        if data.get("tables"):
            table_text = self._tables_to_text(data["tables"])
            if table_text:
                text = f"{text}\n\n{table_text}"
        # TODO: LLM extraction temporarily disabled
        # result = self.llm_processor.extract(
        #     document_type=document_type,
        #     fields=fields,
        #     text=text,
        #     hints=hints,
        # )
        # return result
        result = {f: None for f in fields}
        excel_path = self.excel_generator.create_excel(result)
        return {**result, "excel_path": str(excel_path)}

    def _tables_to_text(self, tables: list) -> str:
        parts = []
        for i, table in enumerate(tables):
            if not table:
                continue
            parts.append(f"\n[Table {i + 1}]")
            for row in table:
                if row:
                    parts.append(" | ".join(str(c) if c is not None else "" for c in row))
        return "\n".join(parts) if parts else ""