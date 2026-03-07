from utils.time import is_yesterday, is_before_yesterday, convert_gmt_pst
from utils.config import NAYAX_API_KEY
from logger import setup_logging
from utils.customers import load_customers
from utils.products import sanitize_product_name
import requests
import time

# For testing:
# from google.cloud import storage
# import os


logger = setup_logging(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


def get_last_sales(machine_id):
    """
    Function to connect to the Nayax api. Accepts the machine id to pass as a header. For example: 942488501.

    API should return the machines list of "last sales". Function returns this list in json format.

    Args:

    machine_id(str): "012345678"

    Returns:

    An list of sales from yesterday in JSON format.

    """

    url = f"https://lynx.nayax.com/operational/v1/machines/{machine_id}/lastSales"
    headers = {"Authorization": f"Bearer {NAYAX_API_KEY}", "accept": "application/json"}

    # Use an environment variable to define the bucket name for Google Cloud Storage
    # BUCKET_NAME = os.environ.get("CONFIG_BUCKET")
    # Initialize the storage client and bucket for Google Cloud
    # storage_client = storage.Client()
    # bucket = storage_client.bucket(BUCKET_NAME)

    # For testing without API connection
    # mock_last_sales_response = load_customers(bucket, "last_sales.json")
    # return mock_last_sales_response

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                last_sales = response.json()
                logger.info(
                    f"Successfully connected to LYNX API for machine {machine_id}"
                )
                return last_sales
            else:
                logger.error(
                    f"API error for machine {machine_id}: HTTP {response.status_code} (attempt {attempt}/{MAX_RETRIES})"
                )

        except requests.exceptions.RequestException as e:
            logger.error(
                f"HTTP request error for machine {machine_id}: {e} (attempt {attempt}/{MAX_RETRIES})"
            )

        if attempt < MAX_RETRIES:
            sleep_time = RETRY_BACKOFF_SECONDS * attempt
            logger.info(f"Retrying in {sleep_time}s...")
            time.sleep(sleep_time)

    logger.error(f"All {MAX_RETRIES} attempts failed for machine {machine_id}")
    return []


def get_daily_sales(last_sales: list):
    """
    Function takes the API returned list of last sales, uses the is_yesterday function to filter it and returns a new list of the sales from that day.

    Args: Last_sales (list)

    Returns: list of sales from yesterday.

    """
    daily_sales = []

    if last_sales is None:
        logger.warning(
            "last_sales is None -- API call likely failed. Returning empty daily sales."
        )
        return daily_sales

    if not isinstance(last_sales, list):
        logger.warning(f"Unexpected Data Format: {type(last_sales)}")
        return daily_sales

    for sale in last_sales:
        sale_date = sale.get("MachineAuthorizationTime", "No Authorization Date Time")

        if is_yesterday(sale_date):
            daily_sales.append(sale)

        elif is_before_yesterday(sale_date):
            break

    return daily_sales


def group_sales_by_customer(
    daily_sales: list, customer_product_dict: dict, product_costs: dict
):
    """
    Function returns a dictionary with the Customer name as the key and their sales as a list of sales.

    Args: daily_sales (list) \n
          customer_product_dict(dict)  - dictionary where the keys are products and the values are customer objects. \n
          product_costs (dict) - dictionary of {"product name": price (float)} \n

    Returns: Dict in the format: {"product name:" product, "settlement_value": settlement_value, "quantity_sold": quantity, "transaction_dt": datetime, "revenue": revenue (float)}
    """

    customer_sales_dict = {}

    for sale in daily_sales:
        product = sanitize_product_name(sale["ProductName"])
        settlement_value = sale["SettlementValue"]
        # API response seems to return everything with a quantity of 0 so I am making this 1 for now.
        # quantity = sale["Quantity"]
        quantity = 1
        # Avoid a key error if this product isn't in the product list
        if product in product_costs:
            revenue = product_costs[product] * quantity
        else:
            logger.error(f"Product {product} from sale not found in product list")
            revenue = 0.0
        # revenue = product_costs[product] * quantity
        transaction_dt = str(sale["MachineAuthorizationTime"])

        # Avoid a key error if this product isn't in the product list
        if product in customer_product_dict:
            customer = customer_product_dict.get(product)
        else:
            logger.error(f"Product {product} not found in Customer Product Dict")
            continue

        if customer:
            sale_info = {
                "product_name": product,
                "settlement_value": settlement_value,
                "quantity_sold": quantity,
                "transaction_dt": transaction_dt,
                "revenue": revenue,
            }

            if customer not in customer_sales_dict:
                customer_sales_dict[customer] = []
            customer_sales_dict[customer].append(sale_info)

    return customer_sales_dict


# For testing purposes
"""
test_date_1 = "2026-02-18T16:53:51.225Z"
test_date_2 = "2026-02-18T16:53:51.225Z"
test_date_3 = "2026-02-18T16:53:51.225Z"
test_date_4 = "2026-02-18T16:53:51.225Z"
test_date_5 = "2026-02-18T16:53:51.225Z"

test_date = "2026-02-18T16:53:51.225Z"


mock_last_sales_response = [
    {
        "TransactionID": 1,
        "PaymentServiceTransactionID": "PS12345678901",
        "PaymentServiceProviderName": "Stripe",
        "MachineID": 942488501,
        "MachineName": "Marshall Vending",
        "MachineNumber": "MV001",
        "InstituteLocationName": "New York Warehouse",
        "AuthorizationValue": 10.00,
        "SettlementValue": 9.50,
        "CurrencyCode": "USD",
        "PaymentMethod": "Credit Card",
        "RecognitionMethod": "Chip",
        "CardNumber": "************1234",
        "CardBrand": "Visa",
        "CLI": "+1234567890",
        "ProductName": "B Stickers RIGHT $3",
        "MultivendTransactionBit": "true",
        "MultivendNumverOfProducts": 2,
        "UnitOfMeasurement": "Item",
        "Quantity": 2,
        "EnergyConsumed": 0,
        "AuthorizationDateTimeGMT": test_date_1,
        "MachineAuthorizationTime": test_date_1,
        "SettlementDateTimeGMT": "2025-10-08T16:54:51.225Z",
        "SiteID": 2,
        "SiteName": "IL1",
    },
    {
        "TransactionID": 2,
        "PaymentServiceTransactionID": "PS12345678902",
        "PaymentServiceProviderName": "Stripe",
        "MachineID": 942488501,
        "MachineName": "Marshall Vending",
        "MachineNumber": "MV001",
        "InstituteLocationName": "New York Warehouse",
        "AuthorizationValue": 20.00,
        "SettlementValue": 19.50,
        "CurrencyCode": "USD",
        "PaymentMethod": "Credit Card",
        "RecognitionMethod": "Chip",
        "CardNumber": "************1234",
        "CardBrand": "Visa",
        "CLI": "+1234567890",
        "ProductName": "B Capsule BOTTOM $5",
        "MultivendTransactionBit": "true",
        "MultivendNumverOfProducts": 2,
        "UnitOfMeasurement": "Item",
        "Quantity": 2,
        "EnergyConsumed": 0,
        "AuthorizationDateTimeGMT": test_date_2,
        "MachineAuthorizationTime": test_date_2,
        "SettlementDateTimeGMT": "2025-10-08T16:54:51.225Z",
        "SiteID": 2,
        "SiteName": "IL1",
    },
    {
        "TransactionID": 3,
        "PaymentServiceTransactionID": "PS12345678903",
        "PaymentServiceProviderName": "Stripe",
        "MachineID": 942488501,
        "MachineName": "Marshall Vending",
        "MachineNumber": "MV001",
        "InstituteLocationName": "New York Warehouse",
        "AuthorizationValue": 30.00,
        "SettlementValue": 30.50,
        "CurrencyCode": "USD",
        "PaymentMethod": "Credit Card",
        "RecognitionMethod": "Chip",
        "CardNumber": "************1234",
        "CardBrand": "Visa",
        "CLI": "+1234567890",
        "ProductName": "B Capsule BOTTOM $5",
        "MultivendTransactionBit": "false",
        "MultivendNumverOfProducts": 1,
        "UnitOfMeasurement": "Item",
        "Quantity": 1,
        "EnergyConsumed": 0,
        "AuthorizationDateTimeGMT": test_date_3,
        "MachineAuthorizationTime": test_date_3,
        "SettlementDateTimeGMT": "2025-10-08T16:54:51.225Z",
        "SiteID": 2,
        "SiteName": "IL1",
    },
    {
        "TransactionID": 4,
        "PaymentServiceTransactionID": "PS12345678903",
        "PaymentServiceProviderName": "Stripe",
        "MachineID": 942488501,
        "MachineName": "Marshall Vending",
        "MachineNumber": "MV001",
        "InstituteLocationName": "New York Warehouse",
        "AuthorizationValue": 30.00,
        "SettlementValue": 30.50,
        "CurrencyCode": "USD",
        "PaymentMethod": "Credit Card",
        "RecognitionMethod": "Chip",
        "CardNumber": "************1234",
        "CardBrand": "Visa",
        "CLI": "+1234567890",
        "ProductName": "B Stickers RIGHT $3",
        "MultivendTransactionBit": "false",
        "MultivendNumverOfProducts": 1,
        "UnitOfMeasurement": "Item",
        "Quantity": 1,
        "EnergyConsumed": 0,
        "AuthorizationDateTimeGMT": test_date_4,
        "MachineAuthorizationTime": test_date_4,
        "SettlementDateTimeGMT": "2025-10-08T16:54:51.225Z",
        "SiteID": 2,
        "SiteName": "IL1",
    },
    {
        "TransactionID": 5,
        "PaymentServiceTransactionID": "PS12345678903",
        "PaymentServiceProviderName": "Stripe",
        "MachineID": 942488501,
        "MachineName": "Marshall Vending",
        "MachineNumber": "MV001",
        "InstituteLocationName": "New York Warehouse",
        "AuthorizationValue": 60.00,
        "SettlementValue": 60.50,
        "CurrencyCode": "USD",
        "PaymentMethod": "B Stickers RIGHT $3",
        "RecognitionMethod": "Chip",
        "CardNumber": "************1234",
        "CardBrand": "Visa",
        "CLI": "+1234567890",
        "ProductName": "Another New Test Item",
        "MultivendTransactionBit": "false",
        "MultivendNumverOfProducts": 1,
        "UnitOfMeasurement": "Item",
        "Quantity": 3,
        "EnergyConsumed": 0,
        "AuthorizationDateTimeGMT": test_date_5,
        "MachineAuthorizationTime": test_date_5,
        "SettlementDateTimeGMT": "2025-10-08T16:54:51.225Z",
        "SiteID": 2,
        "SiteName": "IL1",
    },
]
"""
