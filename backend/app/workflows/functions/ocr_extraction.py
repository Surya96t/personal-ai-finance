import os
import asyncio
import inngest
import mimetypes
from app.workflows.client import inngest_client
from app.db.client import get_supabase_client
from app.core.storage import download_file_from_storage
from app.integrations.openai import extract_text_from_image

@inngest_client.create_function(
    fn_id="ai-perform-ocr-on-document",
    trigger=inngest.TriggerEvent(event="ai/document.ready_for_ocr"),
    retries=3,
)
async def perform_ocr_on_document(ctx: inngest.Context) -> dict:
    document_id = ctx.event.data.get("document_id")
    storage_path = ctx.event.data.get("storage_path")

    if not document_id or not storage_path:
        raise ValueError(f"Missing required event data: document_id={document_id}, storage_path={storage_path}")

    # 1. Update status
    async def update_status_to_ocr() -> None:
        supabase = get_supabase_client()
        await asyncio.to_thread(lambda: supabase.table("documents").update({"status": "PROCESSING_OCR"}).eq("id", document_id).execute())
    await ctx.step.run("update-status-to-ocr", update_status_to_ocr)

    # 2. Extract text with OpenAI
    async def extract_text_action() -> str:
        supabase = get_supabase_client()
        
        # Download from Supabase Storage
        file_bytes = await download_file_from_storage(supabase, storage_path)
        
        # Determine file type
        file_ext = None
        _, ext_part = os.path.splitext(storage_path)
        if ext_part:
            file_ext = ext_part.lstrip('.').lower()
        
        if not file_ext:
            mime_type, _ = mimetypes.guess_type(storage_path)
            if mime_type:
                 # guess_extension returns .ext, we want ext
                 ext = mimetypes.guess_extension(mime_type)
                 if ext:
                     file_ext = ext.lstrip('.')
        
        if not file_ext:
            # Fallback: check magic bytes for common types
            if file_bytes.startswith(b'%PDF'):
                file_ext = "pdf"
            elif file_bytes.startswith(b'\xff\xd8\xff'):
                file_ext = "jpg"
            elif file_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                file_ext = "png"
                
        if not file_ext:
             raise ValueError(f"Could not determine file extension for {storage_path} and magic byte detection failed.")
        
        # Extract text using GPT-4o Vision
        text = await extract_text_from_image(file_bytes, file_ext)
        return text

    # Wrap in step to enable retries and caching
    try:
        extracted_text = await ctx.step.run("extract-text-with-openai", extract_text_action)
    except Exception as e:
        # If extraction completely fails (after internal retries), mark as failed
        async def mark_failed_error() -> None:
            supabase = get_supabase_client()
            await asyncio.to_thread(
                lambda: supabase.table("documents")
                .update({"status": "FAILED", "error_message": f"OCR error: {str(e)}"})
                .eq("id", document_id)
                .execute()
            )
        await ctx.step.run("mark-document-as-failed-error", mark_failed_error)
        raise e

    # 3. Handle empty result
    if not extracted_text:
        async def mark_failed_empty() -> None:
            supabase = get_supabase_client()
            await asyncio.to_thread(
                lambda: supabase.table("documents")
                .update({"status": "FAILED", "error_message": "OCR returned empty text"})
                .eq("id", document_id)
                .execute()
            )
        await ctx.step.run("mark-document-as-failed-empty", mark_failed_empty)
        return {"status": "failed", "reason": "No text extracted"}

    # 4. Save extracted text
    async def save_extracted_text() -> None:
        supabase = get_supabase_client()
        update_payload = {
            "extracted_text": extracted_text,
            "status": "OCR_COMPLETE",
            "error_message": None  # Clear any previous error
        }
        await asyncio.to_thread(lambda: supabase.table("documents").update(update_payload).eq("id", document_id).execute())
    await ctx.step.run("save-extracted-text-to-db", save_extracted_text)

    # 5. Trigger next step (Isolation)
    await ctx.step.send_event(
        "trigger-ai-isolation",
        inngest.Event(name="ai/ocr.completed", data={"document_id": document_id})
    )

    return {"status": "ocr_completed", "document_id": document_id}
