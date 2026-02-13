# backend/app/api/v1/endpoints/dashboard.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional
from datetime import date, timedelta
from collections import defaultdict
import asyncio
from decimal import Decimal

# Import our reorganized dependencies
from app.core.auth import get_current_user_claims, security_scheme
from app.db.client import get_supabase_client
from app.services.transaction_service import fetch_transactions
from app.core.cache import cache
from supabase import Client

# Create the router
router = APIRouter(
    prefix="/api/v1/dashboard",
    dependencies=[Depends(security_scheme)],
)

# ==============================================================================
# Endpoint 1: /summary
# ==============================================================================


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

    # --- V-- START OF CACHING LOGIC --V ---
    endpoint_name = "summary"
    cache_params = {"start_date": str(start_date), "end_date": str(end_date)}

    # 1. Check the cache first
    cached_result = cache.get(
        user_id=user_id, endpoint=endpoint_name, params=cache_params)
    if cached_result is not None:
        return cached_result
    # --- ^-- END OF CACHING LOGIC --^ ---

    try:
        # 1. Fetch transactions for the CURRENT period
        current_transactions = await fetch_transactions(
            user_id=user_id, supabase=supabase, start_date=start_date, end_date=end_date
        )

        # 2. Calculate dates for the PREVIOUS period
        period_duration = (end_date - start_date).days
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=period_duration)

        # 3. Fetch transactions for the PREVIOUS period
        previous_transactions = await fetch_transactions(
            user_id=user_id, supabase=supabase, start_date=prev_start_date, end_date=prev_end_date
        )

        # --- V-- START OF MODIFICATION --V ---
        # 4. Perform all calculations in Python using Decimal for precision

        # Calculate metrics for CURRENT period
        current_total_spending = sum(
            Decimal(str(trx.get('amount', 0))) for trx in current_transactions if trx.get('amount', 0) < 0) * -1
        current_total_income = sum(
            Decimal(str(trx.get('amount', 0))) for trx in current_transactions if trx.get('amount', 0) > 0)

        # Calculate transaction counts
        income_transactions_count = sum(
            1 for trx in current_transactions if trx.get('amount', 0) > 0)
        expense_transactions_count = sum(
            1 for trx in current_transactions if trx.get('amount', 0) < 0)
        total_transactions_count = len(current_transactions)

        # Calculate current average daily spending
        num_days_current = period_duration + 1
        average_daily_spending = current_total_spending / \
            Decimal(num_days_current) if num_days_current > 0 else Decimal('0')

        # Calculations for PREVIOUS period
        previous_total_spending = sum(
            Decimal(str(trx.get('amount', 0))) for trx in previous_transactions if trx.get('amount', 0) < 0) * -1
        previous_total_income = sum(
            Decimal(str(trx.get('amount', 0))) for trx in previous_transactions if trx.get('amount', 0) > 0)
        num_days_prev = (prev_end_date - prev_start_date).days + 1
        previous_average_daily_spending = previous_total_spending / \
            Decimal(num_days_prev) if num_days_prev > 0 else Decimal('0')

        # Calculate percentage change for income & spending
        income_change = Decimal('0.0')
        if previous_total_income > 0:
            income_change = (
                (current_total_income - previous_total_income) / previous_total_income) * 100
        spending_change = Decimal('0.0')
        if previous_total_spending > 0:
            spending_change = (
                (current_total_spending - previous_total_spending) / previous_total_spending) * 100
        avg_daily_spending_change = Decimal('0.0')
        if previous_average_daily_spending > 0:
            avg_daily_spending_change = (
                (average_daily_spending - previous_average_daily_spending) / previous_average_daily_spending) * 100

        # Calculate daily spending trend for the sparkline
        daily_spending = defaultdict(Decimal)
        for trx in current_transactions:
            if trx.get('amount', 0) < 0:
                raw_date = trx['date']
                # Normalize date key to string (ISO format) to ensure match with current_date.isoformat()
                date_key = raw_date.isoformat() if hasattr(raw_date, "isoformat") else str(raw_date)
                daily_spending[date_key] += Decimal(str(trx.get('amount', 0)))

        daily_spending_trend = []
        current_date = start_date
        while current_date <= end_date:
            day_key = current_date.isoformat()
            # Convert to float for JSON response
            daily_spending_trend.append({
                "date": day_key,
                "spending": float(round(daily_spending.get(day_key, Decimal('0')) * -1, 2))
            })
            current_date += timedelta(days=1)

        savings_rate = Decimal('0.0')
        if current_total_income > 0:
            savings_rate = (
                (current_total_income - current_total_spending) / current_total_income) * 100

        spending_by_category = defaultdict(Decimal)
        for trx in current_transactions:
            if trx.get('amount', 0) < 0:
                spending_by_category[trx.get(
                    "category", "Other")] += Decimal(str(trx.get('amount', 0)))

        # Convert to float for JSON response
        formatted_spending = [{"category": cat, "total": float(
            round(total * -1, 2))} for cat, total in spending_by_category.items()]
        formatted_spending.sort(key=lambda x: x['total'], reverse=True)

        result_to_cache = {
            "total_spending": float(round(current_total_spending, 2)),
            "total_income": float(round(current_total_income, 2)),
            "spending_by_category": formatted_spending,
            "savings_rate": float(round(savings_rate, 2)),
            "average_daily_spending": float(round(average_daily_spending, 2)),
            "avg_daily_spending_change": float(round(avg_daily_spending_change, 2)),
            "daily_spending_trend": daily_spending_trend,
            "income_change": float(round(income_change, 2)),
            "spending_change": float(round(spending_change, 2)),
            "total_transactions_count": total_transactions_count,
            "income_transactions_count": income_transactions_count,
            "expense_transactions_count": expense_transactions_count,
        }

        cache.set(user_id=user_id, endpoint=endpoint_name,
                  params=cache_params, value=result_to_cache)

        # FINAL STEP: Convert all Decimal results to float for the JSON response
        return result_to_cache
        # --- ^-- END OF MODIFICATION --^ ---
    except Exception as e:
        print(f"Error calculating dashboard summary: {e}")
        raise HTTPException(
            status_code=500, detail="Could not calculate dashboard summary.")


