import tempfile
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from app.auth.dependencies import get_current_user
from app.db.extraction_repository import ExtractionRepository
from app.services.email_service import send_excel_to_user
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

            repo = ExtractionRepository()
            raw_row = None
            try:
                raw_row = repo.insert_raw(
                    file_name=file.filename or "unknown.pdf",
                    document_type=document_type,
                    fields=field_list,
                    llm_model=orchestrator.llm_model,
                    file_content=content,
                )
            except Exception:
                pass  # DB optional: continue without storing raw

            result = orchestrator.extract_data(
                document_type=document_type,
                fields=field_list,
            )

            try:
                raw_id = raw_row.get("id") if raw_row else None
                repo.insert_processed(
                    file_name=file.filename or "unknown.pdf",
                    document_type=document_type,
                    fields=field_list,
                    response=result,
                    llm_model=orchestrator.llm_model,
                    raw_id=raw_id,
                )
            except Exception:
                pass  # DB optional: continue without storing processed

            # Email Excel to the registered user when authenticated and SMTP is configured
            email_sent = False
            email_note = "user_not_authenticated"
            if _user and _user.get("email"):
                excel_path = result.get("excel_path")
                if excel_path:
                    email_sent, email_note = send_excel_to_user(
                        to_email=_user["email"],
                        excel_path=excel_path,
                        subject="Your extraction report",
                        body="Please find your extraction report attached.",
                    )
                else:
                    email_note = "no_excel_path"
            result["email_sent"] = email_sent
            result["email_note"] = email_note

            return result
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        raise HTTPException(500, f"Extraction failed: {str(e)}") from e


class SendEmailBody(BaseModel):
    excel_path: str


@extract_router.post("/send-email")
async def send_extraction_email(
    body: SendEmailBody,
    _user: dict | None = Depends(get_current_user),
):
    """Send the extraction Excel to the authenticated user's email."""
    if not _user or not _user.get("email"):
        raise HTTPException(401, "Sign in to receive the report by email")
    excel_path = body.excel_path.strip()
    if not excel_path or ".." in excel_path or excel_path.startswith("/"):
        raise HTTPException(400, "Invalid path")
    path_obj = Path(excel_path.replace("\\", "/").strip("/"))
    if not path_obj.parts or path_obj.parts[0] != "generated_excel":
        raise HTTPException(400, "Invalid path")
    if not path_obj.exists():
        raise HTTPException(404, "File not found")
    sent, note = send_excel_to_user(
        to_email=_user["email"],
        excel_path=path_obj,
        subject="Your extraction report",
        body="Please find your extraction report attached.",
    )
    return {"sent": sent, "note": note}


@extract_router.get("/excel/download")
async def download_excel(
    path: str,
    _user: dict | None = Depends(get_current_user),
):
    """Download the generated Excel file by path (e.g. from extract result excel_path)."""
    if not path or ".." in path or path.startswith("/"):
        raise HTTPException(400, "Invalid path")
    path_obj = Path(path.replace("\\", "/").strip("/"))
    if not path_obj.parts or path_obj.parts[0] != "generated_excel":
        raise HTTPException(400, "Invalid path")
    if not path_obj.exists():
        raise HTTPException(404, "File not found")
    filename = path_obj.name
    return FileResponse(
        path_obj,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )


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
