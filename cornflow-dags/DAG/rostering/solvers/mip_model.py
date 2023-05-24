"""

"""
# Imports from external libraries
import pulp as pl
from pytups import SuperDict, TupList

# Imports from cornflow libraries
from cornflow_client.constants import (
    SOLUTION_STATUS_FEASIBLE,
    SOLUTION_STATUS_INFEASIBLE,
)

# Imports from internal modules
from ..core import Experiment, Solution


class MipModel(Experiment):
    def __init__(self, instance, solution=None):
        super().__init__(instance, solution)

        # Sets and parameters
        self.employee_ts_availability = TupList()
        self.ts_employees = SuperDict()
        self.ts_managers = SuperDict()
        self.ts_open = TupList()
        self.max_working_ts_week = SuperDict()
        self.workable_ts_week = SuperDict()
        self.max_working_ts_day = SuperDict()
        self.min_working_ts_day = SuperDict()
        self.workable_ts_day = SuperDict()
        self.ts_ts_employee = SuperDict()
        self.max_working_days = SuperDict()
        self.managers = TupList()
        self.incompatible_ts_employee = TupList()
        self.first_ts_day_employee = SuperDict()
        self.demand = SuperDict()
        self.ts_demand_employee_skill = SuperDict()
        self.ts_employees_holidays = TupList()
        self.ts_employees_rest_days = TupList()
        self.ts_skill_demand = TupList()
        self.preference_starts_ts = SuperDict()
        self.preference_hours_employee = SuperDict()
        self.preference_slots = SuperDict()
        self.employees_rest_days = TupList()

        # Variables
        self.works = SuperDict()
        self.starts = SuperDict()
        self.unmet_skill_demand = SuperDict()
        self.unmet_preference_start = SuperDict()
        self.unmet_preference_hours = SuperDict()
        self.unmet_manager_constraint = SuperDict()
        self.unmet_rest_hours_constraint = SuperDict()
        self.unmet_employee_holidays_constraint = SuperDict()
        self.unmet_min_daily_hours_constraint = SuperDict()
        self.unmet_max_weekly_work_days_constraint = SuperDict()
        self.unmet_max_daily_hours_constraint = SuperDict()
        self.unmet_weekly_hours_constraint = SuperDict()
        self.unmet_employee_schedule = SuperDict()

        self.initialize()

    def solve(self, options: dict) -> dict:

        model = pl.LpProblem("rostering", pl.LpMaximize)
        # Variables:
        self.create_variables()
        # Constraints:
        model = self.create_constraints(model)

        solver_name = options.pop("solver")
        if "." in solver_name:
            prefix, solver_name = solver_name.split(".")
        else:
            prefix = "mip"
            solver_name = "PULP_CBC_CMD"

        options["solver"] = f"{prefix}.{solver_name}"
        solver = pl.getSolver(solver_name, **self.get_solver_config(options, lib="pulp"))

        # Solver and solve
        status = model.solve(solver)

        # Check status
        if model.sol_status not in [pl.LpSolutionIntegerFeasible, pl.LpSolutionOptimal]:
            return dict(status=status, status_sol=SOLUTION_STATUS_INFEASIBLE)

        work_assignments = (
            self.works.vfilter(lambda v: pl.value(v))
            .keys_tl()
            .vapply(lambda v: dict(id_employee=v[1], time_slot=v[0]))
        )

        self.solution = Solution.from_dict(SuperDict(works=work_assignments))
        self.solution.data["indicators"] = self.get_indicators()

        return dict(status=status, status_sol=SOLUTION_STATUS_FEASIBLE)

    def initialize(self):
        self.managers = self.instance.get_employees_managers()
        self.employee_ts_availability = self.instance.get_employees_ts_availability()
        self.ts_employees = self.employee_ts_availability.to_dict(1)
        self.ts_managers = self.ts_employees.vapply(
            lambda v: [e for e in v if e in self.managers]
        )

        self.ts_open = self.ts_employees.keys_tl()

        self.max_working_ts_week = self.instance.get_max_working_slots_week()
        self.workable_ts_week = self.instance.get_employees_time_slots_week()
        self.max_working_ts_day = self.instance.get_max_working_slots_day()
        self.min_working_ts_day = self.instance.get_min_working_slots_day()
        self.workable_ts_day = self.instance.get_employees_time_slots_day()
        self.ts_ts_employee = self.instance.get_consecutive_time_slots_employee()
        self.incompatible_ts_employee = self.instance.get_incompatible_slots_employee()
        self.first_ts_day_employee = self.instance.get_first_time_slot_day_employee()
        self.max_working_days = self.instance.get_max_working_days()

        self.demand = self.instance.get_demand()
        self.ts_demand_employee_skill = self.instance.get_ts_demand_employees_skill(
            self.employee_ts_availability
        )
        self.ts_skill_demand = self.instance.get_ts_skill_demand(self.ts_demand_employee_skill.keys_tl())
        self.ts_employees_holidays = self.instance.get_employee_time_slots_holidays()
        self.preference_starts_ts = self.instance.get_employee_preference_start_ts()
        self.preference_hours_employee = self.instance.get_employee_preference_hours()
        self.preference_slots = self.instance.get_employee_time_slots_preferences()
        self.ts_employees_rest_days = self.instance.get_employee_time_slots_rest_days()
        self.employees_rest_days = self.instance.get_employees_rest_days(self.ts_employees_rest_days)

    def create_variables(self):

        self.works = pl.LpVariable.dicts(
            "works",
            self.employee_ts_availability,
            lowBound=0,
            upBound=1,
            cat=pl.LpBinary,
        )

        self.works = SuperDict(self.works)

        self.starts = pl.LpVariable.dicts(
            "starts",
            self.employee_ts_availability,
            lowBound=0,
            upBound=1,
            cat=pl.LpBinary,
        )

        self.starts = SuperDict(self.starts)

        # RQ02
        self.unmet_weekly_hours_constraint = pl.LpVariable.dicts(
            "unmet_weekly_hours_constraint",
            self.max_working_ts_week.keys_l(),
            lowBound=0,
            cat=pl.LpContinuous
        )
        self.unmet_weekly_hours_constraint = SuperDict(self.unmet_weekly_hours_constraint)

        # RQ03
        self.unmet_max_daily_hours_constraint = pl.LpVariable.dicts(
            "unmet_max_daily_hours_constraint",
            self.workable_ts_day.keys_l(),
            lowBound=0,
            cat=pl.LpContinuous
        )
        self.unmet_max_daily_hours_constraint = SuperDict(self.unmet_max_daily_hours_constraint)

        # RQ05
        self.unmet_max_weekly_work_days_constraint = pl.LpVariable.dicts(
            "unmet_max_weekly_work_days_constraint",
            self.workable_ts_week.keys_l(),
            lowBound=0,
            cat=pl.LpContinuous
        )
        self.unmet_max_weekly_work_days_constraint = SuperDict(self.unmet_max_weekly_work_days_constraint)

        # RQ06
        self.unmet_min_daily_hours_constraint = pl.LpVariable.dicts(
            "unmet_min_daily_hour_constraint",
            self.workable_ts_day.keys_l(),
            lowBound=0,
            cat=pl.LpContinuous
        )
        self.unmet_min_daily_hours_constraint = SuperDict(self.unmet_min_daily_hours_constraint)

        # RQ07
        self.unmet_rest_hours_constraint = pl.LpVariable.dicts(
            "unmet_rest_hours_constraint",
            self.incompatible_ts_employee,
            lowBound=0,
            upBound=1,
            cat=pl.LpContinuous
        )
        self.unmet_rest_hours_constraint = SuperDict(self.unmet_rest_hours_constraint)

        # RQ08
        self.unmet_manager_constraint = pl.LpVariable.dicts(
            "unmet_manager_constraints",
            self.ts_managers.keys_l(),
            lowBound=0,
            upBound=1,
            cat=pl.LpContinuous
        )
        self.unmet_manager_constraint = SuperDict(self.unmet_manager_constraint)

        # RQ09
        self.unmet_skill_demand = pl.LpVariable.dicts(
            "unmet_skill_demand",
            self.ts_skill_demand,
            lowBound=0,
            cat=pl.LpContinuous
        )
        self.unmet_skill_demand = SuperDict(self.unmet_skill_demand)

        # RQ10
        self.unmet_employee_holidays_constraint = pl.LpVariable.dicts(
            "unmet_employees_holidays_constraint",
            self.ts_employees_holidays,
            lowBound=0,
            upBound=1,
            cat=pl.LpContinuous
        )
        self.unmet_employee_holidays_constraint = SuperDict(self.unmet_employee_holidays_constraint)

        # RQ13
        self.unmet_preference_start = pl.LpVariable.dicts(
            "unmet_preference_start",
            self.preference_starts_ts.keys_l(),
            lowBound=0,
            upBound=1,
            cat=pl.LpContinuous
        )
        self.unmet_preference_start = SuperDict(self.unmet_preference_start)

        # RQ14
        self.unmet_preference_hours = pl.LpVariable.dicts(
            "unmet_preference_hours",
            self.preference_slots.keys_l(),
            lowBound=0,
            cat=pl.LpContinuous
        )
        self.unmet_preference_hours = SuperDict(self.unmet_preference_hours)

        # RQ15
        self.unmet_employee_schedule = pl.LpVariable.dicts(
            "unmet_employee_schedule",
            self.employees_rest_days,
            lowBound=0,
            upBound=1,
            cat=pl.LpContinuous
        )
        self.unmet_employee_schedule = SuperDict(self.unmet_employee_schedule)

    def create_constraints(self, model):
        # RQ00: objective function - minimize working hours
        big_m = sum(len(self.ts_employees) * max(self.demand.values()) for _ in self.ts_open) / 100
        model += pl.lpSum(
            pl.lpSum(self.works[ts, e] for e in self.ts_employees[ts]) * self.demand[ts]
            for ts in self.ts_open
        ) - big_m * (
            (self.instance.get_requirement("rq02") == "soft")
                * self.instance.get_penalty("rq02")
                * pl.lpSum(self.unmet_weekly_hours_constraint.values())
            + (self.instance.get_requirement("rq03") == "soft")
                * self.instance.get_penalty("rq03")
                * pl.lpSum(self.unmet_max_daily_hours_constraint.values())
            + (self.instance.get_requirement("rq05") == "soft")
                * self.instance.get_penalty("rq05")
                * pl.lpSum(self.unmet_max_weekly_work_days_constraint.values())
            + (self.instance.get_requirement("rq06") == "soft")
                * self.instance.get_penalty("rq06")
                * pl.lpSum(self.unmet_min_daily_hours_constraint.values())
            + (self.instance.get_requirement("rq07") == "soft")
                * self.instance.get_penalty("rq07")
                * pl.lpSum(self.unmet_rest_hours_constraint.values())
            + (self.instance.get_requirement("rq08") == "soft")
                * self.instance.get_penalty("rq08")
                * pl.lpSum(self.unmet_manager_constraint.values())
            + (self.instance.get_requirement("rq09") == "soft")
                * self.instance.get_penalty("rq09")
                * pl.lpSum(self.unmet_skill_demand.values())
            + (self.instance.get_requirement("rq10") == "soft")
                * self.instance.get_penalty("rq10")
                * pl.lpSum(self.unmet_employee_holidays_constraint.values())
            + (self.instance.get_requirement("rq13") == "soft")
                * self.instance.get_penalty("rq13")
                * pl.lpSum(self.unmet_preference_start.values())
            + (self.instance.get_requirement("rq14") == "soft")
                * self.instance.get_penalty("rq14")
                * pl.lpSum(self.unmet_preference_hours.values())
            + (self.instance.get_requirement("rq15") == "soft")
                * self.instance.get_penalty("rq15")
                * pl.lpSum(self.unmet_employee_schedule.values())
        )

        # RQ01: at least one employee at all times
        for ts, _employees in self.ts_employees.items():
            model += pl.lpSum(self.works[ts, e] for e in _employees) >= 1

        # RQ02: employees work their weekly hours
        if self.instance.get_requirement("rq02") != "deactivated":
            for (w, e), max_slots in self.max_working_ts_week.items():
                model += (
                    pl.lpSum(self.works[ts, e] for ts in self.workable_ts_week[w, e])
                    - (self.instance.get_requirement("rq02") == "soft")
                    * self.unmet_weekly_hours_constraint[w, e]
                    == max_slots
                )

        # RQ03: employees can not exceed their daily hours
        if self.instance.get_requirement("rq03") != "deactivated":
            for (d, e), slots in self.workable_ts_day.items():
                if self.instance.get_requirement("rq03") == "soft":
                    model += (
                        pl.lpSum(self.works[ts, e] for ts in slots)
                        - self.unmet_max_daily_hours_constraint[d, e]
                        <= self.max_working_ts_day[d, e]
                    )
                else:
                    model += (
                        pl.lpSum(self.works[ts, e] for ts in slots)
                        <= self.max_working_ts_day[d, e]
                    )

        # RQ04A: starts if does not work in one ts but in the next it does
        for (ts, ts2, e) in self.ts_ts_employee:
            model += self.works[ts, e] >= self.works[ts2, e] - self.starts[ts2, e]

        # RQ04B: starts on first time slot
        for (d, e), ts in self.first_ts_day_employee.items():
            model += self.works[ts, e] == self.starts[ts, e]

        # RQ04C: only one start per day
        for (d, e), slots in self.workable_ts_day.items():
            model += pl.lpSum(self.starts[ts, e] for ts in slots) <= 1

        # RQ05: max days worked per week
        if self.instance.get_requirement("rq06") != "deactivated":
            for (w, e), slots in self.workable_ts_week.items():
                if self.instance.get_requirement("rq05") == "soft":
                    model += (
                        pl.lpSum(self.starts[ts, e] for ts in slots)
                        - self.unmet_max_weekly_work_days_constraint[w, e]
                        <= self.max_working_days[w, e]
                    )
                else:
                    model += (
                        pl.lpSum(self.starts[ts, e] for ts in slots)
                        <= self.max_working_days[w, e]
                    )

        # RQ06: employees at least work the minimum hours
        if self.instance.get_requirement("rq06") != "deactivated":
            for (d, e), slots in self.workable_ts_day.items():
                if self.instance.get_requirement("rq06") == "soft":
                    model += (pl.lpSum(
                        self.works[ts, e] for ts in slots
                    ) + self.unmet_min_daily_hours_constraint[d, e]
                        >= self.min_working_ts_day[d, e] * pl.lpSum(
                        self.starts[ts, e] for ts in slots
                    ))
                else:
                    model += pl.lpSum(
                        self.works[ts, e] for ts in slots
                    ) >= self.min_working_ts_day[d, e] * pl.lpSum(
                        self.starts[ts, e] for ts in slots
                    )

        # RQ07: employees at least have to rest an amount of hours between working days.
        if self.instance.get_requirement("rq07") != "deactivated":
            for (ts, ts2, e) in self.incompatible_ts_employee:
                if self.instance.get_requirement("rq07") == "soft":
                    model += (
                        self.works[ts, e]
                        + self.works[ts2, e]
                        - self.unmet_rest_hours_constraint[ts, ts2, e] <= 1
                    )
                else:
                    model += self.works[ts, e] + self.works[ts2, e] <= 1

        # RQ08: a manager has to be working at all times
        if self.instance.get_requirement("rq08") != "deactivated":
            for ts, _employees in self.ts_managers.items():
                if self.instance.get_requirement("rq08") == "soft":
                    model += (
                        pl.lpSum(self.works[ts, e] for e in _employees)
                        + self.unmet_manager_constraint[ts] >= 1
                    )
                else:
                    model += pl.lpSum(self.works[ts, e] for e in _employees) >= 1

        # RQ09: The demand for each skill is covered
        if self.instance.get_requirement("rq09") != "deactivated":
            for (
                ts,
                id_skill,
                skill_demand,
            ), employees in self.ts_demand_employee_skill.items():
                if self.instance.get_requirement("rq09") == "soft":
                    model += (
                        pl.lpSum(self.works[ts, e] for e in employees)
                        + self.unmet_skill_demand[ts, id_skill]
                        >= skill_demand
                    )
                else:
                    model += pl.lpSum(self.works[ts, e] for e in employees) >= skill_demand

        # RQ10: Employee holidays
        if self.instance.get_requirement("rq10") == "soft":
            for (ts, e) in self.ts_employees_holidays:
                model += self.works[ts, e] <= self.unmet_employee_holidays_constraint[ts, e]

        # RQ13: Starting hour preference
        if self.instance.get_requirement("rq13") != "deactivated":
            for (d, e), slots in self.preference_starts_ts.items():
                if self.instance.get_requirement("rq13") == "soft":
                    model += pl.lpSum(self.starts[ts, e] for ts in slots) + self.unmet_preference_start[d, e] == 1
                else:
                    model += pl.lpSum(self.starts[ts, e] for ts in slots) == 1

        # RQ14: max preference hours
        if self.instance.get_requirement("rq14") != "deactivated":
            for (d, e), slots in self.preference_slots.items():
                if self.instance.get_requirement("rq14") == "soft":
                    model += (
                        pl.lpSum(self.works[ts, e] for ts in slots)
                        - self.unmet_preference_hours[d, e]
                        <= self.preference_hours_employee[d, e]
                    )
                else:
                    model += (
                        pl.lpSum(self.works[ts, e] for ts in slots)
                        <= self.preference_hours_employee[d, e]
                    )

        # RQ15: Employee schedule
        if self.instance.get_requirement("rq15") == "soft":
            for (ts, d, e) in self.ts_employees_rest_days:
                model += self.works[ts, e] <= self.unmet_employee_schedule[d, e]

        return model
