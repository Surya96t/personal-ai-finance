import asyncio
import inngest
from app.workflows.client import inngest_client
from app.db.client import get_supabase_client
from app.integrations.openai import isolate_transaction_lines as openai_isolate

@inngest_client.create_function(
    fn_id="ai-isolate-transaction-lines",
    trigger=inngest.TriggerEvent(event="ai/ocr.completed"),
    retries=3,
)
async def isolate_transaction_lines(ctx: inngest.Context) -> dict:
    document_id = ctx.event.data.get("document_id")

    # 1. Update status
    async def update_status() -> None:
        supabase = get_supabase_client()
        await asyncio.to_thread(
            lambda: supabase.table("documents")
            .update({"status": "PROCESSING_ISOLATION"})
            .eq("id", document_id)
            .execute()
        )
    await ctx.step.run("update-status-to-isolation", update_status)

    # 2. Get raw text
    async def get_raw_text() -> str:
        supabase = get_supabase_client()
        def sync_get():
            response = supabase.table("documents").select("extracted_text").eq("id", document_id).single().execute()
            if not response.data or not response.data.get("extracted_text"):
                raise ValueError(f"No extracted text found for document_id: {document_id}")
            return response.data["extracted_text"]
        
        return await asyncio.to_thread(sync_get)

    raw_text = await ctx.step.run("get-raw-text-from-db", get_raw_text)

    # 3. Isolate lines using OpenAI
    async def call_isolation_model() -> str:
        # openai.isolate_transaction_lines is already async
        return await openai_isolate(raw_text)

    isolated_lines = await ctx.step.run("call-openai-to-isolate-lines", call_isolation_model)

    # 4. Save results
    async def save_isolated_lines() -> None:
        supabase = get_supabase_client()
        await asyncio.to_thread(
            lambda: supabase.table("documents")
            .update({"transaction_lines_text": isolated_lines})
            .eq("id", document_id)
            .execute()
        )
    await ctx.step.run("save-isolated-lines-to-db", save_isolated_lines)

    # 5. Trigger Structuring
    await ctx.step.send_event(
        "trigger-ai-structuring",
        inngest.Event(
            name="ai/transaction_lines.isolated",
            data={"document_id": document_id}
        ),
    )

    return {"status": "isolation_completed", "document_id": document_id}
