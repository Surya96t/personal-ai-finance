# backend/app/inngest_functions.py
import os
import inngest
import json
import asyncio
from .clients import inngest_client, supabase
from google.cloud import vision
import google.generativeai as genai
from pydantic import BaseModel, Field  # <-- Add Pydantic imports
from typing import List, Literal  # <-- Add typing imports
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure the Gemini client
# It will automatically use the GOOGLE_APPLICATION_CREDENTIALS for auth
genai.configure()

# --- Pydantic Schemas for Structured Output ---
# Define the structure we want the LLM to return for each transaction.


class Transaction(BaseModel):
    date: str = Field(
        description="The date of the transaction in YYYY-MM-DD format.")
    description: str = Field(
        description="The full, original description of the transaction.")
    amount: float = Field(
        description="The transaction amount. Use a negative number for debits/expenses.")


class TransactionList(BaseModel):
    transactions: List[Transaction]


class EnrichedTransaction(BaseModel):
    cleaned_description: str = Field(
        description="The cleaned, human-readable merchant name.")
    category: Literal[
        "Food & Drink", "Shopping", "Housing", "Transportation", "Utilities",
        "Entertainment", "Income", "Travel", "Health & Wellness", "Groceries",
        "Personal Care", "Gifts & Donations", "Other"
    ] = Field(description="The financial category of the transaction.")


# This function is triggered when a document is uploaded and a record is created.
# Its job is to update the status and trigger the next step in the AI pipeline.
@inngest_client.create_function(
    fn_id="document-processing-pipeline-start",
    trigger=inngest.TriggerEvent(event="app/document.uploaded"),
    retries=3,
)
async def process_document_uploaded(ctx: inngest.Context) -> dict:
    # 1. Extract event data
    document_id = ctx.event.data.get("document_id")
    gcs_path = ctx.event.data.get("gcs_path")

    # 2. Database update (wrapped)
    # Following Rule #3 and #4 for side effects and sync DB calls
    async def update_status_to_processing() -> None:
        await asyncio.to_thread(
            lambda: supabase.table("documents")
            .update({"status": "PROCESSING"})
            .eq("id", document_id)
            .execute()
        )
        # Rule #5: Return a serializable value
        return None

    await ctx.step.run("update-status-to-processing", update_status_to_processing)

    # 3. Send event to trigger the next step (the actual AI agent)
    # Following Rule #6
    await ctx.step.send_event(
        "trigger-ai-ocr",
        inngest.Event(
            name="ai/document.ready_for_ocr",
            data={
                "document_id": document_id,
                "gcs_path": gcs_path,
            }
        ),
    )

    # 4. Return serializable result
    # Following Rule #8
    return {"status": "processing_started", "document_id": document_id}