# ==============================================================================
# Endpoint 2: /cashflow
# ==============================================================================

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

    # --- V-- START OF CACHING LOGIC --V ---
    endpoint_name = "cashflow"
    cache_params = {"start_date": str(start_date), "end_date": str(end_date)}

    cached_result = cache.get(
        user_id=user_id, endpoint=endpoint_name, params=cache_params)
    if cached_result is not None:
        return cached_result
    # --- ^-- END OF CACHING LOGIC --^ ---

    try:
        # Step 1: Fetch all decrypted transactions.
        transactions = await fetch_transactions(
            user_id=user_id, supabase=supabase, start_date=start_date, end_date=end_date
        )

        # --- V-- START OF MODIFICATIONS FOR /cashflow --V ---

        # Step 2: Perform GROUP BY aggregation in Python.
        # AGGREGATION: Group transactions by month, summing income and spending.
        monthly_data = defaultdict(
            lambda: {"total_income": Decimal('0.0'), "total_spending": Decimal('0.0')})
        for trx in transactions:
            month_key = date.fromisoformat(trx['date']).strftime(
                '%b %Y')  # e.g., "Oct 2025"
            amount = Decimal(str(trx.get("amount", 0)))
            if amount > 0:
                monthly_data[month_key]["total_income"] += amount
            else:
                monthly_data[month_key]["total_spending"] += amount

        # Step 3: Format the final JSON response, converting all Decimals to floats.
        result_to_cache = [
            {"month": month, "total_income": float(round(
                data["total_income"], 2)), "total_spending": float(round(data["total_spending"] * -1, 2))}
            for month, data in monthly_data.items()
        ]
        from datetime import datetime
        result_to_cache.sort(
            key=lambda x: datetime.strptime(x['month'], '%b %Y'))

        cache.set(user_id=user_id, endpoint=endpoint_name,
                  params=cache_params, value=result_to_cache)

        return result_to_cache
    except Exception as e:
        print(f"Error fetching cash flow data: {e}")
        raise HTTPException(
            status_code=500, detail="Could not fetch cash flow data.")


# ==============================================================================
# Endpoint 3: /spending-trends
# ==============================================================================
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

    endpoint_name = "spending-trends"
    cache_params = {"start_date": str(start_date), "end_date": str(end_date)}
    cached_result = cache.get(
        user_id=user_id, endpoint=endpoint_name, params=cache_params)
    if cached_result is not None:
        return cached_result

    try:
        transactions = await fetch_transactions(
            user_id=user_id, supabase=supabase, start_date=start_date, end_date=end_date
        )
        daily_spending = defaultdict(Decimal)
        for trx in transactions:
            if trx.get('amount', 0) < 0:
                daily_spending[trx['date']] += Decimal(str(trx.get('amount', 0)))

        result_to_cache = []
        current_date = start_date
        while current_date <= end_date:
            day_key = current_date.isoformat()
            result_to_cache.append({
                "date": day_key,
                "total_spending": float(round(daily_spending.get(day_key, Decimal('0')) * -1, 2))
            })
            current_date += timedelta(days=1)

        cache.set(user_id=user_id, endpoint=endpoint_name,
                  params=cache_params, value=result_to_cache)

        return result_to_cache
    except Exception as e:
        print(f"Error fetching spending trends: {e}")
        raise HTTPException(
            status_code=500, detail="Could not fetch spending trends data.")
