### **Detailed Implementation Plan: Application-Level Encryption (ALE)**

**Goal:** Implement a high-security architecture where all sensitive user financial data is encrypted at the application level before being stored in the database. This will be achieved using Google Cloud Key Management Service (KMS) for secure key management and encryption/decryption operations.

---

#### **Phase 1: Infrastructure Setup & Configuration**

**Objective:** Provision and configure the necessary cloud services and update our database schema to support encryption.

- **Task: Configure Google Cloud KMS**

  - **Action:** In our existing Google Cloud Platform project, enable the **"Cloud Key Management Service (KMS) API"**.
  - **Action:** Create a new **"Key Ring"**. This is a logical grouping for our cryptographic keys. Name it something descriptive, like `personal-ai-finance-key-ring`.
  - **Action:** Within the new key ring, create a new **"Cryptographic Key"**.
    - **Name:** `user-data-encryption-key`.
    - **Purpose:** Select **"Symmetric encrypt/decrypt"**. This is the standard for this type of data protection.
    - Leave all other settings (rotation period, etc.) as default for now.
  - **Action:** Update IAM (Identity and Access Management) permissions. Find the service account our backend is already using (`backend-api-service`) and grant it the **"Cloud KMS CryptoKey Encrypter/Decrypter"** role. This gives our backend permission to _use_ the key, but not to manage or delete it.

- **Task: Update the Database Schema**
  - **Action:** We need to modify our `transactions` table to store the encrypted data. The current columns (`description`, `cleaned_description`, `amount`) are designed for plaintext and have the wrong data types for ciphertext.
  - **Plan:**
    1.  Add a new column to the `transactions` table named `encrypted_data`. The data type should be `TEXT` or `BYTEA` to store the base64-encoded ciphertext.
    2.  The existing columns (`description`, `cleaned_description`, `amount`, `category`) will eventually be deprecated and removed, but we will keep them for now during the transition.

---

#### **Phase 2: Backend Refactoring**

**Objective:** Modify our backend API and Inngest pipeline to handle the encryption and decryption lifecycle.

- **Task: Install New Python Libraries**

  - **Action:** Add the `google-cloud-kms` library to our backend's dependencies.

- **Task: Create an Encryption Service**

  - **Action:** Create a new file, `backend/app/encryption_service.py`.
  - **Plan:** This file will contain two core functions:
    1.  `encrypt_data(user_id, plaintext_data)`: This function will take a user's ID and a Python dictionary (e.g., a transaction object), serialize it to a JSON string, and then call the Google Cloud KMS API to encrypt it using our cryptographic key. It will return the resulting base64-encoded ciphertext.
    2.  `decrypt_data(user_id, ciphertext_data)`: This function will take the ciphertext, call the KMS API to decrypt it, and then deserialize the resulting JSON string back into a Python dictionary.

- **Task: Refactor the Inngest Pipeline (Write Path)**

  - **Action:** Modify the `enrich_and_categorize_transactions` function in `inngest_functions.py`.
  - **Plan:**
    1.  After the enrichment process, instead of updating the individual plaintext columns, the function will now call our new `encrypt_data()` service for each transaction.
    2.  It will then perform a bulk update to save this encrypted blob into the new `encrypted_data` column of the `transactions` table.

- **Task: Refactor the API Endpoints (Read Path)**
  - **Action:** Modify all data-retrieval endpoints in `main.py` (`GET /transactions`, `GET /dashboard/summary`, etc.).
  - **Plan:**
    1.  The endpoints will still query the database as before, but they will now fetch the `encrypted_data` column.
    2.  For each row returned from the database, the endpoint will loop through the results and call our new `decrypt_data()` service.
    3.  The endpoint will then return the fully decrypted and reconstructed list of transactions to the frontend.
  - **Note:** Our PostgreSQL functions (`get_dashboard_summary`, etc.) will become obsolete, as the database can no longer read the encrypted data to perform calculations. All aggregations will now need to be performed in our Python backend _after_ the data has been decrypted. The endpoints will be refactored to handle this.

---

#### **Phase 3: Frontend Adjustments (Minimal)**

**Objective:** Ensure the frontend continues to work seamlessly with the new backend.

- **Task: No Major Changes Required**
  - **Plan:** Because we are performing the decryption on the backend, the frontend remains "dumb" to the encryption. It will continue to send and receive standard, unencrypted JSON. The API contract does not change.
  - **Action:** We will need to thoroughly test all frontend components (dashboard, transactions table) to ensure they still receive data in the exact format they expect.

---

### **Summary of Changes by File**

- **`backend/.env`**: Will need to be updated with the Google Cloud KMS key path/ID.
- **`backend/app/clients.py`**: No changes needed here.
- **`backend/app/encryption_service.py`**: A completely new file to house the encryption and decryption logic.
- **`backend/app/inngest_functions.py`**: The final enrichment function will be heavily modified to call the encryption service instead of writing plaintext data.
- **`backend/app/main.py`**: All `GET` endpoints that return financial data will be heavily modified to fetch encrypted data, call the decryption service, and perform calculations in Python instead of SQL.
- **Supabase SQL Editor**: We will run an `ALTER TABLE` command to add the new `encrypted_data` column.
- **Frontend Files**: No code changes are expected, but full regression testing is required.
