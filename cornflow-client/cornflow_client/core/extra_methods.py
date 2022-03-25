# Import from external libraries
from datetime import datetime, timedelta


class DateExtraMethods:
    def __init__(self):
        pass

    @staticmethod
    def get_date_from_string(string: str) -> datetime:
        """
        Returns a datetime object from an hour-string in format 'YYYY-MM-DD'
        """
        return datetime.strptime(string, "%Y-%m-%d")

    @staticmethod
    def get_datetime_from_string(string: str) -> datetime:
        """
        Returns a datetime object from an hour-string in format 'YYYY-MM-DDTh:m'
        """
        return datetime.strptime(string, "%Y-%m-%dT%H:%M")

    @staticmethod
    def get_datetimesec_from_string(string: str) -> datetime:
        """
        Returns a datetime object from an hour-string in format 'YYYY-MM-DDTh:m:s'
        """
        return datetime.strptime(string, "%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def get_datetime_from_date_hour(date: str, hour: int) -> datetime:
        """
        Returns a datetime object from a date and an hour
        """
        if hour == 24:
            hour = 0
        return datetime.strptime(f"{date}T{hour}", "%Y-%m-%dT%H")

    @staticmethod
    def get_date_hour_from_string(string: str, zero_to_twenty_four=False):
        """
        Returns a tuple (date, hour) from an hour-string
        """
        date_t = DateExtraMethods.get_datetime_from_string(string)
        hour = date_t.strftime("%H")
        if hour == "00" and zero_to_twenty_four:
            hour = "24"
            date_t -= timedelta(days=1)
        date = date_t.strftime("%Y-%m-%d")
        return date, int(hour)

    @staticmethod
    def get_date_string_from_ts(ts: datetime) -> str:
        """Returns the string of a given date as 'YYYY-MM-DD'"""
        return datetime.strftime(ts, "%Y-%m-%d")

    @staticmethod
    def get_datetime_string_from_ts(ts: datetime) -> str:
        """Returns the string of a given date as 'YYYY-MM-DDTh:m'"""
        return datetime.strftime(ts, "%Y-%m-%dT%H:%M")

    @staticmethod
    def get_datetimesec_string_from_ts(ts: datetime) -> str:
        """Returns the string of a given date as 'YYYY-MM-DDTh:m:s'"""
        return datetime.strftime(ts, "%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def get_next_hour_datetime_string(string: str) -> str:
        """
        Returns the hour following the given hour, as a string
        """
        return (
            DateExtraMethods.get_datetime_from_string(string) + timedelta(hours=1)
        ).isoformat()

    @staticmethod
    def get_next_hour_datetimesec_string(string: str) -> str:
        """
        Returns the hour following the given hour, as a string
        """
        return (
            DateExtraMethods.get_datetimesec_from_string(string) + timedelta(hours=1)
        ).isoformat()

    @staticmethod
    def get_next_hour(ts: datetime) -> datetime:
        """
        Returns the hour following the given hour
        """
        return ts + timedelta(hours=1)

    @staticmethod
    def get_previous_hour_datetime_string(string: str) -> str:
        """
        Returns the hour preceding the given hour, as a string
        """
        return (
            DateExtraMethods.get_datetime_from_string(string) - timedelta(hours=1)
        ).isoformat()

    @staticmethod
    def get_previous_hour_datetimesec_string(string: str) -> str:
        """
        Returns the hour preceding the given hour, as a string
        """
        return (
            DateExtraMethods.get_datetimesec_from_string(string) - timedelta(hours=1)
        ).isoformat()

    @staticmethod
    def get_previous_hour(ts: datetime) -> datetime:
        """
        Returns the hour preceding the given hour
        """
        return ts - timedelta(hours=1)

    @staticmethod
    def get_date_string_from_ts_string(ts: str) -> str:
        """Returns the date in format 'YYYY-MM-DD' from a datetime string"""
        return ts[0:10]

    @staticmethod
    def get_hour_from_ts(ts: datetime) -> float:
        """Returns the hours (in number) of the given time slot"""
        return float(ts.hour + ts.minute / 60)

    @staticmethod
    def add_time_to_ts(ts: datetime, weeks=0, days=0, minutes=0, seconds=0) -> datetime:
        """Adds time to a datetime"""
        return ts + timedelta(days=7 * weeks + days, minutes=minutes, seconds=seconds)

    @staticmethod
    def add_time_to_date_string(
        string: str, weeks=0, days=0, minutes=0, seconds=0
    ) -> str:
        """Adds time to a datetime"""
        return DateExtraMethods.get_date_string_from_ts(
            DateExtraMethods.get_date_from_string(string)
            + timedelta(days=7 * weeks + days, minutes=minutes, seconds=seconds)
        )

    @staticmethod
    def add_time_to_datetime_string(
            string: str, weeks=0, days=0, minutes=0, seconds=0
    ) -> str:
        """Adds time to a datetime"""
        return DateExtraMethods.get_datetime_string_from_ts(
            DateExtraMethods.get_datetime_from_string(string)
            + timedelta(days=7 * weeks + days, minutes=minutes, seconds=seconds)
        )

    @staticmethod
    def add_time_to_datetimesec_string(
        string: str, weeks=0, days=0, hours=0, minutes=0, seconds=0
    ) -> str:
        """Adds time to a datetime"""
        return DateExtraMethods.get_datetimesec_string_from_ts(
            DateExtraMethods.get_datetimesec_from_string(string)
            + timedelta(days=7 * weeks + days, hours=hours, minutes=minutes, seconds=seconds)
        )

    @staticmethod
    def get_week_from_ts(ts: datetime) -> int:
        """Returns the integer value of the week for the given time slot"""
        return ts.isocalendar()[1]

    @staticmethod
    def get_week_from_date_string(string: str) -> int:
        """Returns the integer value of the week for the given string"""
        return DateExtraMethods.get_week_from_ts(
            DateExtraMethods.get_date_from_string(string)
        )

    @staticmethod
    def get_week_from_datetime_string(string: str) -> int:
        """Returns the integer value of the week for the given string"""
        return DateExtraMethods.get_week_from_ts(
            DateExtraMethods.get_datetime_from_string(string)
        )

    @staticmethod
    def get_week_from_datetimesec_string(string: str) -> int:
        """Returns the integer value of the week for the given string"""
        return DateExtraMethods.get_week_from_ts(
            DateExtraMethods.get_datetimesec_from_string(string)
        )

    @staticmethod
    def get_weekday_from_ts(ts: datetime) -> int:
        """ Returns the number of the weekday from a ts """
        return ts.isocalendar()[2]

    @staticmethod
    def get_weekday_from_date_string(string: str) -> int:
        """ Returns the number of the weekday from a date string in format 'YYYY-MM-DD' """
        return DateExtraMethods.get_date_from_string(string).isocalendar()[2]

    @staticmethod
    def get_weekday_from_datetime_string(string: str) -> int:
        """ Returns the number of the weekday from a date string in format 'YYYY-MM-DDTh:m' """
        return DateExtraMethods.get_datetime_from_string(string).isocalendar()[2]

    @staticmethod
    def get_weekday_from_datetimesec_string(string: str) -> int:
        """ Returns the number of the weekday from a date string in format 'YYYY-MM-DDT:h:m:s' """
        return DateExtraMethods.get_datetimesec_from_string(string).isocalendar()[2]

    @staticmethod
    def get_hour_from_datetime_string(string: str) -> float:
        """Returns the integer value of the hour (in number) from ts string in format 'YYYY-MM-DDTh:m'"""
        return DateExtraMethods.get_hour_from_ts(
            DateExtraMethods.get_datetime_from_string(string)
        )

    @staticmethod
    def get_hour_from_datetimesec_string(string: str) -> float:
        """Returns the integer value of the hour (in number) from ts string in format 'YYYY-MM-DDTh:m:s'"""
        return DateExtraMethods.get_hour_from_ts(
            DateExtraMethods.get_datetimesec_from_string(string)
        )


class ExtraMethods(DateExtraMethods):
    def __init__(self):
        DateExtraMethods.__init__(self)
