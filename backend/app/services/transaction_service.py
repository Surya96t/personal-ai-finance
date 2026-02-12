# backend/app/services/transaction_service.py

import asyncio
from datetime import date
from typing import Dict, List, Optional
from supabase import Client


async def fetch_transactions(
    user_id: str,
    supabase: Client,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
) -> List[Dict]:
    """
    Fetches transactions for a user from Supabase.
    Simplified version without encryption (using Supabase native encryption at rest).
    
    Args:
        user_id: The user's ID
        supabase: Supabase client instance
        start_date: Optional start date filter
        end_date: Optional end date filter
        category: Optional category filter
        
    Returns:
        List of transaction dictionaries
    """
    def sync_fetch():
        query_builder = (
            supabase.table("transactions")
            .select("id, date, description, cleaned_description, amount, category")
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

    transactions = await asyncio.to_thread(sync_fetch)
    return transactions
