# app/encryption_service.py

import os
import json
import base64
from decimal import Decimal, InvalidOperation
from google.cloud import kms_v1

# --- Global variables to cache the client and key path after first use ---
_kms_client = None
_key_path = None


def _get_kms_client_and_key_path():
    """Initializes and caches the KMS client and key path."""
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
    """Encrypts a dictionary using Google Cloud KMS."""
    kms_client, key_path = _get_kms_client_and_key_path()

    try:
        plaintext_bytes = json.dumps(plaintext_data).encode("utf-8")
        response = kms_client.encrypt(
            request={"name": key_path, "plaintext": plaintext_bytes}
        )
        return base64.b64encode(response.ciphertext).decode("utf-8")
    except Exception as e:
        print(f"Error during KMS data encryption: {e}")
        raise e


def decrypt_data(ciphertext_b64: str | None) -> dict:
    """
    Decrypts a base64 encoded string containing JSON using Google Cloud KMS.
    Safely handles None or empty inputs.
    """
    if not isinstance(ciphertext_b64, str) or not ciphertext_b64:
        return {}

    kms_client, key_path = _get_kms_client_and_key_path()

    try:
        ciphertext_bytes = base64.b64decode(ciphertext_b64)
        response = kms_client.decrypt(
            request={"name": key_path, "ciphertext": ciphertext_bytes}
        )
        decrypted_json_string = response.plaintext.decode("utf-8")
        return json.loads(decrypted_json_string)
    except Exception as e:
        print(f"CRITICAL: Error during KMS data decryption: {e}")
        return {}

# --- NEW FUNCTIONS FOR AMOUNT ENCRYPTION (TASK 0.1) ---


def encrypt_amount(amount: Decimal, user_id: str) -> str:
    """
    Encrypts a single Decimal value using Google Cloud KMS with a specific context.
    """
    kms_client, key_path = _get_kms_client_and_key_path()

    try:
        # Convert Decimal to string, then to bytes for encryption
        plaintext_bytes = str(amount).encode("utf-8")

        # CRITICAL: Use Additional Authenticated Data (AAD) as encryption context
        # This binds the ciphertext to the user and the data type, preventing misuse.
        aad = json.dumps({"type": "amount", "user_id": user_id},
                         sort_keys=True).encode('utf-8')

        response = kms_client.encrypt(
            request={
                "name": key_path,
                "plaintext": plaintext_bytes,
                "additional_authenticated_data": aad
            }
        )
        return base64.b64encode(response.ciphertext).decode("utf-8")
    except Exception as e:
        print(f"Error during KMS amount encryption: {e}")
        raise e


def decrypt_amount(encrypted_amount_b64: str, user_id: str) -> Decimal | None:
    """
    Decrypts a base64 encoded amount using Google Cloud KMS, validating the context.
    Returns None on any failure.
    """
    if not isinstance(encrypted_amount_b64, str) or not encrypted_amount_b64:
        return None

    kms_client, key_path = _get_kms_client_and_key_path()

    try:
        ciphertext_bytes = base64.b64decode(encrypted_amount_b64)

        # CRITICAL: Provide the exact same AAD that was used for encryption.
        # If it doesn't match, the decryption call will fail.
        aad = json.dumps({"type": "amount", "user_id": user_id},
                         sort_keys=True).encode('utf-8')

        response = kms_client.decrypt(
            request={
                "name": key_path,
                "ciphertext": ciphertext_bytes,
                "additional_authenticated_data": aad
            }
        )
        decrypted_string = response.plaintext.decode("utf-8")

        # Convert the decrypted string back to a Decimal for precision
        return Decimal(decrypted_string)
    except (InvalidOperation, Exception) as e:
        # Catch any exception, from a bad b64 string to a KMS context mismatch.
        print(
            f"CRITICAL: Error during KMS amount decryption for user {user_id}: {e}")
        return None  # Return None on failure to prevent crashes