# --- NEW FUNCTION: Performs OCR on the document ---
@inngest_client.create_function(
    fn_id="ai-perform-ocr-on-document",
    trigger=inngest.TriggerEvent(event="ai/document.ready_for_ocr"),
    retries=3,
)
async def perform_ocr_on_document(ctx: inngest.Context) -> dict:
    # 1. Extract event data
    document_id = ctx.event.data.get("document_id")

    # --- NEW: Update status at the beginning of the step ---
    async def update_status_to_ocr() -> None:
        await asyncio.to_thread(
            lambda: supabase.table("documents")
            .update({"status": "PROCESSING_OCR"})
            .eq("id", document_id)
            .execute()
        )
        return None
    await ctx.step.run("update-status-to-ocr", update_status_to_ocr)

    gcs_path = ctx.event.data.get("gcs_path")
    bucket_name = os.getenv("GCP_BUCKET_NAME")

    # 2. Side-effecting operation (wrapped) - NOW USING THE ROBUST BATCH METHOD
    async def extract_text_from_gcs() -> str:
        def sync_extract() -> str:
            """
            Performs OCR on a document in GCS using the batch method,
            which is optimized for multi-page PDFs.
            """
            client = vision.ImageAnnotatorClient()

            gcs_source = vision.GcsSource(uri=f"gs://{bucket_name}/{gcs_path}")

            # This tells Vision what kind of file it is.
            # It can also handle other types like 'image/tiff'.
            input_config = vision.InputConfig(
                gcs_source=gcs_source,
                mime_type='application/pdf'
            )

            features = [vision.Feature(
                type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)]

            # The batch request can handle multiple files, but we're just sending one.
            request = vision.AnnotateFileRequest(
                input_config=input_config,
                features=features
            )

            # Make the API call
            response = client.batch_annotate_files(requests=[request])

            # The response is nested. We need to iterate through it to collect the text.
            all_text = []
            # Check for errors at the top level of the response
            # (Note: The actual error structure may be different, this is a basic check)
            if response.responses[0].error.message:
                raise Exception(
                    f"Google Vision API batch error: {response.responses[0].error.message}")

            for image_response in response.responses[0].responses:
                if image_response.full_text_annotation:
                    all_text.append(image_response.full_text_annotation.text)

            if not all_text:
                # This handles cases where the PDF was empty or unreadable
                return ""

            # Join the text from all pages together
            return "\n\n--- Page Break ---\n\n".join(all_text)

        # Run the synchronous function in a separate thread
        loop = asyncio.get_running_loop()
        extracted_text = await loop.run_in_executor(None, sync_extract)
        return extracted_text

    extracted_text = await ctx.step.run("extract-text-from-gcs-batch", extract_text_from_gcs)

    # If no text was extracted, we should fail the process gracefully.
    if not extracted_text:
        async def mark_document_as_failed() -> None:
            await asyncio.to_thread(
                lambda: supabase.table("documents")
                .update({"status": "FAILED", "error_message": "OCR failed: No text could be extracted from the document."})
                .eq("id", document_id)
                .execute()
            )
            return None
        await ctx.step.run("mark-document-as-failed", mark_document_as_failed)
        return {"status": "failed", "reason": "No text extracted"}

    # 3. Database update (wrapped) - Unchanged

    async def save_extracted_text() -> None:
        await asyncio.to_thread(
            lambda: supabase.table("documents")
            .update({"extracted_text": extracted_text})
            .eq("id", document_id)
            .execute()
        )
        return None

    await ctx.step.run("save-extracted-text-to-db", save_extracted_text)

    # 4. Send event for the next step (unchanged)
    await ctx.step.send_event(
        "trigger-ai-structuring",
        inngest.Event(
            name="ai/ocr.completed",
            data={"document_id": document_id}
        ),
    )

    # 5. Return serializable result (unchanged)
    return {"status": "ocr_completed", "document_id": document_id}


