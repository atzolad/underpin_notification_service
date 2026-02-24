from dataclasses import dataclass
import json
from typing import List, Tuple
from .config import customer_file
from google.cloud import storage
from logger import setup_logging
from utils.products import sanitize_product_name
import os


logger = setup_logging(__name__)


@dataclass(frozen=True)
class Customer:
    name: str
    email: str
    products: Tuple[str, ...]


# def load_customers(bucket, customer_file=customer_file):
#     """
#     Opens the customers json file and...

#     Args:
#         filename (str): Path to file containing json list of customers. Defaults to the customer_file in the config.

#     Returns:
#         An object containing the loaded JSON data.
#     """

#     blob = bucket.blob(customer_file)
#     logger.info(f"Reading customers from: {customer_file}")

#     try:
#         # download_as_bytes() returns the content, which we decode to a string
#         customer_string = blob.download_as_bytes().decode("utf-8")

#         # 3. Load and return the JSON data
#         customer_data = json.loads(customer_string)
#         return customer_data

#     except Exception as e:
#         # Handle cases where the file doesn't exist or is empty
#         logger.error(f"Error reading {customer_file} from GCS: {e}")
#         return []  # Return empty list


def load_customers(conn):
    """
    Opens the customers json file and...

    Args:
        filename (str): Path to file containing json list of customers. Defaults to the customer_file in the config.

    Returns:
        An object containing the loaded JSON data.
    """

    # blob = bucket.blob(customer_file)
    # logger.info(f"Reading customers from: {customer_file}")

    # with conn.cursor as curr:

    # try:
    #     # download_as_bytes() returns the content, which we decode to a string
    #     customer_string = blob.download_as_bytes().decode("utf-8")

    #     # 3. Load and return the JSON data
    #     customer_data = json.loads(customer_string)
    #     return customer_data

    # except Exception as e:
    #     # Handle cases where the file doesn't exist or is empty
    #     logger.error(f"Error reading {customer_file} from GCS: {e}")
    #     return []  # Return empty list


def create_customer_list(customer_data):
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

    customers = [
        Customer(c["name"], c["email"], tuple(c["products"])) for c in customer_data
    ]

    return customers


def get_customer_to_product_map(customers):
    """
    Loops through the list of Customer objects and returns a new dictionary with the products as the keys and the Costumer objects as the values. To later search for the customer who owns a specific product.

    Args:
        customers(list): A list of the customers returned from the create_customer_list() function.

    Returns:
        A dicionary with the format "Product": "Customer"
    """

    customer_product_dict = {}

    if not customers:
        logger.warning("No customers provided")
        return {}

    for customer in customers:
        for product in customer.products:
            customer_product_dict[product] = customer

    return customer_product_dict


def get_customers_products(daily_sales, conn) -> tuple[dict, dict]:
    daily_sales_products = list(
        set(sanitize_product_name(sale["ProductName"]) for sale in daily_sales)
    )
    print(daily_sales_products)

    notification_address = os.environ.get("NOTIFICATION_ADDRESS")
    customer_product_dict = {}
    product_costs = {}

    try:

        with conn.cursor() as cur:
            cur.execute(
                """
                    SELECT c.name, c.email, p.name, p.price
                    FROM customers AS c
                    JOIN customer_products AS cp on c.id = cp.customer_id
                    RIGHT JOIN products AS p ON cp.product_id = p.id
                    WHERE p.name = ANY(%s)

                    """,
                (daily_sales_products,),
            )

            customer_data = cur.fetchall()

            for customer in customer_data:
                name = customer[0]
                email = customer[1]
                product = customer[2]
                product_cost = customer[3]

                if product not in product_costs:
                    product_costs[product] = product_cost

                else:
                    logger.warning(f"Product {product} already in product_costs")

                if name:

                    if product not in customer_product_dict:
                        customer_product_dict[product] = Customer(
                            name=name, email=email, products=(product,)
                        )
                    else:
                        logger.warning(
                            f"Product {product} already in customer_product_dict"
                        )
                else:
                    customer_product_dict[product] = Customer(
                        name="Underpin Vending- No Customer",
                        email=notification_address,
                        products=(product,),
                    )

        return customer_product_dict, product_costs

    except Exception as e:
        logger.error(
            f"Error loading customer and product info from db: {e}",
            exc_info=True,
        )
