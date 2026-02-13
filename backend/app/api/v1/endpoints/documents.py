# backend/app/api/v1/endpoints/documents.py

import asyncio
import uuid
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.auth import get_current_user_claims, security_scheme
from app.db.client import get_supabase_client
from app.models.requests import DocumentProcessRequest
from app.workflows.client import inngest_client
import inngest

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
    dependencies=[Depends(security_scheme)],
)


@router.post("/generate-upload-url")
async def generate_upload_url(
    claims: Dict = Depends(get_current_user_claims),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Generates a secure, short-lived signed URL for uploading files
    directly to Supabase Storage.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    # Generate a unique filename
    unique_file_name = f"{user_id}/{uuid.uuid4()}.pdf"
    bucket_name = "financial-documents"

    try:
        # Create a signed URL for uploading to Supabase Storage
        # Valid for 15 minutes
        def sync_create_signed_url():
            response = supabase.storage.from_(bucket_name).create_signed_upload_url(
                unique_file_name
            )
            return response

        result = await asyncio.to_thread(sync_create_signed_url)
        
        return {
            "upload_url": result.get("signedUrl", result.get("signedURL")),
            "path": unique_file_name,
            "token": result.get("token")  # Supabase may return a token
        }
    except Exception as e:
        print(f"Error generating signed URL: {e}")
        raise HTTPException(
            status_code=500, detail="Could not generate upload URL."
        )


@router.post("/process")
async def process_document_request(
    request: DocumentProcessRequest,
    claims: Dict = Depends(get_current_user_claims),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Creates a document record in the database and triggers the processing workflow.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    try:
        def sync_insert():
            return supabase.table("documents").insert({
                "user_id": user_id,
                "file_name": request.file_name,
                "storage_path": request.storage_path,
                "status": "UPLOADED",
                "file_hash": request.file_hash,
            }).execute()

        db_response = await asyncio.to_thread(sync_insert)
        
        if not db_response or not getattr(db_response, "data", None) or not isinstance(db_response.data, list) or len(db_response.data) == 0:
            raise ValueError("Database insert returned no data.")
             
        first_record = db_response.data[0]
        if not isinstance(first_record, dict) or "id" not in first_record:
            raise ValueError("Database insert returned invalid record format (missing 'id').")

        document_id = first_record['id']

    except Exception as e:
        if "user_document_hash_unique" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail="This document has already been uploaded."
            )
        print(f"Error creating document record: {e}")
        raise HTTPException(
            status_code=500, detail="Could not create document record."
        )

    # Trigger Inngest workflow with error handling
    try:
        await inngest_client.send(
            inngest.Event(
                name="app/document.uploaded",
                data={
                    "document_id": document_id,
                    "storage_path": request.storage_path,
                }
            )
        )
    except Exception as e:
        print(f"Error sending Inngest event: {e}")
        # Compensating action: Update status to avoid zombie "UPLOADED" state
        try:
            await asyncio.to_thread(
                lambda: supabase.table("documents")
                .update({"status": "EVENT_FAILED", "error_message": f"Failed to trigger workflow: {str(e)}"})
                .eq("id", document_id)
                .execute()
            )
        except Exception as update_error:
            print(f"CRITICAL: Failed to update document status after event failure: {update_error}")
        
        raise HTTPException(
            status_code=500, detail="Document created but processing workflow failed to start."
        )

    return {"status": "processing_queued", "document_id": document_id}


@router.get("")
async def get_recent_documents(
    claims: Dict = Depends(get_current_user_claims),
    supabase: Client = Depends(get_supabase_client)
) -> List[Dict]:
    """
    Retrieves the 5 most recent documents for the authenticated user.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    try:
        def sync_fetch():
            response = (
                supabase.table("documents")
                .select("id, file_name, status, created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            return response.data

        documents = await asyncio.to_thread(sync_fetch)
        return documents

    except Exception as e:
        print(f"Error fetching documents: {e}")
        raise HTTPException(
            status_code=500, detail="Could not fetch documents."
        )
