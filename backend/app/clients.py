# backend/app/clients.py

import os
import inngest
import inngest.fast_api
import logging

# 1. Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 2. Initialize the client.
# The SDK is designed to automatically detect INNGEST_DEV=1 from the environment.
# All other logic was incorrect.
inngest_client = inngest.Inngest(
    app_id="personal-ai-finance",
    signing_key=os.getenv("INNGEST_SIGNING_KEY"),
    logger=logger,
)
