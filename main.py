from utils.sales import get_last_sales, get_daily_sales, group_sales_by_customer
from utils.customers import (
    get_customers_products,
)
from utils.notifications import (
    create_notifications,
    send_notifications,
    send_no_sales_notification,
)
from utils.config import (
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
    # all_machine_last_sales = []
    daily_sales = []

    # Loop through each machine in the list and add the last sales together.
    for machine_id in machine_ids:
        logger.info(f"Fetching sales for Machine ID: {machine_id}")
        try:
            machine_sales = get_last_sales(machine_id)
            daily_sales.extend(get_daily_sales(machine_sales))
            # print(f"machine_sales: \n {machine_sales}")
            # all_machine_last_sales.extend(machine_sales)
            # print(f"all_machine_last_sales: \n {all_machine_last_sales}")
        except Exception as e:
            logger.error(f"Error fetching sales for {machine_id}: {str(e)}")

    # Go through the last sales and find all sales from yesterday. End execution if not found.
    for sale in daily_sales:

        print(f"daily sale: \n {sale}")

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

            customer_product_dict, product_costs = get_customers_products(
                daily_sales=daily_sales, conn=conn
            )

    except Exception as e:
        logger.warning(f"Error connecting to Postgres DB: {e}")

    logger.info(f"{len(daily_sales)} sales from yesterday")
    print(f"Customer_product dict:  \n {customer_product_dict} \n")
    print(f"Product list: \n {product_costs}")

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
