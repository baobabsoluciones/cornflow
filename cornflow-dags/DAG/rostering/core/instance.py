"""

"""
# Imports from libraries
from datetime import datetime
import os
import pickle
from pytups import SuperDict, TupList
from typing import Dict, Tuple

# Imports from cornflow libraries
from cornflow_client import InstanceCore
from cornflow_client.core.tools import load_json
from .const import INSTANCE_KEYS_RELATION

# Imports from internal modules
from .tools import (
    get_date_from_string,
    get_date_string_from_ts,
    get_hour_from_date_time,
    get_one_date,
    get_one_date_time,
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

        data_p["parameters"] = pickle.loads(pickle.dumps(data["parameters"], -1))

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
                (el["id_employee"], el["day"]): el
                for el in data["employee_holidays"]
            }
        else:
            data_p["employee_holidays"] = SuperDict({})

        if data.get("store_holidays"):
            data_p["store_holidays"] = {
                (el["day"]): el
                for el in data["store_holidays"]
            }
        else:
            data_p["store_holidays"] = SuperDict({})

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
            "store_holidays"
        ]

        data_p = {el: self.data[el].values_l() for el in tables}

        data_p["parameters"] = self.data["parameters"]
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
            dict(day=day)
            for (day) in self.data["store_holidays"]
        ]
        return pickle.loads(pickle.dumps(data_p, -1))

    def cache_properties(self):
        """Caches the list of weeks, dates and time slots and its associated properties"""
        self.weeks = self._get_weeks()
        self.dates = self._get_dates()
        self.dates_properties = self._get_dates_properties()
        self.time_slots = self._get_time_slots()
        self.time_slots_properties = self._get_time_slots_properties()

    def check(self) -> dict:
        return dict(incoherent_foreign_keys=self.check_indexes_coherence())

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

    def _get_dates(self) -> TupList:
        """
        Returns a TupList with the dates of the whole horizon in datetime format
        For example: [datetime(2021, 9, 6, 0, 0, 0), datetime(2021, 9, 7, 0, 0, 0), ...]
        """
        return TupList(
            [
                get_one_date(self._get_start_date(), pos, d)
                for d in range(0, self._get_opening_days())
                for pos, value in enumerate(self.weeks)
            ]
        ).sorted()

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
        nb_hours = self._get_ending_hour() - self._get_starting_hour()
        nb_slots = int(self._hour_to_slot(nb_hours))

        def date_hour_ts(d, s):
            return get_one_date_time(d, self._get_minutes(s))

        return TupList(
            [date_hour_ts(date, s) for date in self.dates for s in range(nb_slots)]
        ).sorted()

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
                }
                for ts in self.time_slots
            }
        )

    def _get_time_slot_string(self, ts):
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

    def _get_property(self, key, prop) -> SuperDict:
        """Returns a SuperDict with the key of a given 'table' and the prop as value"""
        return self.data[key].get_property(prop)

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

    def _get_start_date(self) -> datetime:
        """Returns the datetime object of the starting date"""
        return get_date_from_string(self.data["parameters"]["starting_date"])

    def _get_end_date(self) -> datetime:
        """
        Returns the last working day based on the starting day, the horizon in weeks
        and the number of days worked
        It assumes that the working days start at the end of the week.
        For example: 5 opening days, 2 week horizon and starting date of 2021-09-06
        would result in 2021-09-17 being the end date.
        """
        days = -(7 - self._get_opening_days()) - 1
        return get_one_date(
            self._get_start_date(), weeks=self._get_horizon(), days=days
        )

    def _get_skills(self) -> TupList:
        """Returns a TupList containing the id of the skills"""
        return self.data["skills"].keys_tl()

    def get_employees_by_skill(self, id_skill) -> TupList:
        """Returns a TupList with the employees that have the given skill"""
        return self.data["skills_employees"][id_skill]

    def _get_opening_days(self) -> int:
        """Returns the number of days that have to be worked each week"""
        return self.data["parameters"]["opening_days"]

    def _get_starting_hour(self) -> float:
        """Returns the first hour of the day that has to be worked."""
        return self.data["parameters"]["starting_hour"]

    def _get_ending_hour(self) -> float:
        """Returns the last hour of the day that has to be worked."""
        return self.data["parameters"]["ending_hour"]

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

    def _get_minutes(self, s) -> float:
        """Method to get the number of minutes from the start of the day given a slot"""
        return self._get_starting_hour() * 60 + s * self._get_slot_length()

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
                <= self._get_date_string_from_date(week)
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
        return self._get_employees_contracts().vapply(
            lambda c: self._hour_to_slot(contract_hours[c])
        )

    def _get_employees_contract_hours(self) -> SuperDict[Tuple[int, int], int]:
        """
        Returns a SuperDict with the week and employee tuple as key
        and the weekly hours of the contract taking holidays into acount
        Contracts are supposed to start on Monday and end on Sunday
        For example: {(36, 1): 40, ...}
        """
        contract_hours = self._get_employees_normal_contract_hours()
        employee_holiday_hours = self._get_employee_holiday_hours()
        store_holiday_hours = self._get_store_holiday_hours()

        return SuperDict({key: contract_hours[key] - employee_holiday_hours.get(key, 0)
                               - store_holiday_hours.get(key,0) for key in contract_hours})

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
        the max days worked weekly of the contract taking holidays into acount
        For example: {(36, 1): 5, ...}
        """
        contract_days = self._get_employees_normal_contract_days()
        employee_holiday_days = self._get_employee_holiday_days()
        store_holiday_days = self._get_store_holiday_days()
        return SuperDict({key: contract_days[key] - employee_holiday_days.get(key, 0) -
                               store_holiday_days.get(key, 0) for key in contract_days})

    def _get_employees_contract_shift(self) -> SuperDict[Tuple[int, int], int]:
        """
        Returns a SuperDict with the week and employee tuple as key
        and the shift id as value
        Contracts are supposed to start on Monday and end on Sunday
        For example: {(36, 1): 1, ...}
        """
        contract_shift = self._get_contracts("id_shift")
        return self._get_employees_contracts().vapply(lambda c: contract_shift[c])

    def _get_employees_contract_starting_hour(self) -> SuperDict:
        """
        Returns a SuperDict with the week and employee tuple as key
        and the shift starting hour
        Contracts are supposed to start on Monday and end on Sunday
        For example: {(36, 1): 7, ...}
        """
        start = self._get_shifts("start")
        return self._get_employees_contract_shift().vapply(lambda s: start[s])

    def _get_employees_contract_ending_hour(self) -> SuperDict[Tuple[int, int], float]:
        """
        Returns a SuperDict with the week and employee tuple as key
        and the shift ending hour
        Contracts are supposed to start on Monday and end on Sunday
        For example: {(36, 1): 21, ...}
        """
        end = self._get_shifts("end")
        return self._get_employees_contract_shift().vapply(lambda s: end[s])

    def _get_employee_time_slots_week(self) -> TupList:
        """
        Returns a TupList with the combinations of employees, weeks, dates and time slots
        in which the employees can work.
        For example: [("2021-09-06T07:00", 36, "2021-09-06", 1),
            ("2021-09-06T08:00", 36, "2021-09-06", 1), ...]
        """
        start = self._get_employees_contract_starting_hour()
        end = self._get_employees_contract_ending_hour()

        return TupList(
            (self._get_time_slot_string(ts), w, self._get_date_string_from_ts(ts), e)
            for ts in self.time_slots
            for (w, e) in start
            if self._get_week_from_ts(ts) == w
            and start[w, e] <= self._get_hour_from_ts(ts) < end[w, e]
            and (e, self._get_date_string_from_ts(ts)) not in self._get_employee_holidays().take([0, 1])
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
        return self.time_slots.vapply(lambda v: self._get_time_slot_string(v)).to_set()

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
        return self._get_employees_contract_hours()

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
                (self._get_date_string_from_date(d), e): hours
                / self._get_employees_contract_days()[w, e]
                + 1
                for d in self.dates
                for (w, e), hours in self._get_employees_contract_hours().items()
                if self._get_week_from_date(d) == w
                if (e, self._get_date_string_from_date(d)) not in self._get_employee_holidays().take([0, 1])
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
                if (e, self._get_date_string_from_date(d)) not in self._get_employee_holidays().take([0, 1])
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
        if (
            24 - (self._get_ending_hour() - self._get_starting_hour())
            >= self._get_min_resting_hours()
        ):
            return TupList()

        nb_incompatible = self._hour_to_slot(
            int(
                self._get_min_resting_hours()
                - (24 - (self._get_ending_hour() - self._get_starting_hour()))
            )
        )

        time_slots_wo_last_day = self.time_slots.vfilter(
            lambda v: self._get_date_string_from_ts(v)
            != get_date_string_from_ts(self._get_end_date())
        )

        def check_same_day(ts, ts2):
            return ts.date() == ts2.date()

        def check_one_day_apart(ts, ts2):
            return (ts2 - ts).days <= 1

        return (
            TupList(
                [
                    (val, self.time_slots[pos + i])
                    for pos, val in enumerate(time_slots_wo_last_day)
                    for i in range(1, nb_incompatible + 1)
                ]
            )
            .vfilter(lambda v: not check_same_day(v[0], v[1]))
            .vfilter(lambda v: check_one_day_apart(v[0], v[1]))
            .vapply(
                lambda v: (
                    self._get_time_slot_string(v[0]),
                    self._get_time_slot_string(v[1]),
                )
            )
        )

    def get_incompatible_slots_employee(self) -> TupList:
        """
        Returns a TupList with the incompatible time slots for each employee
        taking into account if the employee can work in both of them
        For example: [("2021-09-06T20:00", "2021-09-07T07:00", 1),
            ("2021-09-06T21:00", "2021-09-07T07:00", 1), ...]
        """
        availability = self.get_employees_ts_availability()
        return TupList(
            [
                (ts, ts2, e)
                for (ts, ts2) in self._get_incompatible_slots()
                for e in self._get_employees("name")
                if (ts, e) in availability and (ts2, e) in availability
            ]
        )

    def get_employees_managers(self) -> TupList[int]:
        """Returns the list of employees ids that are managers"""
        return self._get_employees("manager").vfilter(lambda v: v).keys_tl()

    def _filter_demand(self, ts) -> float:
        """
        Given a time slot (date time) it returns the demand, if exists, zero otherwise
        """
        return self._get_property("demand", "demand").get(
            (self._get_date_string_from_ts(ts), self._get_hour_from_ts(ts)), 0
        )

    def get_demand(self) -> SuperDict:
        """
        Returns a SuperDict indexed by the time slot (string) and the demand as value
        For example: {"2021-09-06T07:00": 10, "2021-09-06T08:00": 15, ...}
        """
        return SuperDict(
            {
                self._get_time_slot_string(ts): self._filter_demand(ts)
                for ts in self.time_slots
            }
        )

    def _filter_skills_demand(self, ts, id_skill) -> int:
        """
        Given a time slot (date time) and the id of a skill, returns the skill demand if it exists, zero otherwise
        """
        return self._get_property("skill_demand", "demand").get(
            (self._get_date_string_from_ts(ts), self._get_hour_from_ts(ts), id_skill), 0
        )

    def _employee_available(self, ts, id_employee) -> bool:
        """
        Returns a boolean indicating if the employee is available on the time slot or not
        """
        return (
            self._get_time_slot_string(ts),
            id_employee,
        ) in self.get_employees_ts_availability()

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
                    self._get_time_slot_string(ts),
                    id_skill,
                    self._filter_skills_demand(ts, id_skill),
                ): self.get_employees_by_skill(id_skill)
                for ts in self.time_slots
                for id_skill in self._get_skills()
            }
        ).kvapply(lambda k, v: [e for e in v if (k[0], e) in e_availability])

    def _get_employee_holidays(self) -> TupList:
        """
        Returns a TupList with the combinations of employees and holiday days.
        For example: [(1, "2021-09-06"),
            (2, "2021-09-07"), ...]
        """
        return TupList(
            (self.data["employee_holidays"].keys_tl())
        )

    def _get_employee_holiday_hours(self) -> SuperDict:
        """
        Returns a SuperDict with week and employee as key and weekly holiday hours as value.
        For example: {(36, 1): 8,
            (36, 2): 16, ...]
        """
        holiday_hours = TupList(
            (self._get_week_from_date(self.get_date_from_string(d)), e,
             round((self._get_employees_normal_contract_hours()[(self._get_week_from_date(self.get_date_from_string(d))), e] /
              self._get_employees_normal_contract_days()[(self._get_week_from_date(self.get_date_from_string(d))), e])))
                                     for (e, d) in self._get_employee_holidays())
        holiday_hours_week = holiday_hours.take([0, 1, 2]).to_dict(2)
        return SuperDict({k: sum(v) for k, v in holiday_hours_week.items()})

    def _get_employee_holiday_days(self) -> SuperDict:
        """
        Returns a SuperDict with week and employee as key and weekly holiday days as value.
        For example: {(36, 1): 1,
            (36, 2): 2, ...]
        """
        holiday_days = TupList((self._get_week_from_date(self.get_date_from_string(d)), e, 1)
                                     for (e, d) in self._get_employee_holidays().take([0,1]))
        holiday_days_week = holiday_days.take([0, 1, 2]).to_dict(2)
        return SuperDict({k: sum(v) for k, v in holiday_days_week.items()})


    def _get_store_holidays(self) -> TupList:
        """
        Returns a TupList with the store holiday days.
        For example: [("2021-09-06"),
            ("2021-09-07"), ...]
        """
        return TupList(
            (self.data["store_holidays"].keys_tl())
        )

    def _get_store_holiday_hours(self) -> SuperDict:
        """
        Returns a SuperDict with week and employee as key and weekly store holiday hours as value.
        For example: {(36, 1): 8,
            (36, 2): 16, ...]
        """
        store_holiday_hours = TupList(
            (self._get_week_from_date(self.get_date_from_string(d)), e,
             round((self._get_employees_normal_contract_hours()[(self._get_week_from_date(self.get_date_from_string(d))), e] /
              self._get_employees_normal_contract_days()[(self._get_week_from_date(self.get_date_from_string(d))), e])))
                                     for d in self._get_store_holidays() for e in self._get_employees("id"))
        holiday_hours_week = store_holiday_hours.take([0, 1, 2]).to_dict(2)
        return SuperDict({k: sum(v) for k, v in holiday_hours_week.items()})

    def _get_store_holiday_days(self) -> SuperDict:
        """
        Returns a SuperDict with week and employee as key and weekly store holiday days as value.
        For example: {(36, 1): 1,
            (36, 2): 2, ...]
        """
        store_holiday_days = TupList((self._get_week_from_date(self.get_date_from_string(d)), e, 1)
                                     for e in self._get_employees("id") for d in self._get_store_holidays())
        holiday_days_week = store_holiday_days.take([0, 1, 2]).to_dict(2)
        return SuperDict({k: sum(v) for k, v in holiday_days_week.items()})
