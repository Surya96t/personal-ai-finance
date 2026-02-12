import os
import inngest
import logging
from dotenv import load_dotenv

load_dotenv()

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Initialize the Inngest client
inngest_client = inngest.Inngest(
    app_id="personal-ai-finance",
    signing_key=os.getenv("INNGEST_SIGNING_KEY"),
    logger=logger,
)
