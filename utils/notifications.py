from datetime import date, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .config import sender_email, sender_pw, notification_address, email_template
from dataclasses import dataclass
from utils.customers import Customer
from logger import setup_logging
from datetime import datetime
from zoneinfo import ZoneInfo
from .config import machine_tz
from utils.time import get_yesterdays_date
import json

logger = setup_logging(__name__)


@dataclass
class Email:
    message: MIMEMultipart
    customer: Customer
    customer_sales: list
    yesterdays_date: str
    total_revenue: float


def load_email_template(bucket, email_template):
    """
    Opens the email template JSON file from GCP and returns it as a python object.

    The email template filename is in the config file.

    Returns a default template if the file is not found.

    """

    blob = bucket.blob(email_template)
    logger.info(f"Reading email_template from: {email_template}")

    try:
        # download_as_bytes() returns the content, which we decode to a string
        email_template_string = blob.download_as_bytes().decode("utf-8")

        # 3. Load and return the JSON data
        data = json.loads(email_template_string)
        return data

    except Exception as e:
        # Handle cases where the file doesn't exist or is empty
        logger.error(f"Error opening email template. Returning default")

        return {
            "subject": "{customer_name} Daily Sales Report for {date}",
            "greeting": "Dear {customer_name},",
            "header": "Here's your sales summary for {date}:\n\n",
            "sign_off": "Thank you,",
            "signature": "The Underpin Team",
            "total_revenue": "Your total revenue from yesterday's sales:",
        }


def create_email_msg(sender_email, recipients, subject, body, html_body):
    message = MIMEMultipart("alternative")
    message["From"] = sender_email
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    if html_body:
        message.attach(MIMEText(html_body, "html"))
    return message


def create_email_obj(message, customer_sales, yesterdays_date, total_revenue, customer):
    email_obj = Email(
        message,
        customer,
        customer_sales,
        yesterdays_date,
        total_revenue,
    )
    return email_obj


def create_notifications(bucket, customer_sales_dict: dict):
    """
    Takes a dictionary of customers: Sends a notification to each customer containing their sales as well as the value of those sales.

    Args: customer_sales_dict (dict)

    Returns:
    A list of sales:
    list(sales_map.values()), notification_rows, sales_list, successfully_sent, failed_sends)

    """

    yesterdays_date = get_yesterdays_date()

    sales_list = []
    sales_map = {}
    messages = []

    et = load_email_template(bucket, email_template)

    for customer, sales in customer_sales_dict.items():
        # Email creation

        subject = et["subject"].format(
            customer_name=customer.name, date=yesterdays_date
        )
        greeting = et["greeting"].format(customer_name=customer.name) + "\n\n"
        header = et["header"].format(date=yesterdays_date) + "\n\n"
        body = greeting + header
        sign_off = et["sign_off"] + "\n"
        signature = et["signature"]
        total_revenue_msg = et["total_revenue"]

        recipients = [notification_address]
        recipients.append(customer.email)

        total_revenue = 0

        # Create HTML body
        html_body = f"""
      <html>
        <head>
          <style>
            body {{
              font-family: Arial, sans-serif;
              line-height: 1.6;
              color: #333;
            }}
            h2 {{
              color: #2c3e50;
            }}
              table {{
                  border-collapse: collapse;
                  width: auto;
                  margin: 20px 0;
              }}
              th {{
                  background-color: #3498db;
                  color: white;
                  padding: 12px 20px;
                  text-align: left;
                  font-weight: bold;
                  white-space: nowrap;
              }}
              td {{
                  padding: 10px 20px;
                  border-bottom: 1px solid #ddd;
              }}
              tr:hover {{
                  background-color: #f5f5f5;
              }}
              .total-row {{
                  font-weight: bold;
                  background-color: #ecf0f1;
                  font-size: 1.1em;
              }}
              .total-row td {{
                  padding: 15px 20px;
              }}
              td:nth-child(2), td:nth-child(3) {{
                  text-align: center;
              }}
              th:nth-child(2), th:nth-child(3) {{
                  text-align: center;
            }}
          </style>
        </head>
        <body>
          <h2>Daily Sales Report</h2>
          <p>{greeting}</p>
          <p>{header}</p>
          
          <table>
            <thead>
              <tr>
                <th>Product Name</th>
                <th>Quantity Sold</th>
                <th>Revenue</th>
              </tr>
            </thead>
            <tbody>
      """

        # Initialize a dictionary to combine the sales of the same product to add to the email body (rather than listing the product multiple times)
        combined_product_quantities = {}

        for sale in sales:
            product_name = sale["product_name"]
            revenue = round(sale["revenue"], 2)
            total_revenue += revenue
            quantity_sold = sale["quantity_sold"]

            sales_list.append(
                [
                    sale["transaction_dt"],
                    customer.name,
                    customer.email,
                    product_name,
                    quantity_sold,
                    revenue,
                ]
            )

            # Create a dictionary of products sold for every customer. Each customer gets one line per product. Update the product quantities dictionary which exists only within the loop for each customer to add the aggregated product sales to the email body.
            if product_name in sales_map.keys():
                new_quantity_sold = sales_map[product_name][4] + quantity_sold
                combined_product_quantities[product_name][0] += quantity_sold
                new_revenue = sales_map[product_name][5] + revenue
                combined_product_quantities[product_name][1] += revenue
                sales_map[product_name] = [
                    yesterdays_date,
                    customer.name,
                    customer.email,
                    product_name,
                    new_quantity_sold,
                    new_revenue,
                ]
            else:
                sales_map[product_name] = [
                    yesterdays_date,
                    customer.name,
                    customer.email,
                    product_name,
                    quantity_sold,
                    revenue,
                ]
                combined_product_quantities[product_name] = [quantity_sold, revenue]

        # Initialize a customer sales list to add the combined product quantities to.
        customer_sales = []

        # Go through the dictionary and add each product and the combined quanties to the html email body.
        for product in combined_product_quantities:
            customer_sales.append(
                f"{product} ({combined_product_quantities[product][0]}x)"
            )

            html_body += f"""
            <tr>
              <td>{product}</td>
              <td>{combined_product_quantities[product][0]}</td>
              <td>${combined_product_quantities[product][1]:.2f}</td>
            </tr>
        """
            body += f"{product} (Qty: {combined_product_quantities[product][0]}) - ${combined_product_quantities[product][1]}\n"

        # Add total row
        html_body += f"""
              <tr class="total-row">
                <td colspan="2">Total Revenue</td>
                <td>${total_revenue:.2f}</td>
              </tr>
            </tbody>
          </table>
          
          <p>{sign_off}<br>{signature}</p>
        </body>
      </html>
      """

        # Add to the plain text body
        body += f"{total_revenue_msg} {total_revenue}\n\n"
        body += f"{sign_off}\n"
        body += signature

        message = create_email_msg(sender_email, recipients, subject, body, html_body)
        messages.append(
            create_email_obj(
                message, customer_sales, yesterdays_date, total_revenue, customer
            )
        )

    itemized_receipt_rows = list(sales_map.values())
    return messages, itemized_receipt_rows, sales_list


