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
        self.preference_starts_ts = SuperDict()
        self.preference_hours_employee = SuperDict()
        self.preference_slots = SuperDict()
        self.employee_holiday = TupList()

        # Variables
        self.works = SuperDict()
        self.starts = SuperDict()

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

        solver = pl.getSolver(solver_name, **options)
        options["solver"] = f"{prefix}.{solver_name}"

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
        self.ts_demand_employee_skill = \
            self.instance.get_ts_demand_employees_skill(self.employee_ts_availability)
        self.preference_starts_ts = self.instance.get_employee_preference_start_ts()
        self.preference_hours_employee = self.instance.get_employe_prefererence_hours()
        self.preference_slots = self.instance.get_employee_time_slots_preferences()
        self.employee_holiday = self.instance._get_employee_holidays()


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

    def create_constraints(self, model):
        # RQ00: objective function - minimize working hours
        model += pl.lpSum(
            pl.lpSum(self.works[ts, e] for e in self.ts_employees[ts]) * self.demand[ts]
            for ts in self.ts_open
        )

        # RQ01: at least one employee at all times
        for ts, _employees in self.ts_employees.items():
            model += pl.lpSum(self.works[ts, e] for e in _employees) >= 1

        # RQ02: employees work their weekly hours
        for (w, e), max_slots in self.max_working_ts_week.items():
            model += (
                pl.lpSum(self.works[ts, e] for ts in self.workable_ts_week[w, e])
                == max_slots
            )

        # RQ03: employees can not exceed their daily hours
        for (d, e), slots in self.workable_ts_day.items():
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
        for (w, e), slots in self.workable_ts_week.items():
            model += (
                pl.lpSum(self.starts[ts, e] for ts in slots)
                <= self.max_working_days[w, e]
            )

        # RQ06: employees at least work the minimum hours
        for (d, e), slots in self.workable_ts_day.items():
            model += pl.lpSum(
                self.works[ts, e] for ts in slots
            ) >= self.min_working_ts_day[d, e] * pl.lpSum(
                self.starts[ts, e] for ts in slots
            )

        # RQ07: employees at least have to rest an amount of hours between working days.
        for (ts, ts2, e) in self.incompatible_ts_employee:
            model += self.works[ts, e] + self.works[ts2, e] <= 1

        # RQ08: a manager has to be working at all times
        for ts, _employees in self.ts_managers.items():
            model += pl.lpSum(self.works[ts, e] for e in _employees) >= 1

        # RQ09: The demand for each skill should be covered
        if self.instance.get_requirements("skill_demand"):
            for (ts, id_skill, skill_demand), _employees in self.ts_demand_employee_skill.items():
                model += pl.lpSum(self.works[ts, e] for e in _employees) >= skill_demand


        if self.instance.get_requirements("employee_preferences"):
            # RQ13: Starting hour preference
            for (d, e), slots in self.preference_starts_ts.items():
                model += pl.lpSum(self.starts[ts, e] for ts in slots) == 1

            # RQ14: max preference hours
            for (d, e), slots in self.preference_slots.items():
                model += pl.lpSum(self.works[ts, e] for ts in slots) <= self.preference_hours_employee[d, e]

        return model
