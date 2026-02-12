# backend/app/api/v1/endpoints/transactions.py

import uuid
import asyncio
from datetime import date
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.core.auth import get_current_user_claims, security_scheme
from app.db.client import get_supabase_client
from app.services.transaction_service import fetch_transactions
from app.models.requests import TransactionUpdate

router = APIRouter(
    prefix="/api/v1/transactions",
    tags=["transactions"],
    dependencies=[Depends(security_scheme)],
)


@router.get("")
async def get_transactions(
    category: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    query: Optional[str] = Query(None, min_length=2),
    claims: Dict = Depends(get_current_user_claims),
    supabase: Client = Depends(get_supabase_client)
) -> List[Dict]:
    """
    Retrieves all transactions for the authenticated user with optional filtering.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    try:
        # Fetch transactions using the service layer
        transactions = await fetch_transactions(
            user_id=user_id,
            supabase=supabase,
            start_date=start_date,
            end_date=end_date,
            category=category
        )

        # Apply text-based search filter if provided
        if query:
            query_lower = query.lower()
            return [
                trx for trx in transactions
                if query_lower in trx.get("cleaned_description", "").lower() or
                query_lower in trx.get("description", "").lower()
            ]

        return transactions
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        raise HTTPException(
            status_code=500, detail="Could not fetch transactions."
        )


@router.patch("/{transaction_id}")
async def update_transaction_category(
    transaction_id: uuid.UUID,
    update_data: TransactionUpdate,
    claims: Dict = Depends(get_current_user_claims),
    supabase: Client = Depends(get_supabase_client)
) -> Dict:
    """
    Updates the category of a transaction.
    Simplified version without encryption complexity.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    try:
        # Update the transaction category
        def sync_update():
            response = (
                supabase.table("transactions")
                .update({"category": update_data.category})
                .eq("id", str(transaction_id))
                .eq("user_id", user_id)
                .execute()
            )
            return response.data

        updated_data = await asyncio.to_thread(sync_update)

        if not updated_data:
            raise HTTPException(
                status_code=404, detail="Transaction not found or could not be updated."
            )

        return updated_data[0]

    except Exception as e:
        print(f"Error updating transaction {transaction_id}: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500, detail="Could not update transaction."
        )
