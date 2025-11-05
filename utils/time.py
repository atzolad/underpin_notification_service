from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from .config import machine_tz


def convert_gmt_pst(gmt_datetime: str, machine_tz: str = machine_tz) -> datetime:
    """
    Since the API returns GMT time, this function converts it to the local machine time.

    Args:

    gmt_datetime (str): Datetime string in ISO8601 format. Example: "2025-10-06T16:54:51.225Z" \n

    machine_tz (str): Timezone of the machine- defaults to the machine timezone from config if not specified. Excample: "America/Los_Angeles"


    Returns:

    A datetime string converted the machine's local timezone

    """
    gmt_dt = datetime.fromisoformat(gmt_datetime.replace("Z", "+00:00"))
    machine_dt = gmt_dt.astimezone(ZoneInfo(machine_tz))
    return machine_dt


def is_yesterday(sale_date):
    """
    Takes the sale date from the API response: "AuthorizationDateTimeGMT" and converts it to machine local time (PST) using the convert_gmt_pst function. Returns True if the date of the sale matches yesterdays date, False if not. Presuming this will run the next day to get all sales for the previous day.

    Args:

    sale_date (str): Datetime string in ISO8601 format. Example: "2025-10-06T16:54:51.225Z"

    Returns:

    Boolean

    """

    local_now = datetime.now(ZoneInfo(machine_tz))
    todays_date = local_now.date()

    yesterdays_date = todays_date - timedelta(days=1)
    # May need this if the API actually returns the local time and not the GMT time- according to docs it is GMT.
    # date_datetime = datetime.fromisoformat(sale_date.replace("Z", "+00:00"))
    # dt_sale_date = date_datetime.date()
    machine_sale_dt = convert_gmt_pst(sale_date)
    machine_sale_date = machine_sale_dt.date()
    # print(f"sale_date: {sale_date}, dt_sale_date: {dt_sale_date}, todays_date: {todays_date}")
    # print(f"sale_date: {sale_date}, machine_sale_dt: {machine_sale_dt}, machine_sale_date: {machine_sale_date}, todays_date: {todays_date}")
    if machine_sale_date == yesterdays_date:
        return True
    else:
        return False


def is_before_yesterday(sale_date):
    """
    Compares the passed in date to yesterdays date. If it is before, it returns True. Since the API response should be ordered, we shouldn't need to keep parsing the list once it hits a date before yesterday.

    Args:

    sale_date (str): Datetime string in ISO8601 format. Example: "2025-10-06T16:54:51.225Z"

    Returns:

    Boolean
    """

    local_now = datetime.now(ZoneInfo(machine_tz))
    todays_date = local_now.date()

    yesterdays_date = todays_date - timedelta(days=1)
    # May need this if the API actually returns the local time and not the GMT time- according to docs it is GMT.
    # date_datetime = datetime.fromisoformat(sale_date.replace("Z", "+00:00"))
    # dt_sale_date = date_datetime.date()
    machine_sale_dt = convert_gmt_pst(sale_date)
    machine_sale_date = machine_sale_dt.date()
    # print(f"sale_date: {sale_date}, dt_sale_date: {dt_sale_date}, todays_date: {todays_date}")
    # print(f"sale_date: {sale_date}, machine_sale_dt: {machine_sale_dt}, machine_sale_date: {machine_sale_date}, todays_date: {todays_date}")
    if machine_sale_date < yesterdays_date:
        return True
    else:
        return False


def get_yesterdays_date():
    local_now = datetime.now(ZoneInfo(machine_tz))
    todays_date = local_now.date()

    yesterdays_date = (todays_date - timedelta(days=1)).strftime(
        "%m-%d-%Y"
    )  # Formats yesterdays date in the traditional mo/day/year format

    return yesterdays_date
