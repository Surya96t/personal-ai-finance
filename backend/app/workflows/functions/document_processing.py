import asyncio
import inngest
from app.workflows.client import inngest_client
from app.db.client import get_supabase_client

@inngest_client.create_function(
    fn_id="document-processing-pipeline-start",
    trigger=inngest.TriggerEvent(event="app/document.uploaded"),
    retries=3,
)
async def process_document_uploaded(ctx: inngest.Context) -> dict:
    """
    Started when a document is uploaded.
    Updates status to PROCESSING and triggers OCR.
    """
    # 1. Extract event data
    document_id = ctx.event.data.get("document_id")
    storage_path = ctx.event.data.get("storage_path")
    
    if not document_id or not storage_path:
        raise inngest.NonRetriableError(
            f"Missing required event data: document_id={document_id}, storage_path={storage_path}"
        )

    # 2. Database update (wrapped)
    async def update_status_to_processing() -> None:
        supabase = get_supabase_client()
        await asyncio.to_thread(
            lambda: supabase.table("documents")
            .update({"status": "PROCESSING"})
            .eq("id", document_id)
            .execute()
        )
        return None

    await ctx.step.run("update-status-to-processing", update_status_to_processing)

    # 3. Send event to trigger the next step (OCR)
    await ctx.step.send_event(
        "trigger-ai-ocr",
        inngest.Event(
            name="ai/document.ready_for_ocr",
            data={
                "document_id": document_id,
                "storage_path": storage_path,
            }
        ),
    )

    return {"status": "processing_started", "document_id": document_id}
