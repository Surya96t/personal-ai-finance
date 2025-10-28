# backend/app/dependencies.py

import asyncio
from datetime import date
import os
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from typing import Dict, List, Optional
from supabase import create_client, Client
from clerk_backend_api import Clerk
from clerk_backend_api.security import AuthenticateRequestOptions
from dotenv import load_dotenv

from .encryption_service import decrypt_data

load_dotenv()

# --- Clerk and Security Scheme Initialization ---
clerk_secret_key = os.getenv("CLERK_SECRET_KEY")
if not clerk_secret_key:
    raise ValueError("CLERK_SECRET_KEY is not set.")
clerk_sdk = Clerk(bearer_auth=clerk_secret_key)
security_scheme = HTTPBearer()

# --- Dependency Functions ---


def get_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase keys not set.")
    return create_client(supabase_url, supabase_key)


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


# --- REUSABLE HELPER FUNCTION ---


async def fetch_and_decrypt_transactions(
    user_id: str,
    supabase: Client,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
) -> List[Dict]:
    """
    A reusable helper to fetch transactions from the DB and decrypt them.
    Filtering by date and category is done at the database level for efficiency.
    """
    def sync_fetch_encrypted():
        query_builder = (
            supabase.table("transactions")
            .select("id, date, amount, category, encrypted_data")
            .eq("user_id", user_id)
        )
        if category:
            query_builder = query_builder.eq("category", category)
        if start_date:
            query_builder = query_builder.gte("date", str(start_date))
        if end_date:
            query_builder = query_builder.lte("date", str(end_date))

        response = query_builder.order("date", desc=True).execute()
        return response.data

    encrypted_transactions = await asyncio.to_thread(sync_fetch_encrypted)

    decrypted_transactions = []
    # --- THE FIX IS HERE ---
    for trx in encrypted_transactions:
        # The robust decrypt_data function will handle None.
        decrypted_blob = decrypt_data(trx.get("encrypted_data"))

        # We only add the transaction if decryption produced something.
        if decrypted_blob:
            full_transaction = {
                "id": trx["id"],
                "date": trx["date"],
                "amount": trx["amount"],
                "category": trx["category"],
                **decrypted_blob
            }
            decrypted_transactions.append(full_transaction)
        else:
            # This handles old, unencrypted data. We can decide to log it or ignore it.
            print(
                f"Skipping transaction {trx.get('id')} with no encrypted data.")

    return decrypted_transactions
