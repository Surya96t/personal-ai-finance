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
from decimal import Decimal, InvalidOperation  # <-- Import Decimal

# --- V-- IMPORT NEW DEPENDENCIES --V ---
from .encryption_service import decrypt_data, decrypt_amount
# from .config import ENCRYPTION_READ_PATH_ENABLED
# --- ^-- IMPORT NEW DEPENDENCIES --^ ---

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


# --- V-- THIS IS THE COMPLETELY REFACTORED HELPER FUNCTION --V ---

async def fetch_and_decrypt_transactions(
    user_id: str,
    supabase: Client,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
) -> List[Dict]:
    """
    A reusable helper to fetch transactions and decrypt them.
    It uses the ENCRYPTION_READ_PATH_ENABLED feature flag to determine
    whether to decrypt the amount or use the plaintext fallback.
    """
    def sync_fetch_encrypted():
        # Select both the old and new amount columns
        query_builder = (
            supabase.table("transactions")
            .select("id, date, category, encrypted_data, amount_encrypted")
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
    decryption_failures = 0

    for trx in encrypted_transactions:
        # Decrypt the main data blob (description, etc.) first
        decrypted_blob = decrypt_data(trx.get("encrypted_data"))
        if not decrypted_blob:
            # Skip records with no main data blob
            continue

        full_transaction = {
            "id": trx["id"],
            "date": trx["date"],
            "category": trx["category"],
            **decrypted_blob
        }

        # --- PERMANENT LOGIC: Decrypt the amount ---
        encrypted_amount_val = trx.get("amount_encrypted")
        if encrypted_amount_val:
            decrypted = decrypt_amount(encrypted_amount_val, user_id)
            if decrypted is not None:
                full_transaction["amount"] = decrypted
                decrypted_transactions.append(full_transaction)
            else:
                print(
                    f"WARN: Decryption failed for trx_id: {trx['id']}. Skipping transaction.")
        else:
            # This case should no longer happen for new data.
            print(
                f"WARN: Missing encrypted amount for trx_id: {trx['id']}. Skipping transaction.")

    return decrypted_transactions
