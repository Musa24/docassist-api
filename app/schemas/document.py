"""Pydantic schemas for Document API responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    """Full document representation for single-resource API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_size: int
    page_count: int
    text_content: str
    summary: str | None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentSummary(BaseModel):
    """Lightweight document representation for list-view endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    status: str
    created_at: datetime
