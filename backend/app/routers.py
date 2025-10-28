# backend/app/routers.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional
from datetime import date, timedelta
from collections import defaultdict
import asyncio

# Import our dependencies and the helper function
from .dependencies import (
    get_supabase_client,
    get_current_user_claims,
    security_scheme,
    fetch_and_decrypt_transactions
)
from supabase import Client

# Create the router
router = APIRouter(
    prefix="/api/v1/dashboard",
    dependencies=[Depends(security_scheme)],
)

# --- /summary endpoint (already correct) ---


@router.get("/summary")
async def get_dashboard_summary(
    start_date: date,
    end_date: date,
    claims: Dict = Depends(get_current_user_claims),
    supabase: Client = Depends(get_supabase_client)
) -> Dict:
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    try:
        transactions = await fetch_and_decrypt_transactions(
            user_id=user_id, supabase=supabase, start_date=start_date, end_date=end_date
        )
        total_spending = sum(trx['amount']
                             for trx in transactions if trx['amount'] < 0)
        total_income = sum(trx['amount']
                           for trx in transactions if trx['amount'] > 0)

        spending_by_category = defaultdict(float)
        for trx in transactions:
            if trx['amount'] < 0:
                spending_by_category[trx.get(
                    "category", "Other")] += trx['amount']

        formatted_spending = [{"category": cat, "total": round(
            total * -1, 2)} for cat, total in spending_by_category.items()]
        formatted_spending.sort(key=lambda x: x['total'], reverse=True)

        return {
            "total_spending": round(total_spending * -1, 2),
            "total_income": round(total_income, 2),
            "spending_by_category": formatted_spending
        }
    except Exception as e:
        print(f"Error calculating dashboard summary: {e}")
        raise HTTPException(
            status_code=500, detail="Could not calculate dashboard summary.")


# --- REFACTORED /cashflow endpoint ---
@router.get("/cashflow")
async def get_cashflow_data(
    start_date: date,
    end_date: date,
    claims: Dict = Depends(get_current_user_claims),
    supabase: Client = Depends(get_supabase_client)
) -> List[Dict]:
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    try:
        transactions = await fetch_and_decrypt_transactions(
            user_id=user_id, supabase=supabase, start_date=start_date, end_date=end_date
        )

        monthly_data = defaultdict(
            lambda: {"total_income": 0.0, "total_spending": 0.0})
        for trx in transactions:
            month_key = date.fromisoformat(
                trx['date']).strftime('%b %Y')  # "Oct 2025"
            amount = float(trx.get("amount", 0))
            if amount > 0:
                monthly_data[month_key]["total_income"] += amount
            else:
                monthly_data[month_key]["total_spending"] += amount

        formatted_cashflow = [
            {"month": month, "total_income": round(
                data["total_income"], 2), "total_spending": round(data["total_spending"] * -1, 2)}
            for month, data in monthly_data.items()
        ]
        # Ensure a consistent sort order by date
        from datetime import datetime
        formatted_cashflow.sort(
            key=lambda x: datetime.strptime(x['month'], '%b %Y'))

        return formatted_cashflow
    except Exception as e:
        print(f"Error fetching cash flow data: {e}")
        raise HTTPException(
            status_code=500, detail="Could not fetch cash flow data.")


# --- REFACTORED /spending-trends endpoint ---
@router.get("/spending-trends")
async def get_spending_trends(
    start_date: date,
    end_date: date,
    claims: Dict = Depends(get_current_user_claims),
    supabase: Client = Depends(get_supabase_client)
) -> List[Dict]:
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    try:
        transactions = await fetch_and_decrypt_transactions(
            user_id=user_id, supabase=supabase, start_date=start_date, end_date=end_date
        )

        daily_spending = defaultdict(float)
        for trx in transactions:
            if trx['amount'] < 0:
                daily_spending[trx['date']] += trx['amount']

        all_days_data = []
        current_date = start_date
        while current_date <= end_date:
            day_key = current_date.isoformat()
            all_days_data.append({
                "date": day_key,
                "total_spending": round(daily_spending.get(day_key, 0) * -1, 2)
            })
            current_date += timedelta(days=1)

        return all_days_data
    except Exception as e:
        print(f"Error fetching spending trends: {e}")
        raise HTTPException(
            status_code=500, detail="Could not fetch spending trends data.")
