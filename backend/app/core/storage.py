# backend/app/core/storage.py

import os
import asyncio
from typing import Optional
from supabase import Client
from dotenv import load_dotenv

load_dotenv()

STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "financial-documents")


async def download_file_from_storage(
    supabase: Client,
    file_path: str
) -> bytes:
    """
    Downloads a file from Supabase Storage.
    
    Args:
        supabase: Supabase client instance
        file_path: Path to file in storage bucket
        
    Returns:
        File contents as bytes
    """
    def sync_download():
        response = supabase.storage.from_(STORAGE_BUCKET).download(file_path)
        return response
    
    file_bytes = await asyncio.to_thread(sync_download)
    return file_bytes


async def upload_file_to_storage(
    supabase: Client,
    file_path: str,
    file_bytes: bytes,
    content_type: Optional[str] = None
) -> str:
    """
    Uploads a file to Supabase Storage.
    
    Args:
        supabase: Supabase client instance
        file_path: Destination path in storage bucket
        file_bytes: File contents as bytes
        content_type: MIME type of the file
        
    Returns:
        Public URL or path to the uploaded file
    """
    def sync_upload():
        response = supabase.storage.from_(STORAGE_BUCKET).upload(
            file_path,
            file_bytes,
            file_options={"content-type": content_type} if content_type else None
        )
        return response
    
    result = await asyncio.to_thread(sync_upload)
    
    # Handle response - could be dict or Response object
    uploaded_path = None
    
    if isinstance(result, dict):
        uploaded_path = result.get("Key") or result.get("key") or result.get("path")
    elif hasattr(result, "json"):
        try:
            data = result.json()
            if isinstance(data, dict):
                uploaded_path = data.get("Key") or data.get("key") or data.get("path")
        except:
            pass
            
    # Return extracted path or fallback to request path
    return uploaded_path if uploaded_path else file_path


async def delete_file_from_storage(
    supabase: Client,
    file_path: str
) -> bool:
    """
    Deletes a file from Supabase Storage.
    
    Args:
        supabase: Supabase client instance
        file_path: Path to file in storage bucket
        
    Returns:
        True if successful
    """
    def sync_delete():
        return supabase.storage.from_(STORAGE_BUCKET).remove([file_path])
    
    try:
        response = await asyncio.to_thread(sync_delete)
        
        # Check if response is a list of deleted objects (success case)
        if isinstance(response, list) and len(response) > 0:
            return True
            
        # Handle failures or file not found cases
        if isinstance(response, dict) and response.get("error"):
            raise Exception(f"Storage delete error: {response['error']}")
            
        return False
        
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")
        raise e


def get_file_type_from_path(file_path: str) -> str:
    """
    Extracts file extension from a path.
    
    Args:
        file_path: File path or name
        
    Returns:
        File extension (e.g., 'pdf', 'jpg')
    """
    return file_path.split('.')[-1].lower() if '.' in file_path else 'pdf'
