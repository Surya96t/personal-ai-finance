import os
import uuid
import asyncio
from datetime import timedelta, date  # <-- Import date
from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from clerk_backend_api import Clerk
from clerk_backend_api.security import AuthenticateRequestOptions
from google.cloud import storage
from dotenv import load_dotenv
from typing import Dict, List, Optional  # <-- Import List and Optional
from pydantic import BaseModel, Field
import inngest
import inngest.fast_api
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Import our new clients and the Inngest server
from .clients import inngest_client, supabase
from .inngest_functions import (
    process_document_uploaded,
    perform_ocr_on_document,
    isolate_transaction_lines,
    structure_transaction_data,
    enrich_and_categorize_transactions,
)

# --- Initialization ---
load_dotenv()
clerk_secret_key = os.getenv("CLERK_SECRET_KEY")
if not clerk_secret_key:
    raise ValueError("CLERK_SECRET_KEY is not set in the environment.")
clerk_sdk = Clerk(bearer_auth=clerk_secret_key)
app = FastAPI(title="Personal AI Finance Planner API")

# --- NEW EXCEPTION HANDLER FOR DEBUGGING ---


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Log detailed validation errors to the console.
    """
    print(f"Caught validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


storage_client = storage.Client()
bucket_name = os.getenv("GCP_BUCKET_NAME")  # Use env var for bucket name


origins = [
    "http://localhost:3000",
    # We will add our production frontend URL here later
    # "https://your-production-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # Important for allowing cookies and auth headers
    allow_methods=["*"],    # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],    # Allow all headers (like Authorization)
)


# --- THIS IS THE KEY PART FOR THE DOCS UI ---
# Define the security scheme.
# This object's only job is to tell the /docs page how to create the "Authorize" button.
# The tokenUrl is a required dummy value and is not actually used.
security_scheme = HTTPBearer()

# Google Cloud Storage Client
storage_client = storage.Client()
# IMPORTANT: Replace with your actual bucket name!
bucket_name = "personal-ai-finance-uploads-01"

# --- 2. FastAPI Dependency for Authentication ---
# This function remains the same. It's the real security guard.


async def get_current_user_claims(req: Request) -> Dict:
    options = AuthenticateRequestOptions()
    try:
        request_state = clerk_sdk.authenticate_request(req, options)
        if not request_state.is_signed_in:
            raise HTTPException(
                status_code=401, detail="Unauthorized: Not signed in")
        return request_state.payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Unauthorized: {str(e)}")


# --- Pydantic Models for Request Bodies ---
class DocumentProcessRequest(BaseModel):
    file_name: str
    gcs_path: str
    file_hash: str

# --- NEW PYDANTIC MODEL for the PATCH request body ---


class TransactionUpdate(BaseModel):
    category: str = Field(min_length=1, max_length=100)

# --- 3. API Endpoints ---

# Health Check Endpoint


@app.get("/")
def read_root():
    return {"Status": "API is running"}


# --- MODIFIED ENDPOINT with security dependency for docs ---
@app.post("/api/v1/documents/generate-upload-url", dependencies=[Depends(security_scheme)])
def generate_upload_url(claims: Dict = Depends(get_current_user_claims)):
    """
    This is a protected endpoint.
    It generates a secure, short-lived URL for a client to upload a file
    directly to Google Cloud Storage.
    """
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


# --- NEW ENDPOINT: Get Transactions ---
@app.get("/api/v1/transactions", dependencies=[Depends(security_scheme)])
async def get_transactions(
    category: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    query: Optional[str] = Query(None, min_length=2),
    claims: Dict = Depends(get_current_user_claims)
) -> List[Dict]:
    """
    Retrieves all transactions for the authenticated user, with optional filtering.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401, detail="User ID not found in token")

    try:
        def sync_fetch():
            # Start with a base query
            query_builder = supabase.table(
                "transactions").select("*").eq("user_id", user_id)

            # Dynamically add filters if they are provided
            if category:
                query_builder = query_builder.eq("category", category)
            if start_date:
                query_builder = query_builder.gte("date", str(start_date))
            if end_date:
                query_builder = query_builder.lte("date", str(end_date))
            if query:
                # Use 'ilike' for case-insensitive text search
                query_builder = query_builder.ilike(
                    "cleaned_description", f"%{query}%")

            # Execute the final query, ordered by most recent date
            response = query_builder.order("date", desc=True).execute()
            return response.data

        transactions = await asyncio.to_thread(sync_fetch)
        return transactions

    except Exception as e:
        print(f"Error fetching transactions: {e}")
        raise HTTPException(
            status_code=500, detail="Could not fetch transactions.")


