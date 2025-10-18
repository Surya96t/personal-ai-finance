# backend/app/clients.py

import os
import inngest
import inngest.fast_api
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not supabase_url or not supabase_key:
    raise ValueError("Supabase URL or Key is not set.")
supabase: Client = create_client(supabase_url, supabase_key)

# --- THE FINAL, CORRECTED INNGEST CLIENT INITIALIZATION ---

# 1. Create a standard Python logger (optional but good for debugging)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 2. Initialize the client.
# The INNGEST_DEV=1 flag in your package.json script will be automatically
# detected by the SDK's internal `env_lib` to set development mode.
# The code itself does not need any conditional logic.
inngest_client = inngest.Inngest(
    app_id="personal-ai-finance",
    signing_key=os.getenv("INNGEST_SIGNING_KEY"),
    logger=logger,
)
