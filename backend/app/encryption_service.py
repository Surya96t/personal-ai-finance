# backend/app/encryption_service.py

import os
import json
import base64
from google.cloud import kms_v1

# --- DO NOT INITIALIZE THE CLIENT HERE ---
# kms_client = kms_v1.KeyManagementServiceClient() # THIS WAS THE BUG

# --- Use a global variable to cache the client after first use ---
_kms_client = None
_key_path = None


def _get_kms_client_and_key_path():
    """
    Initializes and caches the KMS client and key path.
    This function will only do the expensive setup once.
    """
    global _kms_client, _key_path
    if _kms_client is None:
        _kms_client = kms_v1.KeyManagementServiceClient()

        project_id = os.getenv("GCP_PROJECT_ID")
        location = os.getenv("GCP_KMS_LOCATION")
        key_ring = os.getenv("GCP_KMS_KEY_RING")
        key_name = os.getenv("GCP_KMS_KEY_NAME")

        if not all([project_id, location, key_ring, key_name]):
            raise ValueError("Google Cloud KMS config is missing.")

        _key_path = _kms_client.crypto_key_path(
            project_id, location, key_ring, key_name)

    return _kms_client, _key_path


def encrypt_data(plaintext_data: dict) -> str:
    """Encrypts data using Google Cloud KMS."""
    kms_client, key_path = _get_kms_client_and_key_path()  # <-- Initialize lazily

    try:
        plaintext_bytes = json.dumps(plaintext_data).encode("utf-8")
        response = kms_client.encrypt(name=key_path, plaintext=plaintext_bytes)
        return base64.b64encode(response.ciphertext).decode("utf-8")
    except Exception as e:
        print(f"Error during KMS encryption: {e}")
        raise e

# --- THIS IS THE ROBUST DECRYPTION FUNCTION ---


def decrypt_data(ciphertext_b64: str | None) -> dict:
    """
    Decrypts a base64 encoded string using Google Cloud KMS.
    Safely handles None or empty inputs.
    """
    # --- THE FIX IS HERE ---
    # If the input is None or not a string, return an empty dict.
    if not isinstance(ciphertext_b64, str) or not ciphertext_b64:
        return {}

    kms_client, key_path = _get_kms_client_and_key_path()

    try:
        ciphertext_bytes = base64.b64decode(ciphertext_b64)
        response = kms_client.decrypt(
            name=key_path, ciphertext=ciphertext_bytes)
        decrypted_json_string = response.plaintext.decode("utf-8")
        return json.loads(decrypted_json_string)
    except Exception as e:
        # If decryption fails for any reason (e.g., corrupted data),
        # log it and return an empty dict to prevent a crash.
        print(f"CRITICAL: Error during KMS decryption: {e}")
        return {}