# --- THIS IS THE NEW ENDPOINT ---
@app.patch("/api/v1/transactions/{transaction_id}", dependencies=[Depends(security_scheme)])
async def update_transaction_category(
    transaction_id: uuid.UUID,
    update_data: TransactionUpdate,
    claims: Dict = Depends(get_current_user_claims)
) -> Dict:
    """
    Updates the category of a specific transaction for the authenticated user.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401, detail="User ID not found in token")

    try:
        def sync_update():
            # This query is the core of the security. It ensures a user can ONLY
            # update a transaction that has both the correct transaction_id AND their user_id.
            response = (
                supabase.table("transactions")
                .update({"category": update_data.category})
                .eq("id", str(transaction_id))
                .eq("user_id", user_id)
                .execute()
            )
            return response.data

        updated_data = await asyncio.to_thread(sync_update)

        # If the returned data list is empty, it means no row was found that matched
        # both the transaction_id and the user_id.
        if not updated_data:
            raise HTTPException(
                status_code=404, detail="Transaction not found or you do not have permission to update it.")

        return updated_data[0]

    except Exception as e:
        # Avoid leaking detailed database errors in production
        print(f"Error updating transaction {transaction_id}: {e}")
        # Check if it's the specific 404 we raised, otherwise return a generic 500
        if isinstance(e, HTTPException) and e.status_code == 404:
            raise e
        raise HTTPException(
            status_code=500, detail="Could not update transaction.")


# --- NEW ENDPOINT: Get Dashboard Summary ---
@app.get("/api/v1/dashboard/summary", dependencies=[Depends(security_scheme)])
async def get_dashboard_summary(
    start_date: date,
    end_date: date,
    claims: Dict = Depends(get_current_user_claims)
) -> Dict:
    """
    Retrieves aggregated summary data for the user's dashboard for a given date range.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401, detail="User ID not found in token")

    try:
        def sync_rpc_call():
            # Define the parameters for our PostgreSQL function
            params = {
                'p_user_id': user_id,
                'p_start_date': str(start_date),
                'p_end_date': str(end_date)
            }
            # Use .rpc() to call the database function by name
            # The Postgrest API that Supabase uses is smart enough to map the keys
            # to the correct named parameters in the function.
            response = supabase.rpc('get_dashboard_summary', params).execute()

            # The error message indicates a schema cache issue.
            # While Supabase usually auto-updates its schema, if this error persists,
            # it might be a temporary desync. This is a rare case.
            # The most likely fix is re-running the SQL function creation.

            return response.data

        summary_data = await asyncio.to_thread(sync_rpc_call)

        if not summary_data:
            return {"total_spending": 0, "total_income": 0, "spending_by_category": []}

        # The function returns a single JSON object which is the first element in the data list
        return summary_data[0] if isinstance(summary_data, list) and len(summary_data) > 0 else summary_data

    except Exception as e:
        print(f"Error fetching dashboard summary: {e}")
        raise HTTPException(
            status_code=500, detail="Could not fetch dashboard summary.")


# --- NEW ENDPOINT: Get Recent Documents ---
@app.get("/api/v1/documents", dependencies=[Depends(security_scheme)])
async def get_recent_documents(claims: Dict = Depends(get_current_user_claims)) -> List[Dict]:
    """
    Retrieves the 5 most recent documents for the authenticated user.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401, detail="User ID not found in token")

    try:
        def sync_fetch():
            response = (
                supabase.table("documents")
                # Select only the fields we need
                .select("id, file_name, status, created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)  # Most recent first
                .limit(5)  # Limit to the last 5
                .execute()
            )
            return response.data

        documents = await asyncio.to_thread(sync_fetch)
        return documents

    except Exception as e:
        print(f"Error fetching documents: {e}")
        raise HTTPException(
            status_code=500, detail="Could not fetch documents.")


# --- Register Inngest with FastAPI ---
inngest.fast_api.serve(app, inngest_client, [
    process_document_uploaded,
    perform_ocr_on_document,
    isolate_transaction_lines,
    structure_transaction_data,
    enrich_and_categorize_transactions,
])