def send_notifications(messages: list):
    """
    Accepts a list of Email objects, connects to GOOGLE SMTP and sends an email containing each message to the customer.

    Args:
    messages (list): A list of MIMEMultipart message objects \n

    Returns:

    itemized_receipt_rows(list): A list containing the sales for the customer- multiple sales for the same product are combined together so there is one line for each product. [yesterdays_date, customer.name, customer.email, product_name, quantity_sold, revenue] \n
    notification_rows (list): A list containing each notifcation and that status of whether or not it was successfully sent \n
    successfully_sent (int): The amount of messages that were succcessfully sent \n
    failed_sends (int): The amount of messages that failed to send.
    """

    notification_rows = []
    successfully_sent = 0
    failed_sends = 0

    try:

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_pw)
            logger.info("Connection success to GMAIL SMTP")

            if not messages or not messages[0].customer:
                return send_no_sales(server, messages[0], notification_rows)

            # Loop through the list of messages and then send them all.
            for message in messages:
                try:
                    server.send_message(message.message)
                    logger.info(
                        f"Email sent successfully to  {message.customer.name} at {message.customer.email} and {notification_address} "
                    )
                    successfully_sent += 1
                    notification_status = "sent"
                    notification_rows = add_notification_row(
                        notification_rows, message, notification_status
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to send email to {message.customer.name}: {str(e)}"
                    )
                    failed_sends += 1
                    notification_status = "failed"
                    notification_rows = add_notification_row(
                        notification_rows, message, notification_status
                    )

    except Exception as e:
        logger.error(f"Failed to connect to gmail service: {e}")
        return f"Failed to connect to gmail service: {e}"

    return notification_rows, successfully_sent, failed_sends


def send_no_sales(server, message, notification_rows):
    try:
        server.send_message(message.message)
        logger.info(f"Email sent successfully to {notification_address}")
        notification_row = add_notification_row(notification_rows, message, "sent")
        return notification_row, 1, 0
    except Exception as e:
        logger.error(f"Failed to send email to {notification_address}")
        notification_row = add_notification_row(notification_rows, message, "failed")
        return notification_row, 0, 1


def add_notification_row(notification_rows, message, notification_status):
    if message.customer:
        notification_rows.append(
            [
                message.yesterdays_date,
                message.customer.name,
                message.customer.email,
                ", ".join(message.customer_sales),
                message.total_revenue,
                notification_status,
            ]
        )
    else:
        notification_rows.append(
            [
                message.yesterdays_date,
                "Main Notification Address",
                notification_address,
                "No Sales",
                0,
                notification_status,
            ]
        )
    return notification_rows


def send_no_sales_notification():

    yesterdays_date = get_yesterdays_date()
    message = create_email_msg(
        sender_email,
        [notification_address],
        f"Daily Sales Notification Report {yesterdays_date}",
        f"Sales-Notification service completed successfully- No sales from {yesterdays_date}",
        None,
    )
    notification_rows, successfully_sent, failed_sends = send_notifications(
        [create_email_obj(message, [], yesterdays_date, 0, customer=None)]
    )
    return notification_rows
