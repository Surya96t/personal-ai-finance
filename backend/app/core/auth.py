# backend/app/core/auth.py

import os
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from typing import Dict
from clerk_backend_api import Clerk
from clerk_backend_api.security import AuthenticateRequestOptions
from dotenv import load_dotenv

load_dotenv()

# --- Clerk and Security Scheme Initialization ---
clerk_secret_key = os.getenv("CLERK_SECRET_KEY")
if not clerk_secret_key:
    raise ValueError("CLERK_SECRET_KEY is not set.")

clerk_sdk = Clerk(bearer_auth=clerk_secret_key)
security_scheme = HTTPBearer()


async def get_current_user_claims(req: Request) -> Dict:
    """
    Validates the JWT token from Clerk and returns user claims.
    Raises HTTPException if authentication fails.
    """
    options = AuthenticateRequestOptions()
    try:
        request_state = clerk_sdk.authenticate_request(req, options)
        if not request_state.is_signed_in:
            raise HTTPException(
                status_code=401, detail="Unauthorized: Not signed in"
            )
        return request_state.payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")
