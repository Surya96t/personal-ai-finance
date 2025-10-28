# backend/app/main.py

import os
import uuid
import asyncio
from datetime import timedelta, date
from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage  # Import the library
from dotenv import load_dotenv
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import inngest
import inngest.fast_api
from supabase import Client

from .encryption_service import decrypt_data, encrypt_data

# Import from our new dependency file
from .dependencies import (
    get_supabase_client,
    get_current_user_claims,
    security_scheme,
    fetch_and_decrypt_transactions
)
from .routers import router as dashboard_router
from .clients import inngest_client
from .inngest_functions import (
    process_document_uploaded, perform_ocr_on_document, isolate_transaction_lines,
    structure_transaction_data, enrich_and_categorize_transactions,
)

# --- Initialization ---
load_dotenv()
app = FastAPI(title="Personal AI Finance Planner API")
app.add_middleware(CORSMiddleware, allow_origins=[
                   "http://localhost:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- LAZY INITIALIZATION FOR GOOGLE CLOUD STORAGE CLIENT ---
_storage_client = None


def get_storage_client():
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client

# --- Pydantic Models ---


class DocumentProcessRequest(BaseModel):
    file_name: str
    gcs_path: str
    file_hash: str


class TransactionUpdate(BaseModel):
    category: str = Field(min_length=1, max_length=100)

# --- API Endpoints ---


@app.get("/")
def read_root():
    return {"Status": "API is running"}

# --- THIS IS THE FULL, CORRECTED generate-upload-url ENDPOINT ---


@app.post("/api/v1/documents/generate-upload-url", dependencies=[Depends(security_scheme)])
def generate_upload_url(claims: Dict = Depends(get_current_user_claims)):
    """
    Generates a secure, short-lived URL for a client to upload a file
    directly to Google Cloud Storage.
    """
    storage_client = get_storage_client()  # <-- Initialize lazily
    bucket_name = os.getenv("GCP_BUCKET_NAME")

    if not bucket_name:
        raise HTTPException(
            status_code=500, detail="Bucket name not configured on server.")

    unique_file_name = f"{uuid.uuid4()}.pdf"

    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(unique_file_name)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="PUT",
            content_type="application/pdf",
        )
        return {"upload_url": url, "gcs_path": unique_file_name}
    except Exception as e:
        print(f"Error generating signed URL: {e}")
        raise HTTPException(
            status_code=500, detail="Could not generate upload URL.")


@app.post("/api/v1/documents/process", dependencies=[Depends(security_scheme)])
async def process_document_request(  # <-- Changed to async def
    request: DocumentProcessRequest,
    claims: Dict = Depends(get_current_user_claims)
):
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401, detail="User ID not found in token")

    # 1. Create a record in our database.
    # Because this function is now async, we must wrap the sync Supabase call.
    try:
        def sync_insert():
            supabase = get_supabase_client()
            return supabase.table("documents").insert({
                "user_id": user_id,
                "file_name": request.file_name,
                "gcs_path": request.gcs_path,
                "status": "UPLOADED",
                "file_hash": request.file_hash,
            }).execute()

        db_response = await asyncio.to_thread(sync_insert)
        document_id = db_response.data[0]['id']

    except Exception as e:
        if "user_document_hash_unique" in str(e).lower():
            raise HTTPException(
                status_code=409, detail="This document has already been uploaded.")
        print(f"Error creating document record: {e}")
        raise HTTPException(
            status_code=500, detail="Could not create document record.")

    # 2. Send the event to Inngest, now correctly awaited.
    await inngest_client.send(  # <-- Added await
        inngest.Event(
            name="app/document.uploaded",
            data={
                "document_id": document_id,
                "gcs_path": request.gcs_path,
            }
        )
    )

    return {"status": "processing_queued", "document_id": document_id}


