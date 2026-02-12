# backend/app/db/client.py

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def get_supabase_client() -> Client:
    """
    Creates and returns a Supabase client instance.
    Uses service role key for backend operations.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase keys not set.")
    
    return create_client(supabase_url, supabase_key)
