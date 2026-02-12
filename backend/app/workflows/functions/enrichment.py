import asyncio
import inngest
from app.workflows.client import inngest_client
from app.db.client import get_supabase_client
from app.integrations.openai import enrich_transaction

@inngest_client.create_function(
    fn_id="ai-enrich-transaction",
    trigger=inngest.TriggerEvent(event="ai/transaction.created"),
    retries=3,
    concurrency=[inngest.Concurrency(limit=5)], # Limit concurrency
)
async def enrich_transaction_function(ctx: inngest.Context) -> dict:
    transaction_id = ctx.event.data.get("transaction_id")
    description = ctx.event.data.get("description")

    # 1. Enrich using OpenAI
    async def call_enrichment() -> dict:
        return await enrich_transaction(description)

    enrichment_result = await ctx.step.run("call-openai-enrichment", call_enrichment)

    # 2. Update Transaction in DB
    async def update_transaction() -> None:
        supabase = get_supabase_client()
        
        update_data = {
            "category": enrichment_result.get("category"),
            "is_enriched": True
        }
        
        # Include cleaned_description if available. 
        # Note: Ensure your DB table has this column. If not, this might fail or be ignored.
        if enrichment_result.get("cleaned_description"):
             update_data["cleaned_description"] = enrichment_result.get("cleaned_description")
             
        await asyncio.to_thread(
            lambda: supabase.table("transactions")
            .update(update_data)
            .eq("id", transaction_id)
            .execute()
        )
    
    await ctx.step.run("update-transaction-db", update_transaction)
    
    return {"status": "enriched", "transaction_id": transaction_id}
