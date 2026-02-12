# backend/app/models/requests.py

from pydantic import BaseModel, Field


class DocumentProcessRequest(BaseModel):
    """Request model for processing an uploaded document."""
    file_name: str
    storage_path: str  # Path in Supabase Storage
    file_hash: str


class TransactionUpdate(BaseModel):
    """Request model for updating a transaction."""
    category: str = Field(min_length=1, max_length=100)
