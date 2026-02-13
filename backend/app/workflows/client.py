import os
import inngest
import logging
from dotenv import load_dotenv

load_dotenv()

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

signing_key = os.getenv("INNGEST_SIGNING_KEY")

# Only enforce signing key if NOT in dev mode
if not signing_key and not os.getenv("INNGEST_DEV"):
    raise RuntimeError("INNGEST_SIGNING_KEY is missing or empty in environment variables.")

# Initialize the Inngest client
inngest_client = inngest.Inngest(
    app_id="personal-ai-finance",
    signing_key=signing_key,
    logger=logger,
)