# --- NEW FUNCTION: Isolates transaction lines using an LLM ---
@inngest_client.create_function(
    fn_id="ai-isolate-transaction-lines",
    trigger=inngest.TriggerEvent(event="ai/ocr.completed"),
    retries=3,
)
async def isolate_transaction_lines(ctx: inngest.Context) -> dict:
    # 1. Extract event data
    document_id = ctx.event.data.get("document_id")

    # --- NEW: Update status at the beginning of the step ---
    async def update_status_to_ocr() -> None:
        await asyncio.to_thread(
            lambda: supabase.table("documents")
            .update({"status": "PROCESSING_ISOLATION"})
            .eq("id", document_id)
            .execute()
        )
        return None
    await ctx.step.run("update-status-to-ocr", update_status_to_ocr)

    # 2. Database fetch (wrapped)
    async def get_raw_text() -> str:
        def sync_get():
            response = supabase.table("documents").select(
                "extracted_text").eq("id", document_id).single().execute()
            if not response.data or not response.data.get("extracted_text"):
                raise ValueError(
                    f"No extracted text found for document_id: {document_id}")
            return response.data["extracted_text"]

        loop = asyncio.get_running_loop()
        raw_text = await loop.run_in_executor(None, sync_get)
        return raw_text

    raw_text = await ctx.step.run("get-raw-text-from-db", get_raw_text)

    # 3. LLM call to isolate transactions (wrapped)
    async def call_llm_to_isolate() -> str:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        You are a financial data extraction expert.
        From the following raw text from a financial statement, extract ONLY the lines that represent financial transactions.
        Ignore all headers, footers, summary boxes, marketing text, page numbers, and any other non-transactional text.
        Present the output as a clean list of transaction lines, one per line.

        RAW TEXT:
        ---
        {raw_text}
        ---
        """
        # The genai library is async, so we can call it directly
        response = await model.generate_content_async(prompt)
        return response.text

    isolated_lines = await ctx.step.run("call-gemini-to-isolate-lines", call_llm_to_isolate)

    # 4. Database update (wrapped)
    async def save_isolated_lines() -> None:
        await asyncio.to_thread(
            lambda: supabase.table("documents")
            .update({"transaction_lines_text": isolated_lines})
            .eq("id", document_id)
            .execute()
        )
        return None

    await ctx.step.run("save-isolated-lines-to-db", save_isolated_lines)

    # 5. Send event for the next step
    await ctx.step.send_event(
        "trigger-ai-structuring",
        inngest.Event(
            name="ai/transaction_lines.isolated",
            data={
                "document_id": document_id,
            }
        ),
    )

    # 6. Return serializable result
    return {"status": "isolation_completed", "document_id": document_id}


# --- NEW FUNCTION: Structures transaction text into JSON ---
@inngest_client.create_function(
    fn_id="ai-structure-transaction-data",
    trigger=inngest.TriggerEvent(event="ai/transaction_lines.isolated"),
    retries=2,  # Less retries as LLM failures can be persistent
)
async def structure_transaction_data(ctx: inngest.Context) -> dict:
    # 1. Extract event data
    document_id = ctx.event.data.get("document_id")

    # --- NEW: Update status at the beginning of the step ---
    async def update_status_to_ocr() -> None:
        await asyncio.to_thread(
            lambda: supabase.table("documents")
            .update({"status": "PROCESSING_STRUCTURING"})
            .eq("id", document_id)
            .execute()
        )
        return None
    await ctx.step.run("update-status-to-ocr", update_status_to_ocr)

    # 2. Database fetch (wrapped)
    async def get_document_data() -> dict:
        def sync_get():
            response = supabase.table("documents").select(
                "transaction_lines_text, user_id").eq("id", document_id).single().execute()
            if not response.data or not response.data.get("transaction_lines_text"):
                raise ValueError(
                    f"No transaction lines found for document_id: {document_id}")
            return response.data

        loop = asyncio.get_running_loop()
        doc_data = await loop.run_in_executor(None, sync_get)
        return doc_data

    document_data = await ctx.step.run("get-isolated-lines-from-db", get_document_data)
    transaction_lines = document_data.get("transaction_lines_text")
    user_id = document_data.get("user_id")

    # 3. LLM call with JSON mode (wrapped)
    async def call_llm_to_structure() -> list:
        # Use a model that supports JSON mode
        model = genai.GenerativeModel(
            'gemini-2.5-flash',
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=TransactionList,  # <-- Use the Pydantic model directly
            )
        )
        prompt = f"""
        You are a JSON data extraction specialist.
        From the following lines of financial transactions, parse each line into a structured JSON object.
        The final output must be a single JSON object with a key "transactions" which contains a list of these objects.
        Adhere strictly to the provided schema.
        - The 'amount' should be negative for expenses, debits, or payments.
        - The 'amount' should be positive for income, credits, or deposits.
        
        TRANSACTION LINES:
        ---
        {transaction_lines}
        ---
        """
        # Call WITHOUT the tools parameter
        response = await model.generate_content_async(prompt)

        # Parse the response text directly, as you showed
        parsed_response = json.loads(response.text)
        return parsed_response.get("transactions", [])

    structured_transactions = await ctx.step.run("call-gemini-to-structure-data", call_llm_to_structure)

    # 4. Prepare and save data to the 'transactions' table (wrapped)
    async def save_transactions() -> int:
        if not structured_transactions:
            return 0

        # Add the user_id and document_id to each transaction before inserting
        for trx in structured_transactions:
            trx['user_id'] = user_id
            trx['document_id'] = document_id

        def sync_insert():
            response = supabase.table("transactions").insert(
                structured_transactions).execute()
            return len(response.data)

        loop = asyncio.get_running_loop()
        count = await loop.run_in_executor(None, sync_insert)
        return count

    transactions_created_count = await ctx.step.run("save-structured-transactions-to-db", save_transactions)

    # 5. Send event for the next step (enrichment)
    await ctx.step.send_event(
        "trigger-ai-enrichment",
        inngest.Event(
            name="ai/transactions.structured",
            data={
                "document_id": document_id,
            }
        ),
    )

    # 6. Return serializable result
    return {
        "status": "structuring_completed",
        "document_id": document_id,
        "transactions_created": transactions_created_count,
    }


# REFACTORED AND CORRECTED for parallel processing and database updates
@inngest_client.create_function(
    fn_id="ai-enrich-and-categorize-transactions",
    trigger=inngest.TriggerEvent(event="ai/transactions.structured"),
    retries=1,
)
async def enrich_and_categorize_transactions(ctx: inngest.Context) -> dict:
    # 1. Extract event data and update status (unchanged)
    document_id = ctx.event.data.get("document_id")

    async def update_status_to_enrichment() -> None:
        await asyncio.to_thread(lambda: supabase.table("documents").update({"status": "PROCESSING_ENRICHMENT"}).eq("id", document_id).execute())
    await ctx.step.run("update-status-to-enrichment", update_status_to_enrichment)

    # 2. Fetch transactions (unchanged)
    async def get_transactions_to_enrich() -> List[dict]:
        def sync_get():
            return supabase.table("transactions").select("id, description").eq("document_id", document_id).execute().data
        return await asyncio.to_thread(sync_get)
    transactions_to_enrich = await ctx.step.run("get-transactions-to-enrich", get_transactions_to_enrich)

    if not transactions_to_enrich:
        async def mark_document_as_completed_early() -> None:
            await asyncio.to_thread(lambda: supabase.table("documents").update({"status": "COMPLETED"}).eq("id", document_id).execute())
        await ctx.step.run("mark-document-as-completed-early", mark_document_as_completed_early)
        return {"status": "completed", "reason": "No transactions to enrich"}

    # --- THIS IS THE CORRECTED PARALLEL LOGIC ---

    # 3. Define a task that ONLY calls the LLM
    async def enrich_one_transaction(trx: dict) -> dict:
        """Calls the LLM and returns the enriched data."""
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config=genai.GenerationConfig(
            response_schema=EnrichedTransaction, response_mime_type="application/json"))
        prompt = f"Analyze the following raw transaction description and return a clean merchant name and a category. RAW DESCRIPTION:\n---\n{trx['description']}\n---"
        response = await model.generate_content_async(prompt)
        return json.loads(response.text)

    # 4. Run all LLM enrichment tasks concurrently in a single step
    async def run_all_enrichments() -> List[dict]:
        tasks = [enrich_one_transaction(trx) for trx in transactions_to_enrich]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    enriched_results = await ctx.step.run("enrich-all-transactions-in-parallel", run_all_enrichments)

    # 5. Now, loop through the results and update the database one by one.
    # This is safe and still much faster than a fully serial process.
    async def update_all_transactions() -> int:
        updated_count = 0
        errors = []
        for i, result in enumerate(enriched_results):
            if isinstance(result, Exception):
                errors.append(f"Transaction index {i} failed: {result}")
                continue

            # Get the ID of the transaction we need to update
            transaction_id = transactions_to_enrich[i]['id']

            # This is a synchronous call, so it must be wrapped
            def sync_update():
                supabase.table("transactions").update(
                    result).eq("id", transaction_id).execute()

            await asyncio.to_thread(sync_update)
            updated_count += 1

        if errors:
            print(
                f"Warning: {len(errors)} enrichment tasks failed. Errors: {errors}")

        return updated_count

    updated_count = await ctx.step.run("update-enriched-transactions-in-db", update_all_transactions)

    # --- END OF CORRECTED LOGIC ---

    # 6. Mark document as completed (unchanged)
    async def mark_document_as_completed() -> None:
        await asyncio.to_thread(lambda: supabase.table("documents").update({"status": "COMPLETED"}).eq("id", document_id).execute())
    await ctx.step.run("mark-document-as-completed", mark_document_as_completed)

    # 7. Return result
    return {
        "status": "enrichment_completed",
        "document_id": document_id,
        "transactions_enriched": updated_count,
    }
