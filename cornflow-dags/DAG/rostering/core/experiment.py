"""

"""

# Imports from libraries
import os
from pytups import SuperDict, TupList

# Imports from cornflow libraries
from cornflow_client import ExperimentCore
from cornflow_client.core.tools import load_json

# Imports from internal modules
from .instance import Instance
from .solution import Solution


class Experiment(ExperimentCore):
    schema_checks = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/solution_checks.json")
    )

    def __init__(self, instance: Instance, solution: Solution = None) -> None:
        ExperimentCore.__init__(self, instance=instance, solution=solution)
        if solution is None:
            self.solution = Solution(SuperDict(works=SuperDict()))

    @property
    def instance(self) -> Instance:
        return super().instance

    @property
    def solution(self) -> Solution:
        return super().solution

    @solution.setter
    def solution(self, value):
        self._solution = value

    def get_objective(self) -> float:
        return self.solution.get_working_hours()

    def get_indicators(self) -> dict:
        return {
            "objective_function": self.get_objective(),
            "only_one_employee_percentage": self.get_one_employee_percentage(),
            "mean_demand": self.get_mean_demand_employee(),
            "max_demand": self.get_max_demand_employee(),
            "min_demand": self.get_min_demand_employee(),
        }

    def solve(self, options: dict) -> dict:
        raise NotImplementedError()

    def check_slots_without_workers(self) -> list:
        """Checks if there is any time slot where no employees are working"""
        time_slots_open = self.instance.get_opening_time_slots_set()
        time_slots_assigned = self.solution.get_time_slots().to_set()
        return [{"timeslot": k} for k in time_slots_open - time_slots_assigned]

    def check_slots_closed_with_workers(self) -> list:
        """Checks if there is any time slot where an employee is working, but it shouldn't"""
        time_slots_open = self.instance.get_opening_time_slots_set()
        time_slots_assigned = self.solution.get_time_slots().to_set()
        return [{"timeslot": k} for k in time_slots_assigned - time_slots_open]

    def check_difference_hours_worked(self) -> list:
        """Checks the difference between the hours in the contract and the worked hours for each employee and week"""
        max_slots = self.instance.get_max_working_slots_week()
        worked_slots = self.solution.get_hours_worked_per_week()

        return (
            (worked_slots - max_slots)
            .vapply(self.instance.slot_to_hour)
            .vfilter(lambda v: v)
            .to_tuplist()
            .vapply(lambda v: {"week": v[0], "id_employee": v[1], "extra_hours": v[2]})
        )

    def check_manager_present(self) -> list:
        """Checks if there is any time slot where no managers are working"""
        managers = self.instance.get_employees_managers()
        time_slots_managers = (
            self.solution.get_ts_employee()
            .vapply(lambda v: [e for e in v if e in managers])
            .vfilter(lambda v: len(v))
            .keys_tl()
            .to_set()
        )

        time_slots_open = self.instance.get_opening_time_slots_set()
        return [{"timeslot": k} for k in time_slots_open - time_slots_managers]

    def check_skills_demand(self) -> list:
        """Checks if there are any time slot where the skill demand is not covered"""
        if self.instance.get_requirement("rq09"):
            ts_employee = self.solution.get_ts_employee()

            ts_skill_demand = SuperDict(
                {
                    (
                        self.instance.get_time_slot_string(ts),
                        id_skill,
                    ): self.instance.filter_skills_demand(ts, id_skill)
                    for ts in self.instance.time_slots
                    for id_skill in self.instance.get_skills()
                }
            )
            ts_skill_worked = SuperDict(
                {
                    (ts, skill): sum(
                        1
                        for e in employees
                        if e in self.instance.get_employees_by_skill(skill)
                    )
                    for ts, employees in ts_employee.items()
                    for skill in self.instance.get_skills()
                }
            )

            demand_minus_worked = ts_skill_demand - ts_skill_worked
            return (
                demand_minus_worked.vfilter(lambda v: v > 0)
                .to_tuplist()
                .vapply(
                    lambda v: {
                        "timeslot": v[0],
                        "id_skill": v[1],
                        "number_missing": v[2],
                    }
                )
            )
        else:
            return TupList([])

    def check_days_worked_per_week(self):
        """Checks if an employee works more days than the number of days on their contract"""
        max_working_slots_week = self.instance.get_max_working_days()

        return (
            self.solution.get_ts_employee()
            .to_tuplist()
            .vapply_col(
                None,
                lambda v: self.instance.get_week_from_ts(
                    self.instance.get_datetime_from_string(v[0])
                ),
            )
            .to_dict(result_col=0, indices=[2, 1])
            .vapply(lambda v: len(v.vapply(lambda vv: vv[:10]).unique()))
            .kvfilter(lambda k, v: v > max_working_slots_week[k])
            .to_tuplist()
            .vapply(
                lambda v: {
                    "week": v[0],
                    "id_employee": v[1],
                    "nb_days_worked": v[2],
                    "max_days_week": max_working_slots_week[v[0], v[1]],
                }
            )
        )

    def check_min_hours_worked_day(self):
        """Checks if an employee works less than the minimum hours"""
        min_worked_ts_day = self.instance.get_min_working_slots_day()

        return (
            self.solution.get_ts_employee()
            .to_tuplist()
            .vapply_col(None, lambda v: v[0][:10])
            .to_dict(result_col=[0], indices=[2, 1])
            .vapply(lambda v: len(v))
            .kvfilter(lambda k, v: v < min_worked_ts_day[k])
            .to_tuplist()
            .vapply(
                lambda v: {
                    "date": v[0],
                    "id_employee": v[1],
                    "nb_hours_worked": self.instance.slot_to_hour(v[2]),
                    "min_hours_day": self.instance.slot_to_hour(
                        min_worked_ts_day[v[0], v[1]]
                    ),
                }
            )
        )

    def check_employee_holidays(self):
        """Checks that no employee works on their holidays"""
        ts_employee_holidays = self.instance.get_employee_time_slots_holidays()
        return (
            self.solution.get_ts_employee()
            .to_tuplist()
            .vfilter(lambda v: v in ts_employee_holidays)
            .vapply_col(None, lambda v: v[0][:10])
            .vapply(lambda v: {"date": v[2], "id_employee": v[1]})
        )

    def check_employees_downtime(self):
        """Checks that no employee works on their downtime"""
        employee_downtime = self.instance._get_employee_downtime()

        return (
            self.solution.get_ts_employee()
            .to_tuplist()
            .vapply_col(None, lambda v: v[0][:10])
            .unique()
            .take([1, 2])
            .vfilter(lambda v: v in employee_downtime)
            .vapply(lambda v: {"date": v[1], "id_employee": v[0]})
        )

    def check_start_hour_preference(self):
        """Checks that start hour preferences are respected"""
        start_preferences = self.instance.get_employee_preference_start_ts()

        return (
            self.solution.get_ts_employee()
            .to_tuplist()
            .vapply_col(None, lambda v: v[0][:10])
            .to_dict(result_col=0, indices=[2, 1])
            .vapply(lambda v: min(v))
            .kvfilter(lambda k, v: v not in start_preferences.get(k, [v]))
            .to_tuplist()
            .vapply(
                lambda v: {"date": v[0], "id_employee": v[1], "start_hour": v[2][11:]}
            )
        )

    def check_number_hours_preference(self):
        """Checks that the preferred number of hours worked is respected"""
        preference_hours_employee = self.instance.get_employee_preference_hours()

        return (
            self.solution.get_ts_employee()
            .to_tuplist()
            .vapply_col(None, lambda v: v[0][:10])
            .to_dict(result_col=0, indices=[2, 1])
            .vapply(lambda v: self.instance.slot_to_hour(len(v)))
            .kvfilter(lambda k, v: v > preference_hours_employee.get(k, v))
            .to_tuplist()
            .vapply(
                lambda v: {
                    "date": v[0],
                    "id_employee": v[1],
                    "number_hours_worked": v[2],
                }
            )
        )

    def check_employee_work_days(self) -> TupList:
        """Checks if some employees are assigned to work on their days off"""
        work_days = self.instance.get_employee_time_slots_rest_days().take([1, 2])
        return (
            self.solution.get_ts_employee()
            .to_tuplist()
            .vapply_col(0, lambda v: v[0][:10])
            .intersect(work_days)
            .vapply(lambda v: {"date": v[0], "id_employee": v[1]})
        )

    def check_fixed_worktable(self) -> TupList:
        """Checks if some parts of the fixed worktable are not respected"""
        ts_employee = self.solution.get_ts_employee().to_tuplist()

        return (
            self.instance.get_fixed_worktable()
            .vfilter(lambda v: v not in ts_employee)
            .vapply(lambda v: {"time_slot": v[0], "id_employee": v[1]})
        )

    def get_one_employee_percentage(self) -> float:
        """Returns the percentage of time slots where only one employee is working"""
        ts_employee = self.solution.get_ts_employee()
        return (
            sum(1 for e in ts_employee.values() if len(e) == 1)
            / len(self.instance.time_slots)
            * 100
        )

    def get_mean_demand_employee(self) -> float:
        """Returns the mean demand of employees"""
        demand = self.instance.get_demand()
        return sum(
            [
                demand[ts] / len(employees)
                for ts, employees in self.solution.get_ts_employee().items()
            ]
        ) / len(self.solution.get_ts_employee().keys_l())

    def get_max_demand_employee(self) -> float:
        """Returns the max demand of employees"""
        demand = self.instance.get_demand()
        return max(
            [
                demand[ts] / len(employees)
                for ts, employees in self.solution.get_ts_employee().items()
            ]
        )

    def get_min_demand_employee(self) -> float:
        """Returns the min demand of employees"""
        demand = self.instance.get_demand()
        return min(
            [
                demand[ts] / len(employees)
                for ts, employees in self.solution.get_ts_employee().items()
            ]
        )
