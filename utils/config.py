import os
from dotenv import load_dotenv
from logger import setup_logging

logger = setup_logging(__name__)

load_dotenv()

NAYAX_API_KEY = os.environ.get("NAYAX_API_KEY", "default")

if not NAYAX_API_KEY:
    logger.error(f"Missing Nayax API key.")
    raise EnvironmentError("Missing Nayax API key. Please set NAYAX_API_KEY")

machine_ids = ["567219276", "791321280"]

# The JSON file storing customer data
customer_file = "customers.json"

# The file containing the product prices
product_file = "products.json"

# The file containing the email template
email_template = "email-template.json"

# The local timezone of the machines
machine_tz = "America/Los_Angeles"

# Gmail login info
sender_email = os.environ.get("GMAIL_ADDRESS")
sender_pw = os.environ.get("GMAIL_APP_PW")

if not sender_email or not sender_pw:
    logger.error("Missing Gmail credentials. Please set GMAIL_ADDRESS and GMAIL_APP_PW")
    raise EnvironmentError(
        "Missing Gmail credentials. Please set GMAIL_ADDRESS and GMAIL_APP_PW."
    )

# Notification parameters
notification_address = os.eniron.get("NOTIFICATION_ADDRESS")
