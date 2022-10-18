"""

"""
# Imports from libraries
import os
from pytups import SuperDict

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

    def check_solution(self, *args, **kwargs) -> dict:
        return SuperDict(
            slots_without_workers=self.check_slots_without_workers(),
            slots_closed_with_workers=self.check_working_without_opening(),
            difference_hours_worked=self.check_hours_worked(),
            manager_present=self.check_manager_present(),
            skills_demand=self.check_skills_demand(),
        ).vfilter(lambda v: len(v))

    def get_objective(self) -> float:
        return self.solution.get_working_hours()

    def get_indicators(self) -> dict:
        return {"of": self.get_objective()}

    def solve(self, options: dict) -> dict:
        raise NotImplementedError()

    def check_slots_without_workers(self) -> list:
        """Checks if there is any time slot where no employees are working"""
        time_slots_open = self.instance.get_opening_time_slots_set()
        time_slots_assigned = self.solution.get_time_slots().to_set()
        return [{"timeslot": k} for k in time_slots_open - time_slots_assigned]

    def check_working_without_opening(self) -> list:
        """Checks if there is any time slot where an employee is working but it shouldn't"""
        time_slots_open = self.instance.get_opening_time_slots_set()
        time_slots_assigned = self.solution.get_time_slots().to_set()
        return [{"timeslot": k} for k in time_slots_assigned - time_slots_open]

    def check_hours_worked(self) -> list:
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
        ts_employee = self.solution.get_ts_employee()

        ts_skill_demand = SuperDict(
            {
                (
                    self.instance._get_time_slot_string(ts),
                    id_skill,
                ): self.instance._filter_skills_demand(ts, id_skill)
                for ts in self.instance.time_slots
                for id_skill in self.instance._get_skills()
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
                for skill in self.instance._get_skills()
            }
        )

        demand_minus_worked = ts_skill_demand - ts_skill_worked
        return (
            demand_minus_worked.vfilter(lambda v: v > 0)
            .to_tuplist()
            .vapply(
                lambda v: {"timeslot": v[0], "id_skill": v[1], "number_missing": v[2]}
            )
        )
