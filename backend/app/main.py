# backend/app/main.py

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import inngest.fast_api

# Import the aggregated v1 API router
from app.api.v1.router import api_router

# Import Inngest client and workflow functions
from app.workflows.client import inngest_client
from app.workflows.functions.document_processing import process_document_uploaded
from app.workflows.functions.ocr_extraction import perform_ocr_on_document
from app.workflows.functions.line_isolation import isolate_transaction_lines
from app.workflows.functions.data_structuring import structure_transaction_data
from app.workflows.functions.enrichment import enrich_transaction_function

# --- Initialization ---
load_dotenv()

app = FastAPI(
    title="Personal AI Finance Planner API",
    version="2.0.0",
    description="AI-powered personal finance management system"
)

# --- CORS Middleware ---
allowed_origins_env = os.getenv("CORS_ALLOWED_ORIGINS")
if allowed_origins_env:
    allow_origins = [origin.strip() for origin in allowed_origins_env.split(",")]
else:
    allow_origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- Root Endpoint ---
@app.get("/")
def read_root():
    return {
        "status": "running",
        "message": "Personal AI Finance Planner API",
        "version": "2.0.0"
    }

# --- Include V1 API Routes ---
app.include_router(api_router)

# --- Register Inngest Workflows ---
inngest.fast_api.serve(
    app,
    inngest_client,
    [
        process_document_uploaded,
        perform_ocr_on_document,
        isolate_transaction_lines,
        structure_transaction_data,
        enrich_transaction_function,
    ]
)
