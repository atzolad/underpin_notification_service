from dataclasses import dataclass
import json
from typing import List, Tuple
from .config import customer_file
from google.cloud import storage
from logger import setup_logging


logger = setup_logging(__name__)

@dataclass(frozen=True)
class Customer:
    name: str
    email: str
    products: Tuple[str,...]


def load_customers(bucket, customer_file = customer_file):
    '''
    Opens the customers json file and...

    Args:
        filename (str): Path to file containing json list of customers. Defaults to the customer_file in the config.

    Returns:
        An object containing the loaded JSON data. 
    '''

    blob = bucket.blob(customer_file)
    logger.info(f"Reading customers from: {customer_file}")

    try:
        # download_as_bytes() returns the content, which we decode to a string
        customer_string = blob.download_as_bytes().decode("utf-8")
        
        # 3. Load and return the JSON data
        customer_data = json.loads(customer_string)
        return customer_data
    
    except Exception as e:
        # Handle cases where the file doesn't exist or is empty
        logger.error(f"Error reading {customer_file} from GCS: {e}")
        return [] # Return empty list or handle the error

    # if os.path.exists(customer_file):
    #     try:
    #         with open (filename, "r") as file:
    #             customer_data = json.load(file)
    #         return customer_data
        
    #     except Exception as e:
    #         logger.error(f"Error opening customer file: {e}")
    #         return f"Error opening customer file: {e}"


def create_customer_list(customer_data):
    '''
    Loops through customers in customer_data JSON and creates a list of customer objects.
    
    Args:
    customer_data(python obj containing JSON data)

    Returns:
    A list of customer objects,

    '''

    if not customer_data:
        logger.warning("No customer data provided")
        return []
    
    customers = [
        Customer(c["name"], c["email"], tuple(c["products"]))
        for c in customer_data
    ]

    return customers

def get_customer_to_product_map(customers):
    '''
    Loops through the list of Customer objects and returns a new dictionary with the products as the keys and the Costumer objects as the values. To later search for the customer who owns a specific product. 

    Args:
        customers(list): A list of the customers returned from the create_customer_list() function. 

    Returns:
        A dicionary with the format "Product": "Customer"
    '''

    customer_product_dict = {}

    if not customers:
        logger.warning("No customers provided")
        return {}
    
    for customer in customers:
        for product in customer.products:
            customer_product_dict[product] = customer

    return customer_product_dict
