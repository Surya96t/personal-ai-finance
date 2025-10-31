from app.encryption_service import encrypt_amount, decrypt_amount
import os
import base64
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

# Before importing our service, set dummy env vars for testing
os.environ["GCP_PROJECT_ID"] = "test-project"
os.environ["GCP_KMS_LOCATION"] = "global"
os.environ["GCP_KMS_KEY_RING"] = "test-keyring"
os.environ["GCP_KMS_KEY_NAME"] = "test-key"

# Now import the functions to be tested

# --- Test Data ---
TEST_USER_ID = "user_2iabcdeFGHIJKLMnopqrsTUVWX"
TEST_AMOUNTS = [
    Decimal("123.45"),
    Decimal("-50.99"),
    Decimal("0.00"),
    Decimal("0.01"),
    Decimal("-0.01"),
    Decimal("999999999.9999"),
    Decimal("-999999999.9999"),
]

# --- Test Fixture ---


@pytest.fixture(autouse=True)
def mock_kms_client():
    """
    This fixture automatically mocks the KMS client for all tests in this file.
    It simulates the behavior of the real KMS client.
    """
    # Clear the cached client and key path before each test
    from app import encryption_service
    encryption_service._kms_client = None
    encryption_service._key_path = None

    with patch("app.encryption_service.kms_v1.KeyManagementServiceClient") as mock_client_constructor:
        mock_kms = MagicMock()
        mock_client_constructor.return_value = mock_kms

        # --- Simulate the 'encrypt' method ---
        def mock_encrypt(name, plaintext, additional_authenticated_data):
            # In a real scenario, KMS would return complex ciphertext.
            # For testing, we'll just reverse the plaintext and add a prefix
            # to simulate a transformation that isn't just base64.
            simulated_ciphertext = b"mock_encrypted_" + plaintext[::-1]
            mock_response = MagicMock()
            mock_response.ciphertext = simulated_ciphertext
            return mock_response

        mock_kms.encrypt.side_effect = mock_encrypt

        # --- Simulate the 'decrypt' method ---
        def mock_decrypt(name, ciphertext, additional_authenticated_data):
            # This must perfectly reverse the mock_encrypt logic.
            if ciphertext.startswith(b"mock_encrypted_"):
                simulated_plaintext = ciphertext[len(
                    b"mock_encrypted_"):][::-1]
                mock_response = MagicMock()
                mock_response.plaintext = simulated_plaintext
                return mock_response
            else:
                # Simulate a failure if the ciphertext is malformed
                raise Exception("KMS decryption failed: Invalid ciphertext")

        mock_kms.decrypt.side_effect = mock_decrypt

        yield mock_kms


# --- Test Cases ---

@pytest.mark.parametrize("amount", TEST_AMOUNTS)
def test_encrypt_decrypt_roundtrip_success(mock_kms_client, amount):
    """
    Tests that encrypting and then decrypting an amount returns the exact
    original Decimal value for a variety of inputs.
    """
    print(f"Testing amount: {amount}")

    # 1. Encrypt the amount
    encrypted_b64 = encrypt_amount(amount, TEST_USER_ID)

    # Assert that the output is a valid base64 string
    assert isinstance(encrypted_b64, str)
    assert base64.b64decode(encrypted_b64, validate=True)

    # 2. Decrypt the amount
    decrypted_amount = decrypt_amount(encrypted_b64, TEST_USER_ID)

    # 3. Assert the decrypted value is identical to the original
    assert isinstance(decrypted_amount, Decimal)
    assert decrypted_amount == amount


def test_decrypt_amount_with_wrong_user_id_fails(mock_kms_client):
    """
    Tests that decryption fails if the user_id in the AAD context changes.
    We simulate this by having the mock client raise an exception.
    """
    amount = Decimal("100.00")
    encrypted_b64 = encrypt_amount(amount, TEST_USER_ID)

    # Configure the mock to simulate a failure (like a real AAD mismatch would cause)
    mock_kms_client.decrypt.side_effect = Exception("KMS error: AAD mismatch")

    # Attempt to decrypt with a different user ID
    decrypted_amount = decrypt_amount(encrypted_b64, "user_DIFFERENT_ID_XYZ")

    # Assert that our function gracefully returns None instead of crashing
    assert decrypted_amount is None


def test_decrypt_amount_handles_invalid_input_gracefully():
    """

    Tests that decrypt_amount returns None for various kinds of bad input
    without needing to call the KMS client at all.
    """
    assert decrypt_amount(None, TEST_USER_ID) is None
    assert decrypt_amount("", TEST_USER_ID) is None
    assert decrypt_amount("not-base64-string", TEST_USER_ID) is None
    assert decrypt_amount(base64.b64encode(
        b"not-kms-ciphertext").decode(), TEST_USER_ID) is None


def test_encryption_context_is_used(mock_kms_client):
    """
    Verifies that the AAD (encryption context) is correctly constructed
    and passed to the KMS client during encryption and decryption.
    """
    amount = Decimal("75.50")

    # Encrypt
    encrypt_amount(amount, TEST_USER_ID)

    # Expected AAD
    expected_aad = json.dumps(
        {"type": "amount", "user_id": TEST_USER_ID}, sort_keys=True
    ).encode('utf-8')

    # Assert that the mock's 'encrypt' method was called with the correct AAD
    mock_kms_client.encrypt.assert_called_once()
    args, kwargs = mock_kms_client.encrypt.call_args
    assert kwargs['additional_authenticated_data'] == expected_aad

    # Decrypt
    encrypted_val = base64.b64encode(b"mock_encrypted_05.57").decode()
    decrypt_amount(encrypted_val, TEST_USER_ID)

    # Assert that the mock's 'decrypt' method was also called with the correct AAD
    assert mock_kms_client.decrypt.call_count == 1
    args, kwargs = mock_kms_client.decrypt.call_args
    assert kwargs['additional_authenticated_data'] == expected_aad
