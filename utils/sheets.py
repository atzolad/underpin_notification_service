import gspread
import os
from logger import setup_logging

logger = setup_logging(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]


# The ID and range of a sample spreadsheet.
try:
    GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
    GOOGLE_SHEETS_NAME = os.getenv("GOOGLE_SHEETS_NAME")

except Exception as e:
    logger.error(f"error retrieving google sheet ID or Name: {e}")


def connect_sheets():

    creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

        # Define the scope
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Authenticate

    try:

        gc = gspread.service_account(creds_file, scopes=scopes)

        sheet = gc.open(GOOGLE_SHEETS_NAME)

    except Exception as e:
        logger.error(f"Error opening google sheet {GOOGLE_SHEETS_NAME}: {str(e)}")

    return sheet

def write_to_sheet(sheet, index, rows):
    '''
    Takes a sheet object from connect_sheets. Opens the worksheet at index and appends rows
    
    Args: 
    
    sheet (gspread obj): A sheets object returned from opening a google sheet. \n

    index (int): Index of the worksheet you want to write to. \n

    rows (list): A list including the values to write to the row. Example: [yesterdays_date, customer.name, customer.email, product_name, quantity_sold, revenue]
    
    '''

    try:
        worksheet = sheet.get_worksheet(index)
        worksheet.append_rows(rows)

    except Exception as e:
        logger.error(f"Error writing to sheet: {e}")

sheet = connect_sheets()