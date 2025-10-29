import json
from .config import product_file
from logger import setup_logging
#import os

logger = setup_logging(__name__)

def load_product_costs(bucket, product_file = product_file):
    '''
    Opens the products json file and returns a dictionary in the format {"product name": price}. Example: {"Sticker Left" : 5.00 }

    Args: filename (str) default = product_file from config. 

    Returns: dictionary in the format: {"product name": price}. Example: {"Sticker Left" : 5.00 }
    '''

    blob = bucket.blob(product_file)
    logger.info(f"Reading products from: {product_file}")

    try:
        # download_as_bytes() returns the content, which we decode to a string
        products_string = blob.download_as_bytes().decode("utf-8")
        
        # 3. Load and return the JSON data
        product_data = json.loads(products_string)
        return {item['name']: item['price'] for item in product_data}
    
    except Exception as e:
        # Handle cases where the file doesn't exist or is empty
        logger.error(f"Error reading {product_file} from GCS: {e}")
        return [] # Return empty list or handle the error


    # if os.path.exists(product_file):

    #     try:

    #         with open (filename, "r") as file:
    #             product_data = json.load(file)

    #         return {item['name']: item['price'] for item in product_data}
        
    #     except Exception as e:
    #         logger.error(f"Error opening product file: {e}")
    #         return(f"Error opening product file: {e}")
        
    # logger.error(f"{product_file} not found")
    # return(f"{product_file} not found")