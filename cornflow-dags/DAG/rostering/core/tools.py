from datetime import datetime, timedelta


def get_hour_string_from_date_time(ts: datetime) -> str:
    """Returns the hour string for the given time slot"""
    return ts.strftime("%H:%M")


def get_hour_string_from_hour_minute(hour: int, minute: int) -> str:
    """Returns the hour string for the given time slot"""
    return str(hour).zfill(2) + ":" + str(minute).zfill(2)


def get_one_date(starting_date: datetime, weeks: int = 0, days: int = 0) -> datetime:
    """Returns a date from a starting date adding weeks and days"""
    return starting_date + timedelta(days=weeks * 7 + days)


def get_date_time_from_string(string: str) -> datetime:
    return datetime.strptime(string, "%Y-%m-%dT%H:%M")


def get_week_from_ts(ts: datetime) -> int:
    """Returns the integer value of the week for the given time slot"""
    return ts.isocalendar()[1]


def get_week_from_string(string: str) -> int:
    """ "Returns the integer value of the week for the given string"""
    return get_week_from_ts(get_date_time_from_string(string))
