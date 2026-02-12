# backend/app/integrations/openai.py

import os
import io
import base64
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv
import pypdfium2 as pdfium
from PIL import Image

load_dotenv()

# Initialize OpenAI client
_openai_client = None


def get_openai_client() -> OpenAI:
    """Lazy initialization of OpenAI client."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment variables")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


async def extract_text_from_image(image_bytes: bytes, file_type: str = "pdf") -> str:
    """
    Uses OpenAI GPT-4o Vision to extract text from an image or PDF.
    
    Args:
        image_bytes: Raw bytes of the image/PDF
        file_type: Type of file (pdf, jpg, png, etc.)
        
    Returns:
        Extracted text as a string
    """
    client = get_openai_client()

    # Handle PDF conversion
    if file_type.lower() == "pdf":
        try:
            pdf = pdfium.PdfDocument(image_bytes)
            if len(pdf) > 0:
                # Render first page at 2x scale for better OCR
                page = pdf[0]
                bitmap = page.render(scale=2)
                pil_image = bitmap.to_pil()
                
                # Convert to JPEG bytes
                img_byte_arr = io.BytesIO()
                pil_image.save(img_byte_arr, format='JPEG')
                image_bytes = img_byte_arr.getvalue()
                
                # Update file_type to jpg so MIME type is set correctly
                file_type = "jpg"
        except Exception as e:
            print(f"Error converting PDF to image: {e}")
            # Fallback (though this will likely fail 400 at OpenAI if it's still PDF data)
            raise ValueError(f"Could not convert PDF for OCR: {e}")
    
    # Convert bytes to base64
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    # Determine MIME type
    mime_types = {
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "heic": "image/heic",
        "heif": "image/heif"
    }
    mime_type = mime_types.get(file_type.lower(), "application/pdf")
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Extract all text from this financial document. 
                        Focus on transaction data, dates, amounts, and descriptions.
                        Preserve the original formatting and structure as much as possible.
                        Return only the extracted text, no additional commentary."""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ],
            }
        ],
        max_tokens=4096
    )
    
    return response.choices[0].message.content


async def isolate_transaction_lines(full_text: str) -> str:
    """
    Uses OpenAI to identify and extract just the transaction lines from OCR text.
    
    Args:
        full_text: Full OCR extracted text
        
    Returns:
        Just the transaction lines
    """
    client = get_openai_client()
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """You are a financial document parser. Extract ONLY the transaction lines from bank statements or credit card statements.
                Include: date, description, and amount for each transaction.
                Exclude: headers, footers, account summaries, page numbers, and promotional text.
                Preserve the original line format."""
            },
            {
                "role": "user",
                "content": f"Extract only transaction lines from this text:\n\n{full_text}"
            }
        ],
        max_tokens=4096
    )
    
    return response.choices[0].message.content


async def structure_transactions(transaction_lines: str) -> List[Dict]:
    """
    Uses OpenAI with structured output to parse transactions into JSON.
    
    Args:
        transaction_lines: Raw transaction text lines
        
    Returns:
        List of structured transaction dictionaries
    """
    client = get_openai_client()
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """You are a JSON data extraction specialist for financial transactions.
                Parse each transaction line into a structured JSON object with these fields:
                - date: YYYY-MM-DD format
                - description: full original transaction description
                - amount: numeric value (negative for expenses/debits, positive for income/credits)
                
                Return a JSON object with a "transactions" array containing all parsed transactions."""
            },
            {
                "role": "user",
                "content": f"Parse these transaction lines into JSON:\n\n{transaction_lines}"
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=4096
    )
    
    import json
    result = json.loads(response.choices[0].message.content)
    return result.get("transactions", [])


async def enrich_transaction(description: str) -> Dict[str, str]:
    """
    Uses OpenAI to clean description and categorize a transaction.
    
    Args:
        description: Raw transaction description
        
    Returns:
        Dictionary with cleaned_description and category
    """
    client = get_openai_client()
    
    categories = [
        "Food & Drink", "Shopping", "Housing", "Transportation", "Utilities",
        "Entertainment", "Income", "Travel", "Health & Wellness", "Groceries",
        "Personal Care", "Gifts & Donations", "Other"
    ]
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"""You are a financial transaction categorization expert.
                For each transaction description:
                1. Clean it to extract the merchant/payee name (remove codes, locations, dates)
                2. Categorize it into ONE of these categories: {', '.join(categories)}
                
                Return JSON with: {{"cleaned_description": "...", "category": "..."}}
                
                Examples:
                - "AMAZON.COM*2X3Y4Z AMZN.COM/BILL WA" → {{"cleaned_description": "Amazon", "category": "Shopping"}}
                - "STARBUCKS STORE #12345" → {{"cleaned_description": "Starbucks", "category": "Food & Drink"}}
                - "PAYCHECK DEPOSIT - ACME CORP" → {{"cleaned_description": "Acme Corp Paycheck", "category": "Income"}}
                """
            },
            {
                "role": "user",
                "content": f"Clean and categorize: {description}"
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=256
    )
    
    import json
    return json.loads(response.choices[0].message.content)
