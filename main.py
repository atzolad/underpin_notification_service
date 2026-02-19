from utils.sales import get_last_sales, get_daily_sales, group_sales_by_customer
from utils.customers import (
    load_customers,
    create_customer_list,
    get_customer_to_product_map,
    Customer,
)
from utils.products import load_product_costs, sanitize_product_name
from utils.notifications import (
    create_notifications,
    send_notifications,
    send_no_sales_notification,
)
from utils.config import (
    customer_file,
    product_file,
    machine_ids,
)
from utils.sheets import connect_sheets, write_to_sheet
import time
from logger import setup_logging
import os
from google.cloud import storage
import pprint
import psycopg


def main():

    # Calculate the start time
    program_start_time = time.time()

    logger = setup_logging(__name__)

    logger.info("Starting Main.py")

    # Use an environment variable to define the bucket name for Google Cloud Storage
    BUCKET_NAME = os.environ.get("CONFIG_BUCKET")

    # Initialize a list to store the combination of last sales from all machines.
    all_machine_last_sales = []

    # Loop through each machine in the list and add the last sales together.
    for machine_id in machine_ids:
        logger.info(f"Fetching sales for Machine ID: {machine_id}")
        try:
            machine_sales = get_last_sales(machine_id)
            all_machine_last_sales.extend(machine_sales)
        except Exception as e:
            logger.error(f"Error fetching sales for {machine_id}: {str(e)}")

    # Go through the last sales and find all sales from yesterday. End execution if not found.

    daily_sales = get_daily_sales(all_machine_last_sales)

    # Send a notification to main address and end program execution if no sales found.
    if not daily_sales:

        logger.info("No sales from yesterday. Ending program execution")
        notification_rows = send_no_sales_notification()

        try:
            sheet = connect_sheets()

        except Exception as e:
            logger.error(f"Error connecting to sheets: {e}")

        try:
            write_to_sheet(sheet, 0, notification_rows)
            logger.info(f"Wrote to Notification Sheet")

        except Exception as e:
            logger.error(f"Error writing to sheets: {str(e)}")

        return

    try:
        with psycopg.connect("dbname=underpin user=alexzolad") as conn:

            logger.info("Successfully connected to Postgres DB")

            # TODO - move these to functions.

            # Need to get just the customers from daily sales...
            daily_sales_products = list(
                set(sanitize_product_name(sale["ProductName"]) for sale in daily_sales)
            )
            print(daily_sales_products)
            customer_product_dict = {}
            product_costs = {}

            try:

                with conn.cursor() as cur:
                    cur.execute(
                        """
                    SELECT c.name, c.email, p.name, p.price
                    FROM customers AS c
                    JOIN customer_products AS cp on c.id = cp.customer_id
                    JOIN products AS p ON cp.product_id = p.id
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

                        if product not in customer_product_dict:
                            customer_product_dict[product] = Customer(
                                name=name, email=email, products=(product,)
                            )
                        else:
                            logger.warning(
                                f"Product {product} already in customer_product_dict"
                            )

                        if product not in product_costs:
                            product_costs[product] = product_cost

                        else:
                            logger.warning(
                                f"Product {product} already in product_costs"
                            )

            #     # Load customer and product info from files.
            #     customer_data = load_customers(conn)
            #     logger.info(f"Loaded customer info from {customer_file}")

            #     customers = create_customer_list(customer_data)
            #     logger.info(f"Created customer list of {len(customers)} customers")

            #     customer_product_dict = get_customer_to_product_map(customers)
            #     logger.info(
            #         f"Created dictionary of product keys with customer values for {len(customer_product_dict)} products"
            #     )

            #     product_costs = load_product_costs(bucket, product_file)
            #     logger.info(f"Loaded product data for {len(product_costs)} products")

            except Exception as e:
                logger.error(
                    f"Error loading customer and product info from db: {e}",
                    exc_info=True,
                )

    except Exception as e:
        logger.warning(f"Error connecting to Postgres DB: {e}")

    # try:

    #     # Initialize the storage client and bucket for Google Cloud- will be used for both load_customers and load_products
    #     storage_client = storage.Client()
    #     bucket = storage_client.bucket(BUCKET_NAME)

    #     # TODO open the DB connection - actually I should move the API request first so I only need to query for the customers that have products sold...

    #     # Load customer and product info from files.
    #     customer_data = load_customers(bucket, customer_file)
    #     logger.info(f"Loaded customer info from {customer_file}")

    #     customers = create_customer_list(customer_data)
    #     logger.info(f"Created customer list of {len(customers)} customers")

    #     customer_product_dict = get_customer_to_product_map(customers)
    #     logger.info(
    #         f"Created dictionary of product keys with customer values for {len(customer_product_dict)} products"
    #     )

    #     product_costs = load_product_costs(bucket, product_file)
    #     logger.info(f"Loaded product data for {len(product_costs)} products")

    # except Exception as e:
    #     logger.error(
    #         f"Error loading customer and product info from files: {e}", exc_info=True
    #     )

    logger.info(f"{len(daily_sales)} sales from yesterday")

    customer_sales_dict = group_sales_by_customer(
        daily_sales, customer_product_dict, product_costs
    )
    logger.info(f"Grouped sales for {len(customer_sales_dict)} customers")

    if len(customer_sales_dict) == 0:
        logger.error(f"Customer sales dictionary is empty")
        return

    notification_start_time = time.time()

    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    messages, itemized_receipt_rows, sales_list = create_notifications(
        bucket, customer_sales_dict
    )
    notification_rows, notification_success, notification_fail = send_notifications(
        messages
    )
    logger.info(
        f"Notifications sent: {notification_success} successful. {notification_fail} failed"
    )
    notification_end_time = time.time()
    notification_time = notification_end_time - notification_start_time
    logger.info(f"It took {notification_time} seconds to send notifications")

    # Calculate the start time
    connect_sheet_start = time.time()
    try:

        sheet = connect_sheets()

    except Exception as e:
        logger.error(f"Error connecting to sheets: {e}")

    connect_sheet_end = time.time()
    connect_sheet_time = connect_sheet_end - connect_sheet_start
    logger.info(f"It took {connect_sheet_time} seconds to connect to sheets")

    sheet_start_time = time.time()

    try:

        write_to_sheet(sheet, 0, notification_rows)
        logger.info(f"Wrote to Notification Sheet")
        write_to_sheet(sheet, 1, itemized_receipt_rows)
        logger.info(f"Wrote to Itemized Receipt Sheet")
        write_to_sheet(sheet, 2, sales_list)
        logger.info(f"Wrote to Transaction Log Sheet")

    except Exception as e:
        logger.error(f"Error writing to sheets: {str(e)}")

    sheet_end_time = time.time()
    sheet_write_time = sheet_end_time - sheet_start_time
    logger.info(f"It took {sheet_write_time} seconds to write to sheets ")

    program_end_time = time.time()
    program_run_time = program_end_time - program_start_time
    logger.info(f"It took, {program_run_time} seconds to run the whole program")
    logger.info(f"Program execution ended")


if __name__ == "__main__":
    main()
