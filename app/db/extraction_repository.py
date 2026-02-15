import logging
import uuid
from typing import Any

from .database import get_db, is_configured
from .models import ExtractionProcessed, ExtractionRaw

logger = logging.getLogger(__name__)


def _sanitize_for_jsonb(obj: Any) -> Any:
    """Remove null bytes from strings - PostgreSQL JSONB rejects \\u0000."""
    if isinstance(obj, str):
        return obj.replace("\x00", "")
    if isinstance(obj, dict):
        return {k: _sanitize_for_jsonb(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_jsonb(v) for v in obj]
    return obj


class ExtractionRepository:
    """Repository for extraction records using SQLAlchemy ORM."""

    def insert_raw(
        self,
        file_name: str,
        document_type: str,
        fields: list[str],
        llm_model: str,
        file_content: bytes | None = None,
    ) -> dict[str, Any] | None:
        """Store raw extraction input. Returns inserted row dict or None if DB is not configured."""
        if not is_configured():
            return None
        try:
            with get_db() as session:
                if not session:
                    return None
                row = ExtractionRaw(
                    file_name=_sanitize_for_jsonb(file_name),
                    file_content=file_content,
                    document_type=_sanitize_for_jsonb(document_type),
                    fields=_sanitize_for_jsonb(fields),
                    llm_model=_sanitize_for_jsonb(llm_model),
                )
                session.add(row)
                session.flush()
                return {"id": str(row.id), "created_at": row.created_at}
        except Exception as e:
            logger.exception("insert_raw failed: %s", e)
            return None

    def insert_processed(
        self,
        file_name: str,
        document_type: str,
        fields: list[str],
        response: dict[str, Any],
        llm_model: str,
        raw_id: str | uuid.UUID | None = None,
    ) -> dict[str, Any] | None:
        """Store processed extraction result. Returns inserted row dict or None if DB is not configured."""
        if not is_configured():
            return None
        try:
            with get_db() as session:
                if not session:
                    return None
                parsed_raw_id = uuid.UUID(str(raw_id)) if raw_id else None
                row = ExtractionProcessed(
                    file_name=_sanitize_for_jsonb(file_name),
                    document_type=_sanitize_for_jsonb(document_type),
                    fields=_sanitize_for_jsonb(fields),
                    response=_sanitize_for_jsonb(response),
                    llm_model=_sanitize_for_jsonb(llm_model),
                    raw_id=parsed_raw_id,
                )
                session.add(row)
                session.flush()
                return {"id": str(row.id), "created_at": row.created_at}
        except Exception as e:
            logger.exception("insert_processed failed: %s", e)
            return None

    def get_raw_file(self, raw_id: str | uuid.UUID) -> tuple[bytes, str] | None:
        """Get stored PDF content and filename by raw record id. Returns (content, filename) or None."""
        if not is_configured():
            return None
        try:
            with get_db() as session:
                if not session:
                    return None
                parsed_id = uuid.UUID(str(raw_id))
                row = session.query(ExtractionRaw).filter(ExtractionRaw.id == parsed_id).first()
                if not row or not row.file_content:
                    return None
                return (bytes(row.file_content), row.file_name or "document.pdf")
        except Exception as e:
            logger.exception("get_raw_file failed: %s", e)
            return None
