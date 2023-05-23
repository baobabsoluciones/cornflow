"""

"""
# Imports from libraries
from datetime import datetime, timedelta
import os
import pickle
from pytups import SuperDict, TupList
from typing import Dict, Tuple
from math import ceil

# Imports from cornflow libraries
from cornflow_client import InstanceCore
from cornflow_client.core.tools import load_json
from .const import INSTANCE_KEYS_RELATION

# Imports from internal modules
from .tools import (
    get_date_from_string,
    get_date_string_from_ts,
    get_hour_from_date_time,
    get_hour_string_from_date_time,
    get_hour_string_from_hour_minute,
    get_one_date,
    get_time_slot_string,
    get_week_from_ts,
)


class Instance(InstanceCore):
    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/instance.json")
    )
    schema_checks = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/instance_checks.json")
    )

    def __init__(self, data: dict):
        super().__init__(data)

        # Stores a list of the starting date of each week ordered
        self.opening_days = set()
        self.weeks = TupList()

        # First object stores a list of the dates ordered,
        # the second the properties for each date.
        self.dates = TupList()
        self.dates_properties = SuperDict()

        # First object stores a list of the time slots ordered,
        # the second the properties for each one.
        self.time_slots = TupList()
        self.time_slots_properties = SuperDict()

        self.cache_properties()

    @classmethod
    def from_dict(cls, data: dict) -> "Instance":
        tables = ["employees", "shifts", "contracts"]

        data_p = {el: {v["id"]: v for v in data[el]} for el in tables}

        data_p["demand"] = {(el["day"], el["hour"]): el for el in data["demand"]}
        data_p["weekly_schedule"] = TupList(
            (el["week_day"], el["starting_hour"], el["ending_hour"])
            for el in data["weekly_schedule"]
        ).to_dict(indices=[0], result_col=[1, 2])

        if "schedule_exceptions" in data:
            data_p["schedule_exceptions"] = TupList(
                (el["date"], el["starting_hour"], el["ending_hour"])
                for el in data["schedule_exceptions"]
            ).to_dict(indices=[0], result_col=[1, 2])
        else:
            data_p["schedule_exceptions"] = SuperDict({})

        data_p["parameters"] = pickle.loads(pickle.dumps(data["parameters"], -1))
        data_p["requirements"] = pickle.loads(pickle.dumps(data["requirements"], -1))

        if data.get("skill_demand"):
            data_p["skill_demand"] = {
                (el["day"], el["hour"], el["id_skill"]): el
                for el in data["skill_demand"]
            }
        else:
            data_p["skill_demand"] = SuperDict({})

        if data.get("skills"):
            data_p["skills"] = {el["id"]: el for el in data["skills"]}
        else:
            data_p["skills"] = SuperDict({})

        if data.get("skills_employees"):
            data_p["skills_employees"] = TupList(data["skills_employees"]).to_dict(
                result_col=["id_employee"], is_list=True, indices=["id_skill"]
            )
        else:
            data_p["skills_employees"] = SuperDict({})

        if data.get("employee_holidays"):
            data_p["employee_holidays"] = {
                (el["id_employee"], el["day"]): el for el in data["employee_holidays"]
            }
        else:
            data_p["employee_holidays"] = SuperDict({})

        if data.get("store_holidays"):
            data_p["store_holidays"] = {
                (el["day"]): el for el in data["store_holidays"]
            }
        else:
            data_p["store_holidays"] = SuperDict({})

        if data.get("employee_downtime"):
            data_p["employee_downtime"] = {
                (el["id_employee"], el["day"]): el for el in data["employee_downtime"]
            }
        else:
            data_p["employee_downtime"] = SuperDict({})

        if data.get("employee_preferences"):
            data_p["employee_preferences"] = {
                (el["id_employee"], el["day"], el["hours"], el["start"]): el
                for el in data["employee_preferences"]
            }
        else:
            data_p["employee_preferences"] = SuperDict({})

        return cls(data_p)

    def to_dict(self) -> Dict:
        tables = [
            "employees",
            "shifts",
            "contracts",
            "demand",
            "skill_demand",
            "skills",
            "employee_holidays",
            "employee_downtime",
            "store_holidays",
            "employee_preferences",
        ]

        data_p = {el: self.data[el].values_l() for el in tables}

        data_p["parameters"] = self.data["parameters"]
        data_p["requirements"] = self.data["requirements"]

        data_p["weekly_schedule"] = [
            {"week_day": d, "starting_hour": h_ini, "ending_hour": h_end}
            for d, value in self.data["weekly_schedule"].items()
            for (h_ini, h_end) in value
        ]

        data_p["schedule_exceptions"] = [
            {"date": d, "starting_hour": h_ini, "ending_hour": h_end}
            for d, value in self.data["schedule_exceptions"].items()
            for (h_ini, h_end) in value
        ]

        data_p["skills_employees"] = [
            dict(id_employee=id_employee, id_skill=id_skill)
            for id_skill in self.data["skills_employees"]
            for id_employee in self.data["skills_employees"][id_skill]
        ]
        data_p["employee_holidays"] = [
            dict(id_employee=id_employee, day=day)
            for (id_employee, day) in self.data["employee_holidays"]
        ]
        data_p["store_holidays"] = [
            dict(day=day) for (day) in self.data["store_holidays"]
        ]
        data_p["employee_downtime"] = [
            dict(id_employee=id_employee, day=day)
            for (id_employee, day) in self.data["employee_downtime"]
        ]
        data_p["employee_preferences"] = [
            dict(id_employee=id_employee, day=day, hours=hours, start=start)
            for (id_employee, day, hours, start) in self.data["employee_preferences"]
        ]
        return pickle.loads(pickle.dumps(data_p, -1))

    def cache_properties(self):
        """Caches the list of weeks, dates and time slots and its associated properties"""

        self.weeks = self._get_weeks()
        self.opening_days = self._get_opening_days()
        self.dates = self._get_dates()
        self.dates_properties = self._get_dates_properties()
        self.time_slots = self._get_time_slots()
        self.time_slots_properties = self._get_time_slots_properties()

    def check(self) -> dict:
        return SuperDict(
            incoherent_foreign_keys=self.check_indexes_coherence(),
            timeslot_length=self.check_timeslot_length(),
            **self.check_timeslot_coherence()
        ).vfilter(lambda v: len(v))

    def check_indexes_coherence(self) -> list:
        errors = list()
        for pk, fk_list in INSTANCE_KEYS_RELATION.items():
            for fk_table, fk_column in fk_list:
                fk_values = self._get_property(fk_table, fk_column).values_tl()
                for fk in fk_values:
                    if fk not in self._get_property(pk[0], pk[1]).values_tl():
                        errors.append(
                            {
                                "primary_table": pk[0],
                                "foreign_table": fk_table,
                                "key": fk_column,
                                "value": fk,
                            }
                        )

        return errors

    def check_timeslot_length(self):
        slot_length = self._get_slot_length()
        if slot_length not in [15, 30, 60]:
            return dict(
                timeslot_length=slot_length
            )
        return dict()

    def check_timeslot_coherence(self):
        checks = SuperDict(
            weekly_schedule_timeslots=TupList(),
            schedule_exceptions_timeslots=TupList(),
            shift_hours_timeslots=TupList(),
            employee_preferences_timeslots=TupList()
        )
        slot_length = self._get_slot_length()
        weekly_schedule = self._get_weekly_schedule(round_ts=False)
        schedule_exceptions = self._get_schedule_exceptions(round_ts=False)
        contract_start_hours = self._get_employees_contract_starting_hour(round_ts=False)
        contract_end_hours = self._get_employees_contract_ending_hour(round_ts=False)
        employee_preferences = self._get_employee_preferences()

        for key, values in weekly_schedule.items():
            checks["weekly_schedule_timeslots"] += TupList(
                {
                    "weekday": key,
                    "hour": get_hour_string_from_hour_minute(hour=v[0], minute=v[1])
                }
                for v in values
                if v[1] % slot_length != 0
            ) + TupList(
                {
                    "weekday": key,
                    "hour": get_hour_string_from_hour_minute(hour=v[2], minute=v[3])
                }
                for v in values
                if v[3] % slot_length != 0
            )

        for key, values in schedule_exceptions.items():
            checks["schedule_exceptions_timeslots"] += TupList(
                {
                    "date": key,
                    "hour": get_hour_string_from_hour_minute(hour=v[0], minute=v[1])
                }
                for v in values
                if v[1] % slot_length != 0
            ) + TupList(
                {
                    "date": key,
                    "hour": get_hour_string_from_hour_minute(hour=v[2], minute=v[3])
                }
                for v in values
                if v[3] % slot_length != 0
            )

        checks["shift_hours_timeslots"] += TupList(
            {"week": week, "employee": employee, "hour": hour}
            for (week, employee), hour in contract_start_hours.items()
            if int(hour[3:]) % slot_length != 0
        ) + TupList(
            {"week": week, "employee": employee, "hour": hour}
            for (week, employee), hour in contract_end_hours.items()
            if int(hour[3:]) % slot_length != 0
        )

        checks["employee_preferences_timeslots"] += TupList(
            {"date": date, "employee": employee, "hour": hour_string}
            for (employee, date, _, hour_string) in employee_preferences
            if int(hour_string[3:]) % slot_length != 0
        )

        return checks.vfilter(lambda v: len(v))

    def _get_weeks(self) -> TupList:
        """
        Returns a TupList with the starting date of each week in date time format
        For example: [datetime(2021, 9, 6, 0, 0, 0), datetime(2021, 9, 13, 0, 0, 0), ...]
        """
        return TupList(
            [
                get_one_date(self._get_start_date(), weeks=i)
                for i in range(0, self._get_horizon())
            ]
        ).sorted()

    def _get_opening_days(self):
        """
        Returns a set of the days of the week that the wc opens.
        For example (Monday, Tuesday)
        """
        return set(self._get_weekly_schedule().keys())

    def _get_dates(self) -> TupList:
        """
        Returns a TupList with the dates of the whole horizon when the center opens in datetime format
        For example: [datetime(2021, 9, 6, 0, 0, 0), datetime(2021, 9, 7, 0, 0, 0), ...]
        """

        return (
            TupList(
                self._get_start_date() + timedelta(days=d)
                for d in range(self._get_horizon() * 7)
            )
            .vfilter(lambda v: v.isoweekday() in self.opening_days)
            .sorted()
        )

    def _get_dates_properties(self) -> SuperDict:
        """
        Returns a SuperDict with dates as key and its dict properties as a value
        For example: {datetime(2021, 9, 6, 0, 0, 0): {"string": "2021-09-06", "week": 36}, ...}
        """
        return SuperDict(
            {
                date: {
                    "string": get_date_string_from_ts(date),
                    "week": get_week_from_ts(date),
                }
                for date in self.dates
            }
        )

    def _get_date_string_from_date(self, date):
        """Returns the date string of a given date"""
        return self.dates_properties[date]["string"]

    def _get_week_from_date(self, date):
        """Returns the week number of a given date"""
        return self.dates_properties[date]["week"]

    def _get_time_slots(self) -> TupList:
        """
        Returns a TupList with the time slots of the whole horizon in datetime format
        For example: [datetime(2021, 9, 6, 7, 0, 0), datetime(2021, 9, 6, 8, 0, 0), ...]
        """
        weekly_schedule = self._get_weekly_schedule()
        date_shift = {date: weekly_schedule[date.isoweekday()] for date in self.dates}

        ts = (
            TupList(
                key + timedelta(hours=h_start, minutes=m_start + self._get_slot_length() * x)
                for key, value in date_shift.items()
                for (h_start, m_start, h_end, m_end) in value
                for x in range(int(self._minutes_to_slot(60 * h_end + m_end - 60 * h_start - m_start)))
            )
            .vfilter(
                # Remove schedule exceptions.
                lambda v: get_date_string_from_ts(v)
                not in self._get_schedule_exceptions()
            )
            .vfilter(
                lambda v: get_date_string_from_ts(v) not in self._get_store_holidays()
            )
        )

        ts_schedule_exceptions = TupList(
            get_date_from_string(d)
            + timedelta(hours=h_start, minutes=m_start + self._get_slot_length() * x)
            for d, value in self._get_schedule_exceptions().items()
            for (h_start, m_start, h_end, m_end) in value
            for x in range(int(self._minutes_to_slot(60 * h_end + m_end - 60 * h_start - m_start)))
        )
        # In case some shift overlap we apply unique
        ts_total = (ts + ts_schedule_exceptions).unique2().sorted()

        return ts_total

    def _get_time_slots_properties(self) -> SuperDict:
        """
        Returns a SuperDict with the time slots as key and their properties dict as a value
        For example: {datetime(2021, 9, 6, 7, 0, 0): {"string": "2021-09-06T07:00",
            "date": "2021-09-06", "week": 36, "hour": 7.0}, ...}
        """
        return SuperDict(
            {
                ts: {
                    "string": get_time_slot_string(ts),
                    "date": get_date_string_from_ts(ts),
                    "week": get_week_from_ts(ts),
                    "hour": get_hour_from_date_time(ts),
                    "hour_string": get_hour_string_from_date_time(ts)
                }
                for ts in self.time_slots
            }
        )

    def get_time_slot_string(self, ts):
        """Returns the time slot string of a given time slot"""
        return self.time_slots_properties[ts]["string"]

    def _get_date_string_from_ts(self, ts):
        """Returns the date string of a given time slot"""
        return self.time_slots_properties[ts]["date"]

    def _get_week_from_ts(self, ts):
        """Returns the week number of a given time slot"""
        return self.time_slots_properties[ts]["week"]

    def _get_hour_from_ts(self, ts):
        """Returns the hour of a given time slot"""
        return self.time_slots_properties[ts]["hour"]

    def _get_hour_string_from_ts(self, ts):
        """Returns the hour of a given time slot"""
        return self.time_slots_properties[ts]["hour_string"]

    def _get_hour_from_hour_string(self, st):
        """Returns a float corresponding to the given hour"""
        return int(st[:2]) + int(st[3:]) / 60

    def _get_employees(self, prop) -> SuperDict:
        """Returns a SuperDict with the employee id as key and the prop as value"""
        return self._get_property("employees", prop)

    def _get_contracts(self, prop) -> SuperDict:
        """Returns a SuperDict with the contract id as key and the prop as value"""
        return self._get_property("contracts", prop)

    def _get_shifts(self, prop) -> SuperDict:
        """Returns a SuperDict with the shift id as key and the prop as value"""
        return self._get_property("shifts", prop)

    def _get_horizon(self) -> int:
        """Returns the value of the horizon parameter"""
        return self.data["parameters"]["horizon"]

    def _get_weekly_schedule(self, round_ts=True):
        """Returns a SuperDict of days and the opening hours"""
        ts_length = self._get_slot_length()
        if not round_ts:
            ts_length = 1

        return (
            self.data["weekly_schedule"].vapply(lambda v: (
                v.vapply(
                    lambda vv: (
                        int(vv[0][:2]),
                        ts_length * (int(vv[0][3:]) // ts_length),
                        int(vv[1][:2]),
                        ts_length * ceil(int(vv[1][3:]) / ts_length)
                    )
                ).vapply(self._round_up_tuple)
            ))
        )

    def _get_schedule_exceptions(self, round_ts=True):
        """Returns a SuperDict of days and the opening hours"""
        ts_length = self._get_slot_length()
        if not round_ts:
            ts_length = 1

        return (
            self.data["schedule_exceptions"].vapply(lambda v: (
                v.vapply(
                    lambda vv: (
                        int(vv[0][:2]),
                        ts_length * (int(vv[0][3:]) // ts_length),
                        int(vv[1][:2]),
                        ts_length * ceil(int(vv[1][3:]) / ts_length)
                    )
                ).vapply(self._round_up_tuple)
            ))
        )

    @staticmethod
    def _round_up_tuple(el):
        if el[3] == 60 and el[2] != 23:
            return el[0], el[1], el[2] + 1, 0
        elif el[3] == 60 and el[2] == 23:
            return el[0], el[1], 0, 0
        return el

    @staticmethod
    def _round_up_string(el):
        if el[3:] == "60" and el[:2] != "23":
            return f"{int(el[:2]) + 1}:00"
        elif el[3:] == "60" and el[:2] == "23":
            return "00:00"
        return el

    def _get_start_date(self) -> datetime:
        """Returns the datetime object of the starting date"""
        return get_date_from_string(self.data["parameters"]["starting_date"])

    def _get_end_date(self) -> datetime:
        """Returns the last date in the horizon"""
        return max(self.dates)

    def get_skills(self) -> TupList:
        """Returns a TupList containing the id of the skills"""
        return self.data["skills"].keys_tl()

    def get_employees_by_skill(self, id_skill) -> TupList:
        """Returns a TupList with the employees that have the given skill"""
        return self.data["skills_employees"][id_skill]

    def _get_min_resting_hours(self) -> int:
        """Returns the number of resting hours that the employees have to have between working days"""
        return self.data["parameters"]["min_resting_hours"]

    def _get_slot_length(self) -> float:
        """Returns the length of a time slot in minutes"""
        return self.data["parameters"]["slot_length"]

    def slot_to_hour(self, slots) -> int:
        """Converts from slots to hours"""
        return int(slots * self._get_slot_length() / 60)

    def _hour_to_slot(self, hours) -> int:
        """Converts from a hours to slots"""
        return int(hours * 60 / self._get_slot_length())

    def _minutes_to_slot(self, minutes) -> int:
        """Converts from a hours to slots"""
        return int(minutes / self._get_slot_length())

    def _get_employees_contracts(self) -> SuperDict[Tuple[int, int], int]:
        """
        Returns a SuperDict with the week and employee tuple as key
        and the contract id as value
        Contracts are supposed to start on Monday and end on Sunday
        For example: {(36, 1): 10, ...}
        """
        default_date = get_date_string_from_ts(self._get_end_date())

        contract_start = self._get_contracts("start_contract")
        contract_end = self._get_contracts("end_contract").vapply(
            lambda v: v or default_date
        )

        return SuperDict(
            {
                (self._get_week_from_date(week), e): c
                for week in self.weeks
                for c, e in self._get_contracts("id_employee").items()
                if contract_start[c]
                <= self.get_date_string_from_ts(week)
                <= contract_end[c]
            }
        )

    def _get_employees_normal_contract_hours(self) -> SuperDict[Tuple[int, int], int]:
        """
        Returns a SuperDict with the week and employee tuple as key
        and the weekly hours of the contract as the value
        Contracts are supposed to start on Monday and end on Sunday
        For example: {(36, 1): 40, ...}
        """
        contract_hours = self._get_contracts("weekly_hours")
        return self._get_employees_contracts().vapply(lambda c: contract_hours[c])

    def _get_employees_contract_hours(self) -> SuperDict[Tuple[int, int], int]:
        """
        Returns a SuperDict with the week and employee tuple as key
        and the weekly hours of the contract taking holidays into account
        Contracts are supposed to start on Monday and end on Sunday
        For example: {(36, 1): 40, ...}
        """
        contract_hours = self._get_employees_normal_contract_hours()
        employee_holiday_hours = self._get_employee_holiday_hours()
        downtime_hours = self._get_employee_downtime_hours()
        store_holiday_hours = self._get_store_holiday_hours()

        return SuperDict(
            {
                key: contract_hours[key]
                - employee_holiday_hours.get(key, 0)
                - store_holiday_hours.get(key, 0)
                - downtime_hours.get(key, 0)
                for key in contract_hours
            }
        )

    def _get_employees_normal_contract_days(self) -> SuperDict[Tuple[int, int], int]:
        """
        Returns a SuperDict with the week and employee tuple as key and
        the max days worked weekly of the contract as the value
        Contracts are supposed to start on Monday and end on Sunday
        For example: {(36, 1): 5, ...}
        """
        contract_days = self._get_contracts("days_worked")
        return self._get_employees_contracts().vapply(lambda c: contract_days[c])

    def _get_employees_contract_days(self) -> SuperDict[Tuple[int, int], int]:
        """
        Returns a SuperDict with the week and employee tuple as key and
        the max days worked weekly of the contract taking holidays into account
        For example: {(36, 1): 5, ...}
        """
        contract_days = self._get_employees_normal_contract_days()
        employee_holiday_days = self._get_employee_holiday_days()
        store_holiday_days = self._get_store_holiday_days()
        downtime_days = self._get_employee_downtime_days()

        return SuperDict(
            {
                key: contract_days[key]
                - employee_holiday_days.get(key, 0)
                - store_holiday_days.get(key, 0)
                - downtime_days.get(key, 0)
                for key in contract_days
            }
        )

    def _get_employees_contract_shift(self) -> SuperDict[Tuple[int, int], int]:
        """
        Returns a SuperDict with the week and employee tuple as key
        and the shift id as value
        Contracts are supposed to start on Monday and end on Sunday
        For example: {(36, 1): 1, ...}
        """
        contract_shift = self._get_contracts("id_shift")
        return self._get_employees_contracts().vapply(lambda c: contract_shift[c])

    def _get_employees_contract_starting_hour(self, round_ts=True) -> SuperDict:
        """
        Returns a SuperDict with the week and employee tuple as key
        and the shift starting hour
        Contracts are supposed to start on Monday and end on Sunday
        For example: {(36, 1): 7, ...}
        """
        start = self._get_shifts("start")

        ts_length = self._get_slot_length()
        if round_ts:
            start = start.vapply(lambda v: v[:3] + str(ts_length * (int(v[3:]) // ts_length)).zfill(2))

        return self._get_employees_contract_shift().vapply(lambda s: start[s])

    def _get_employees_contract_ending_hour(self, round_ts=True) -> SuperDict[Tuple[int, int], float]:
        """
        Returns a SuperDict with the week and employee tuple as key
        and the shift ending hour
        Contracts are supposed to start on Monday and end on Sunday
        For example: {(36, 1): 21, ...}
        """
        end = self._get_shifts("end")
        ts_length = self._get_slot_length()

        if round_ts:
            end = end.vapply(
                lambda v: self._round_up_string(
                    v[:3] + str(ts_length * ceil(int(v[3:]) / ts_length)).zfill(2)
                )
            )
        return self._get_employees_contract_shift().vapply(lambda s: end[s])

    def _get_employee_time_slots_week(self) -> TupList:
        """
        Returns a TupList with the combinations of employees, weeks, dates and time slots
        in which the employees can work.
        For example: [("2021-09-06T07:00", 36, "2021-09-06", 1),
            ("2021-09-06T08:00", 36, "2021-09-06", 1), ...]
        """
        start = (
            self._get_employees_contract_starting_hour()
            .vapply(lambda v: self._get_hour_from_hour_string(v))
        )
        end = (
            self._get_employees_contract_ending_hour()
            .vapply(lambda v: self._get_hour_from_hour_string(v))
        )

        return TupList(
            (self.get_time_slot_string(ts), w, self._get_date_string_from_ts(ts), e)
            for ts in self.time_slots
            for (w, e) in start
            if self._get_week_from_ts(ts) == w
            and start[w, e] <= self._get_hour_from_ts(ts) < end[w, e]
            and (e, self._get_date_string_from_ts(ts))
            not in self._get_employee_holidays()
            and (e, self._get_date_string_from_ts(ts))
            not in self._get_employee_downtime()
            if self._get_date_string_from_ts(ts) not in self._get_store_holidays()
        )

    def get_employees_time_slots_week(self) -> SuperDict:
        """
        Returns a SuperDict with the week and employee tuple as key
        and a list of time slots as value
        For example: {(36, 1): ["2021-09-06T07:00", "2021-09-06T08:00", ...], ...}
        """
        return self._get_employee_time_slots_week().take([0, 1, 3]).to_dict(0)

    def get_employees_time_slots_day(self) -> SuperDict:
        """
        Returns a SuperDict with the date and employee tuple as key
        and a list of time slots as value
        For example: {("2021-09-06", 1): ["2021-09-06T07:00", "2021-09-06T08:00", ...], ...}
        """
        return self._get_employee_time_slots_week().take([0, 2, 3]).to_dict(0)

    def get_consecutive_time_slots_employee(self) -> TupList:
        """
        Returns a TupList with a time slot, the nex time slot in the same day
        and an employee according to the employee availability
        For example: [("2021-09-06T07:00", "2021-09-06T08:00", 1), ...]
        """
        return TupList(
            [
                (ts, ts2, e)
                for (d, e), _time_slots in self.get_employees_time_slots_day().items()
                for ts, ts2 in zip(_time_slots, _time_slots[1:])
            ]
        )

    def get_opening_time_slots_set(self) -> set:
        """
        Returns a TupList with the time slots strings
        For example: ["2021-09-06T07:00", "2021-09-06T08:00", ...]
        """
        return self.time_slots.vapply(lambda v: self.get_time_slot_string(v)).to_set()

    def get_employees_ts_availability(self) -> TupList[Tuple[str, int]]:
        """
        Returns a TupList with the combinations of employees and time slots
        in which the employees can work.
        For example: [("2021-09-06T07:00", 1), ("2021-09-06T07:00", 2), ...]
        """
        return self._get_employee_time_slots_week().take([0, 3])

    def get_max_working_slots_week(self) -> SuperDict[Tuple[int, int], int]:
        """
        Returns a SuperDict with the week and employee tuple as key
        and the weekly hours of the contract as the value
        Contracts are supposed to start on Monday and end on Sunday
        For example: {(36, 1): 40, ...}
        """
        return self._get_employees_contract_hours().vapply(
            lambda v: self._hour_to_slot(v)
        )

    def get_max_working_slots_day(self) -> SuperDict[Tuple[str, int], float]:
        """
        Returns a SuperDict with the dates and employees tuple as a key
        and the maximum slots that can be worked on a day as value
        For example: {("2021-09-06", 1): 9, ("2021-09-06", 2): 9, ("2021-09-06", 3): 8, ...}
        """
        # TODO: set up a hard limit from the parameters of the instance, set up as optional,
        #  if there is value it should be that one, if not the current calculation

        return SuperDict(
            {
                (self._get_date_string_from_date(d), e): self._hour_to_slot(
                    hours / self._get_employees_contract_days()[w, e]
                )
                + 1
                for d in self.dates
                for (w, e), hours in self._get_employees_contract_hours().items()
                if self._get_week_from_date(d) == w
                if (e, self._get_date_string_from_date(d))
                not in self._get_employee_holidays()
                and (e, self._get_date_string_from_date(d))
                not in self._get_employee_downtime()
                if self._get_date_string_from_date(d) not in self._get_store_holidays()
            }
        )

    def get_min_working_slots_day(self) -> SuperDict[Tuple[str, int], int]:
        """
        Returns a SuperDict with the dates and employees tuple as a key and
        the minimum amount of slots that need to be worked each day
        For example: {("2021-09-06", 1): 4, ("2021-09-06", 2): 4, ("2021-09-06", 3): 4, ...}
        """
        return SuperDict(
            {
                (self._get_date_string_from_date(d), e): self._hour_to_slot(
                    self.data["parameters"]["min_working_hours"]
                )
                for d in self.dates
                for e in self._get_employees("id")
                if (e, self._get_date_string_from_date(d))
                not in self._get_employee_holidays()
                and (e, self._get_date_string_from_date(d))
                not in self._get_employee_downtime()
                if self._get_date_string_from_date(d) not in self._get_store_holidays()
            }
        )

    def get_first_time_slot_day_employee(self) -> SuperDict[Tuple[str, int], str]:
        """
        Returns a SuperDict with the date and employee tuple as a key
        and the first time slot that the employee can work in the day as the value
        For example: {("2021-09-06", 1): "2021-09-06T07:00", ("2021-09-06", 2): "2021-09-06T13:00", ...}
        """
        return (
            self._get_employee_time_slots_week()
            .take([0, 2, 3])
            .to_dict(0)
            .vapply(lambda v: min(v))
        )

    def get_max_working_days(self) -> SuperDict[Tuple[int, int], int]:
        """
        Returns a SuperDict with the week and employee tuple as key and
        the max days worked weekly of the contract as the value
        Contracts are supposed to start on Monday and end on Sunday
        For example: {(36, 1): 5, ...}
        """
        return self._get_employees_contract_days()

    def _get_incompatible_slots(self) -> TupList:
        """
        Returns a TupList with tuples that have time slots in consecutive days where
        if the employee works in one time slot it can not work
        in the other based on the minimum resting time
        For example: [("2021-09-06T20:00", "2021-09-07T07:00"),
            ("2021-09-06T21:00", "2021-09-07T07:00"), ...]
        """
        # First we calculate the upper limit slots given the resting hours
        upper_limit = int(self._hour_to_slot(self._get_min_resting_hours()))

        def check_same_day(ts, ts2):
            return ts.date() == ts2.date()

        def check_one_day_apart(ts, ts2):
            return (ts2 - ts).days <= 1

        ts_tuple = (
            TupList(
                [
                    (val, self.time_slots[pos + i])
                    for pos, val in enumerate(self.time_slots)
                    for i in range(1, upper_limit + 1)
                    if pos + i < self.time_slots.len()
                    # We only want the tuple if it's lower than the min time
                    and (self.time_slots[pos + i] - val).total_seconds() / 3600
                    < self._get_min_resting_hours() + self.slot_to_hour(1)
                ]
            )
            .vfilter(lambda v: not check_same_day(v[0], v[1]))
            .vfilter(lambda v: check_one_day_apart(v[0], v[1]))
            .vapply(
                lambda v: (
                    self.get_time_slot_string(v[0]),
                    self.get_time_slot_string(v[1]),
                )
            )
        )
        return ts_tuple

    def get_incompatible_slots_employee(self) -> TupList:
        """
        Returns a TupList with the incompatible time slots for each employee
        taking into account if the employee can work in both of them
        For example: [("2021-09-06T20:00", "2021-09-07T07:00", 1),
            ("2021-09-06T21:00", "2021-09-07T07:00", 1), ...]
        """
        availability = self.get_employees_ts_availability()
        ts_tuple = TupList(
            [
                (ts, ts2, e)
                for (ts, ts2) in self._get_incompatible_slots()
                for e in self._get_employees("name")
                if (ts, e) in availability and (ts2, e) in availability
            ]
        )
        return ts_tuple

    def get_employees_managers(self) -> TupList[int]:
        """Returns the list of employees ids that are managers"""
        return self._get_employees("manager").vfilter(lambda v: v).keys_tl()

    def _filter_demand(self, ts) -> float:
        """
        Given a time slot (date time) it returns the demand, if exists, zero otherwise
        """
        return self._get_property("demand", "demand").get(
            (self._get_date_string_from_ts(ts), self._get_hour_string_from_ts(ts)), 0
        )

    def get_demand(self) -> SuperDict:
        """
        Returns a SuperDict indexed by the time slot (string) and the demand as value
        For example: {"2021-09-06T07:00": 10, "2021-09-06T08:00": 15, ...}
        """
        return SuperDict(
            {
                self.get_time_slot_string(ts): self._filter_demand(ts)
                for ts in self.time_slots
            }
        )

    def filter_skills_demand(self, ts, id_skill) -> int:
        """
        Given a time slot (date time) and the id of a skill, returns the skill demand if it exists, zero otherwise
        """
        return self._get_property("skill_demand", "demand").get(
            (self._get_date_string_from_ts(ts), self._get_hour_string_from_ts(ts), id_skill), 0
        )

    def get_ts_demand_employees_skill(self, e_availability) -> TupList:
        """
        Returns a TupList with the combinations of:
         - Time slots
         - Skill
         - Demand for the given skill on this time slot
         - Employees that master the skill and are available on the timeslot
        For example: [("2021-09-06T07:00", 1, 1, [2, 3]), ("2021-09-06T08:00", 2, 1, [1, 2]), ...]
        """

        return SuperDict(
            {
                (
                    self.get_time_slot_string(ts),
                    id_skill,
                    self.filter_skills_demand(ts, id_skill),
                ): self.get_employees_by_skill(id_skill)
                for ts in self.time_slots
                for id_skill in self.get_skills()
            }
        ).kvapply(lambda k, v: [e for e in v if (k[0], e) in e_availability])

    def _get_employee_holidays(self) -> TupList:
        """
        Returns a TupList with the combinations of employees and holiday days.
        For example: [(1, "2021-09-06"),
            (2, "2021-09-07"), ...]
        """
        if self.get_requirement("rq10"):
            return TupList(self.data["employee_holidays"].keys_tl())
        else:
            return TupList([])

    def _get_employee_holiday_hours(self) -> SuperDict:
        """
        Returns a SuperDict with week and employee as key and weekly holiday hours as value.
        For example: {(36, 1): 8,
            (36, 2): 16, ...]
        """
        holiday_hours = TupList(
            (
                self._get_week_from_date(self.get_date_from_string(d)),
                e,
                ceil(
                    (
                        self._get_employees_normal_contract_hours()[
                            (self._get_week_from_date(self.get_date_from_string(d))), e
                        ]
                        / self._get_employees_normal_contract_days()[
                            (self._get_week_from_date(self.get_date_from_string(d))), e
                        ]
                    )
                ),
            )
            for (e, d) in self._get_employee_holidays()
        )
        holiday_hours_week = holiday_hours.take([0, 1, 2]).to_dict(2)
        return SuperDict({k: sum(v) for k, v in holiday_hours_week.items()})

    def _get_employee_holiday_days(self) -> SuperDict:
        """
        Returns a SuperDict with week and employee as key and weekly holiday days as value.
        For example: {(36, 1): 1,
            (36, 2): 2, ...]
        """
        holiday_days = TupList(
            (self._get_week_from_date(self.get_date_from_string(d)), e, 1)
            for (e, d) in self._get_employee_holidays().take([0, 1])
        )
        holiday_days_week = holiday_days.take([0, 1, 2]).to_dict(2)
        return SuperDict({k: sum(v) for k, v in holiday_days_week.items()})

    def _get_store_holidays(self) -> TupList:
        """
        Returns a TupList with the store holiday days.
        For example: [("2021-09-06"),
            ("2021-09-07"), ...]
        """
        if self.get_requirement("rq11"):
            return TupList(self.data["store_holidays"].keys_tl())
        else:
            return TupList([])

    def _get_store_holiday_hours(self) -> SuperDict:
        """
        Returns a SuperDict with week and employee as key and weekly store holiday hours as value.
        For example: {(36, 1): 8,
            (36, 2): 16, ...]
        """
        store_holiday_hours = TupList(
            (
                self._get_week_from_date(self.get_date_from_string(d)),
                e,
                ceil(
                    (
                        self._get_employees_normal_contract_hours()[
                            (self._get_week_from_date(self.get_date_from_string(d))), e
                        ]
                        / self._get_employees_normal_contract_days()[
                            (self._get_week_from_date(self.get_date_from_string(d))), e
                        ]
                    )
                ),
            )
            for d in self._get_store_holidays()
            for e in self._get_employees("id")
        )
        holiday_hours_week = store_holiday_hours.take([0, 1, 2]).to_dict(2)
        return SuperDict({k: sum(v) for k, v in holiday_hours_week.items()})

    def _get_store_holiday_days(self) -> SuperDict:
        """
        Returns a SuperDict with week and employee as key and weekly store holiday days as value.
        For example: {(36, 1): 1,
            (36, 2): 2, ...]
        """
        store_holiday_days = TupList(
            (self._get_week_from_date(self.get_date_from_string(d)), e, 1)
            for e in self._get_employees("id")
            for d in self._get_store_holidays()
        )
        holiday_days_week = store_holiday_days.take([0, 1, 2]).to_dict(2)
        return SuperDict({k: sum(v) for k, v in holiday_days_week.items()})

    def _get_employee_downtime(self) -> TupList:
        """
        Returns a TupList with the combinations of employees and downtime days.
        For example: [(1, "2021-09-06"),
            (2, "2021-09-07"), ...]
        """
        if self.get_requirement("rq12"):
            return TupList(self.data["employee_downtime"].keys_tl())
        else:
            return TupList([])

    def _get_employee_downtime_hours(self) -> SuperDict:
        """
        Returns a SuperDict with week and employee as key and weekly downtime hours as value.
        For example: {(36, 1): 8,
            (36, 2): 16, ...]
        """
        downtime_hours = TupList(
            (
                self._get_week_from_date(self.get_date_from_string(d)),
                e,
                ceil(
                    (
                        self._get_employees_normal_contract_hours()[
                            (self._get_week_from_date(self.get_date_from_string(d))), e
                        ]
                        / self._get_employees_normal_contract_days()[
                            (self._get_week_from_date(self.get_date_from_string(d))), e
                        ]
                    )
                ),
            )
            for (e, d) in self._get_employee_downtime()
        )
        downtime_hours_week = downtime_hours.take([0, 1, 2]).to_dict(2)
        return SuperDict({k: sum(v) for k, v in downtime_hours_week.items()})

    def _get_employee_downtime_days(self) -> SuperDict:
        """
        Returns a SuperDict with week and employee as key and weekly downtime days as value.
        For example: {(36, 1): 1,
            (36, 2): 2, ...]
        """
        downtime_days = TupList(
            (self._get_week_from_date(self.get_date_from_string(d)), e, 1)
            for (e, d) in self._get_employee_downtime()
        )
        downtime_days_week = downtime_days.take([0, 1, 2]).to_dict(2)
        return SuperDict({k: sum(v) for k, v in downtime_days_week.items()})

    def _get_employee_preferences(self, round_ts=True) -> TupList:
        """
        Returns a TupList with the employee preferences
        For example: [(1, "2021-09-09", 5, "15:00"),
        (1, "2021-09-09", 5, "15:00"), ...]
        """

        ts_length = self._get_slot_length()
        if not round_ts:
            ts_length = 1

        return (
            TupList(self.data["employee_preferences"].keys_tl())
            .vapply_col(
                3,
                lambda v: self._round_up_string(v[3][:3] + str(ts_length * (int(v[3][3:]) // ts_length)).zfill(2))
            )
        )

    def get_employee_time_slots_preferences(self) -> SuperDict:
        """
        Returns a SuperDict with the date and employee tuple as key
        and a list of time slots as value where the employee wants to work.
        For example: {("2021-09-06", 1): ["2021-09-06T07:00", "2021-09-06T08:00", ...], ...}
        """
        preferences = self._get_employee_preferences()
        availability = self.get_employees_ts_availability()

        ts_preferences = TupList(
            (self.get_time_slot_string(ts), self._get_date_string_from_ts(ts), e)
            for ts in self.time_slots
            for e in self._get_employees("id")
            if (e, self._get_date_string_from_ts(ts)) in preferences.take([0, 1])
            if (self.get_time_slot_string(ts), e) in availability
        )

        return ts_preferences.to_dict(0)

    def get_employee_preference_start_ts(self) -> SuperDict:
        """
        Returns a SuperDict with the date and employee tuple as key
        and a time slot in which the employee wants to start work.
        For example: {("2021-09-06", 1): ["2021-09-06T07:00"], ...}
        """

        preferences = self._get_employee_preferences()
        availability = self.get_employees_ts_availability()

        starts_ts = TupList(
            (self.get_time_slot_string(ts), self._get_date_string_from_ts(ts), e)
            for ts in self.time_slots
            for e in self._get_employees("id")
            if (e, self._get_date_string_from_ts(ts), self._get_hour_string_from_ts(ts))
            in preferences.take([0, 1, 3])
            if (self.get_time_slot_string(ts), e) in availability
        )

        return starts_ts.to_dict(0)

    def get_employee_preference_hours(self) -> SuperDict:
        """
        Returns a SuperDict with the date and employee tuple as key
        and the max hours the employee wants to work for a specific day.
        For example: {("2021-09-06", 1): 6, ("2021-09-08", 2): 7...}
        """

        return self._get_employee_preferences().to_dict(
            2, indices=[1, 0], is_list=False
        )

    def get_requirement(self, rq):
        """
        Returns the activation value of a given requirement
        """
        return self.data["requirements"].get(rq, True)
