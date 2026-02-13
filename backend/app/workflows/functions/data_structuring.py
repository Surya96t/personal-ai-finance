import asyncio
import logging
import inngest
from app.workflows.client import inngest_client
from app.db.client import get_supabase_client
from app.integrations.openai import structure_transactions
from app.cache_service import cache

logger = logging.getLogger(__name__)

@inngest_client.create_function(
    fn_id="ai-structure-transaction-data",
    trigger=inngest.TriggerEvent(event="ai/transaction_lines.isolated"),
    retries=2,
)
async def structure_transaction_data(ctx: inngest.Context) -> dict:
    document_id = ctx.event.data.get("document_id")
    
    if not document_id:
        logger.error(f"Missing document_id in event data: {ctx.event.data}")
        return {"status": "failed", "error": "Missing document_id"}

    # 1. Update status
    async def update_status() -> None:
        supabase = get_supabase_client()
        await asyncio.to_thread(
            lambda: supabase.table("documents")
            .update({"status": "PROCESSING_STRUCTURING"})
            .eq("id", document_id)
            .execute()
        )
    await ctx.step.run("update-status-to-structuring", update_status)

    # 2. Get transaction lines and user_id
    async def get_doc_data() -> dict:
        supabase = get_supabase_client()
        def sync_get():
            response = supabase.table("documents").select("transaction_lines_text", "user_id").eq("id", document_id).single().execute()
            if not response.data:
                raise ValueError(f"Document not found: {document_id}")
            if not response.data.get("transaction_lines_text"):
                return {"transaction_lines_text": "", "user_id": response.data.get("user_id")}
            return response.data
        return await asyncio.to_thread(sync_get)

    doc_data = await ctx.step.run("get-data-from-db", get_doc_data)
    lines_text = doc_data["transaction_lines_text"]
    user_id = doc_data.get("user_id")

    if not lines_text:
        # Update status to a terminal state before returning
        async def update_status_no_data() -> None:
            supabase = get_supabase_client()
            await asyncio.to_thread(
                lambda: supabase.table("documents")
                .update({"status": "COMPLETED_NO_DATA"})
                .eq("id", document_id)
                .execute()
            )
        await ctx.step.run("update-status-to-no-data", update_status_no_data)
        
        return {"status": "completed_no_data", "reason": "Empty transaction lines"}

    # 3. Structure data
    async def call_structuring() -> list:
        return await structure_transactions(lines_text)

    structured_data = await ctx.step.run("call-openai-structuring", call_structuring)

    # 4. Save initial transactions
    async def save_initial_transactions() -> list:
        supabase = get_supabase_client()
        
        transactions_to_insert = []
        for tx in structured_data:
            transactions_to_insert.append({
                "document_id": document_id,
                "user_id": user_id,
                "date": tx.get("date"),
                "description": tx.get("description"),
                "amount": tx.get("amount"),
                "category": "Uncategorized", 
                "is_enriched": False 
            })
            
        def sync_insert():
            if not transactions_to_insert:
                return []
            response = supabase.table("transactions").insert(transactions_to_insert).execute()
            return response.data
            
        return await asyncio.to_thread(sync_insert)

    inserted_transactions = await ctx.step.run("save-transactions-to-db", save_initial_transactions)

    # 5. Trigger enrichment (Fan-out)
    events = []
    if inserted_transactions:
        for tx in inserted_transactions:
            events.append(
                inngest.Event(
                    name="ai/transaction.created",
                    data={
                        "transaction_id": tx["id"],
                        "description": tx["description"]
                    }
                )
            )
        
        await ctx.step.send_event("trigger-enrichment-fanout", events)
    
    # 6. Mark Document as COMPLETED
    async def set_doc_complete() -> None:
        supabase = get_supabase_client()
        await asyncio.to_thread(
            lambda: supabase.table("documents")
            .update({"status": "COMPLETED"})
            .eq("id", document_id)
            .execute()
        )
    await ctx.step.run("set-document-completed", set_doc_complete)

    # 7. Invalidate Cache
    async def invalidate_user_cache() -> str:
        if user_id:
            cache.invalidate_user(user_id)
            return f"Cache invalidated for user: {user_id}"
        return "No user ID found to invalidate cache."

    invalidation_result = await ctx.step.run("invalidate-dashboard-cache", invalidate_user_cache)
        
    return {"status": "structuring_completed", "count": len(inserted_transactions), "cache_status": invalidation_result}
