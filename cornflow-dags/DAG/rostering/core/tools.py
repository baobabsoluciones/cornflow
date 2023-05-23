from datetime import datetime, timedelta


def get_date_from_string(string: str) -> datetime:
    return datetime.strptime(string, "%Y-%m-%d")


def get_date_time_from_string(string: str) -> datetime:
    return datetime.strptime(string, "%Y-%m-%dT%H%M")


def get_date_string_from_ts(ts: datetime) -> str:
    """Returns the string of a given date"""
    return datetime.strftime(ts, "%Y-%m-%d")


def get_hour_from_date_time(ts: datetime) -> float:
    """Returns the hours (in number) of the given time slot"""
    return float(ts.hour + ts.minute / 60)


def get_hour_string_from_date_time(ts: datetime) -> str:
    """Returns the hour string for the given time slot"""
    return ts.strftime("%H:%M")


def get_hour_string_from_hour_minute(hour: int, minute: int) -> str:
    """Returns the hour string for the given time slot"""
    return datetime.now().replace(hour=hour, minute=minute).strftime("%H:%M")


def get_one_date(starting_date: datetime, weeks: int = 0, days: int = 0) -> datetime:
    """Returns a date from a starting date adding weeks and days"""
    return starting_date + timedelta(days=weeks * 7 + days)


def get_time_slot_string(ts: datetime) -> str:
    """Returns the string of a given time slot"""
    return datetime.strftime(ts, "%Y-%m-%dT%H%M")


def get_week_from_string(string: str) -> int:
    """ "Returns the integer value of the week for the given string"""
    return get_week_from_ts(get_date_time_from_string(string))


def get_week_from_ts(ts: datetime) -> int:
    """Returns the integer value of the week for the given time slot"""
    return ts.isocalendar()[1]