# --- THIS IS THE FULL, REFACTORED /transactions ENDPOINT ---
@app.get("/api/v1/transactions", dependencies=[Depends(security_scheme)])
async def get_transactions(
    category: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    query: Optional[str] = Query(None, min_length=2),
    claims: Dict = Depends(get_current_user_claims),
    supabase: Client = Depends(get_supabase_client)
) -> List[Dict]:
    """
    Retrieves all transactions for the authenticated user, decrypts them,
    and then applies filtering in Python.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    try:
        # 1. Call the reusable helper to get all decrypted transactions
        decrypted_transactions = await fetch_and_decrypt_transactions(
            user_id=user_id,
            supabase=supabase,
            start_date=start_date,
            end_date=end_date,
            category=category
        )

        # 2. Apply text-based search filter in Python (if provided)
        if query:
            query_lower = query.lower()
            return [
                trx for trx in decrypted_transactions
                if query_lower in trx.get("cleaned_description", "").lower() or
                query_lower in trx.get("description", "").lower()
            ]

        return decrypted_transactions
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        raise HTTPException(
            status_code=500, detail="Could not fetch transactions.")


# --- THIS IS THE FULL, REFACTORED /transactions/{id} ENDPOINT ---
@app.patch("/api/v1/transactions/{transaction_id}", dependencies=[Depends(security_scheme)])
async def update_transaction_category(
    transaction_id: uuid.UUID,
    update_data: TransactionUpdate,
    claims: Dict = Depends(get_current_user_claims),
    supabase: Client = Depends(get_supabase_client)
) -> Dict:
    """
    Performs a secure Read-Modify-Write operation to update an encrypted transaction's category.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    try:
        # 1. FETCH the existing record securely
        def sync_fetch_one():
            response = (
                supabase.table("transactions")
                .select("id, encrypted_data")
                .eq("id", str(transaction_id))
                .eq("user_id", user_id)
                .single()  # Expect exactly one result or raise an error
                .execute()
            )
            return response.data

        encrypted_record = await asyncio.to_thread(sync_fetch_one)
        if not encrypted_record:
            raise HTTPException(
                status_code=404, detail="Transaction not found.")

        # 2. DECRYPT the data
        decrypted_data = decrypt_data(encrypted_record["encrypted_data"])

        # 3. MODIFY the decrypted data in Python
        decrypted_data["category"] = update_data.category

        # 4. RE-ENCRYPT the entire modified object
        new_encrypted_blob = encrypt_data(decrypted_data)

        # 5. WRITE the new encrypted data back to the database

        def sync_update():
            response = (
                supabase.table("transactions")
                .update({
                    "encrypted_data": new_encrypted_blob,
                    "category": update_data.category  # Also update the plaintext column
                })
                .eq("id", str(transaction_id))
                .eq("user_id", user_id)
                .execute()
            )
            return response.data

        updated_data = await asyncio.to_thread(sync_update)

        if not updated_data:
            # This would be a very rare race condition, but it's good practice to check.
            raise HTTPException(
                status_code=404, detail="Transaction could not be updated.")

        # 6. RETURN the fully updated (but still decrypted) object to the frontend
        return {**decrypted_data, "id": str(transaction_id)}

    except Exception as e:
        print(f"Error updating transaction {transaction_id}: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500, detail="Could not update transaction.")


# --- THIS IS THE CORRECTED ENDPOINT ---
@app.get("/api/v1/documents", dependencies=[Depends(security_scheme)])
async def get_recent_documents(
    claims: Dict = Depends(get_current_user_claims),
    # <-- THE FIX: Add the dependency
    supabase: Client = Depends(get_supabase_client)
) -> List[Dict]:
    """
    Retrieves the 5 most recent documents for the authenticated user.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401, detail="User ID not found in token")

    try:
        def sync_fetch():
            # Now uses the 'supabase' client passed into the function
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
            status_code=500, detail="Could not fetch documents.")


app.include_router(dashboard_router)

# --- Register Inngest with FastAPI ---
inngest.fast_api.serve(app, inngest_client, [
    process_document_uploaded,
    perform_ocr_on_document,
    isolate_transaction_lines,
    structure_transaction_data,
    enrich_and_categorize_transactions,
])
