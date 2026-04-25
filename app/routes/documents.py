"""Document routes: upload + (future) listing/detail/query."""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document
from app.schemas import DocumentResponse
from app.services import PdfExtractionError, extract_text

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)


def _is_pdf(file: UploadFile) -> bool:
    """True if the upload looks like a PDF by content type or extension."""
    if file.content_type == "application/pdf":
        return True
    if file.filename and file.filename.lower().endswith(".pdf"):
        return True
    return False


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Document:
    """Accept a PDF, save it, extract text, persist a Document row."""
    if not _is_pdf(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF.",
        )

    saved_path = UPLOADS_DIR / f"{uuid.uuid4()}.pdf"
    with saved_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    file_size = saved_path.stat().st_size

    try:
        text, page_count = extract_text(saved_path)
    except PdfExtractionError as exc:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse PDF: {exc}",
        ) from exc

    document = Document(
        filename=file.filename or saved_path.name,
        file_size=file_size,
        page_count=page_count,
        text_content=text,
        status="completed",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document
