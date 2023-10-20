from datetime import datetime, timedelta


def get_hour_string_from_date_time(ts: datetime) -> str:
    """Returns the hour string for the given time slot"""
    return ts.strftime("%H:%M")


def get_hour_string_from_hour_minute(hour: int, minute: int) -> str:
    """Returns the hour string for the given time slot"""
    return datetime.now().replace(hour=hour, minute=minute).strftime("%H:%M")


def get_one_date(starting_date: datetime, weeks: int = 0, days: int = 0) -> datetime:
    """Returns a date from a starting date adding weeks and days"""
    return starting_date + timedelta(days=weeks * 7 + days)
