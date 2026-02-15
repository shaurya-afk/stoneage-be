import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.auth.dependencies import get_current_user
from app.db.extraction_repository import ExtractionRepository
from app.services.extraction.orchestrator import ExtractionOrchestrator

extract_router = APIRouter(prefix="/extract", tags=["extract"])


@extract_router.post("")
async def extract(
    _user: dict | None = Depends(get_current_user),
    file: UploadFile = File(..., description="PDF document to extract data from"),
    document_type: str = Form("invoice", description="Document type (e.g. invoice, receipt)"),
    fields: str = Form(
        "invoice_number,invoice_date,total_amount",
        description="Comma-separated field names to extract",
    ),
):
    """
    Extract structured data from a PDF document.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "File must be a PDF")

    try:
        suffix = Path(file.filename).suffix or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            orchestrator = ExtractionOrchestrator(tmp_path)
            field_list = [f.strip() for f in fields.split(",") if f.strip()]
            field_list = field_list or ["invoice_number", "invoice_date", "total_amount"]

            # Store raw input (including full PDF)
            repo = ExtractionRepository()
            raw_row = repo.insert_raw(
                file_name=file.filename or "unknown.pdf",
                document_type=document_type,
                fields=field_list,
                llm_model=orchestrator.llm_model,
                file_content=content,
            )

            result = orchestrator.extract_data(
                document_type=document_type,
                fields=field_list,
            )

            # Store processed result
            raw_id = raw_row.get("id") if raw_row else None
            repo.insert_processed(
                file_name=file.filename or "unknown.pdf",
                document_type=document_type,
                fields=field_list,
                response=result,
                llm_model=orchestrator.llm_model,
                raw_id=raw_id,
            )

            return result
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        raise HTTPException(500, f"Extraction failed: {str(e)}") from e


@extract_router.get("/{raw_id}/download")
async def download_raw_pdf(
    raw_id: UUID,
    _user: dict | None = Depends(get_current_user),
):
    """Download the stored PDF for a raw extraction record."""
    repo = ExtractionRepository()
    result = repo.get_raw_file(raw_id)
    if not result:
        raise HTTPException(404, "File not found or not stored")
    content, filename = result
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
