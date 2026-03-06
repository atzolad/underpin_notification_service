from dataclasses import dataclass
import json
from typing import List, Tuple
from .config import customer_file
from google.cloud import storage
import os
from logger import setup_logging


logger = setup_logging(__name__)

notification_address = os.environ.get("NOTIFICATION_ADDRESS")
if not notification_address:
    logger.warning(
        "NOTIFICATION_ADDRESS env var is not set. Productless customer notifications will fail."
    )


@dataclass(frozen=True)
class Customer:
    name: str
    email: str
    products: Tuple[str, ...]


def load_customers(bucket, customer_file=customer_file):
    """
    Opens the customers json file and...

    Args:
        filename (str): Path to file containing json list of customers. Defaults to the customer_file in the config.

    Returns:
        An object containing the loaded JSON data.
    """

    blob = bucket.blob(customer_file)
    logger.info(f"Reading customers from: {customer_file}")

    try:
        # download_as_bytes() returns the content, which we decode to a string
        customer_string = blob.download_as_bytes().decode("utf-8")

        customer_data = json.loads(customer_string)
        return customer_data

    except Exception as e:
        # Handle cases where the file doesn't exist or is empty
        logger.error(f"Error reading {customer_file} from GCS: {e}")
        return []


def create_customer_list(customer_data, products_set):
    """
    Loops through customers in customer_data JSON and creates a list of customer objects.

    Args:
    customer_data(python obj containing JSON data)

    Returns:
    A list of customer objects,

    """

    if not customer_data:
        logger.warning("No customer data provided")
        return []

    customers = []
    customer_owned_products = set()

    for customer in customer_data:

        name = customer.get("name")
        email = customer.get("email")
        products = customer.get("products", [])

        if not name or not email:
            logger.warning(
                f"Skipping malformed customer record (missing name or email): {customer}"
            )
            continue

        new_customer = Customer(name, email, tuple(products))

        customers.append(new_customer)
        customer_owned_products.update(customer["products"])

    # customers = [
    #     Customer(c["name"], c["email"], tuple(c["products"])) for c in customer_data
    # ]

    customerless_products = find_customerless_products(
        products_set, customer_owned_products
    )

    if customerless_products:

        # I am creating a customer to store all the products not tied to actual customers. I will send these notifications to the main address.
        main_notification_customer = Customer(
            "Underpin Vending- No Customer",
            notification_address,
            tuple(customerless_products),
        )

        customers.append(main_notification_customer)

    return customers


def find_customerless_products(products_set, customer_owned_products):
    return products_set - customer_owned_products


def get_customer_to_product_map(customers):
    """
    Loops through the list of Customer objects and returns a new dictionary with the products as the keys and the Costumer objects as the values. To later search for the customer who owns a specific product.

    Args:
        customers(list): A list of the customers returned from the create_customer_list() function.

    Returns:
        A dicionary with the format "Product": "Customer"
        A set containing the products owned by all the customers.
    """

    customer_product_dict = {}

    if not customers:
        logger.warning("No customers provided")
        return {}

    for customer in customers:
        for product in customer.products:
            customer_product_dict[product] = customer

    return customer_product_dict
