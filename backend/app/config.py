# app/config.py

import os

# --- Feature Flags ---

# Reads the environment variable 'ENCRYPTION_READ_PATH_ENABLED'.
# The .lower() == 'true' ensures that only the exact string 'true' (case-insensitive)
# will enable the flag. Any other value, or the variable not being set, will
# result in it being False. This is a safe default.

ENCRYPTION_READ_PATH_ENABLED: bool = os.getenv(
    "ENCRYPTION_READ_PATH_ENABLED", "false").lower() == "true"
