"""

"""
# Imports from libraries
import os
import pickle
from pytups import SuperDict, TupList

# Imports from cornflow libraries
from cornflow_client import SolutionCore
from cornflow_client.core.tools import load_json

# Imports from internal modules
from .tools import get_week_from_string


class Solution(SolutionCore):
    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/solution.json")
    )

    @classmethod
    def from_dict(cls, data: dict) -> "Solution":
        data_p = {
            el: {(v["id_employee"], v["time_slot"]): v for v in data[el]}
            for el in ["works"]
        }

        return cls(SuperDict(data_p))

    def to_dict(self) -> dict:
        return {"works": pickle.loads(pickle.dumps(self.data["works"].values_l(), -1))}

    def get_time_slots(self) -> TupList[str]:
        """
        Returns a TupList with all the time slots where someone has worked. It can contain duplicated values
        For example: ["2021-09-06T07:00", "2021-09-06T08:00", "2021-09-06T08:00", ...]
        """
        return TupList([(v["time_slot"]) for v in self.data["works"].values()])

    def get_working_hours(self) -> int:
        """
        Returns the number of total hours worked in the solution
        """
        return len(self.data["works"])

    def get_hours_worked_per_week(self) -> SuperDict:
        """
        Returns a SuperDict with the amount of time slots worked by each employee in each week.
        For example: {(0, 1): 40, ...}
        """
        return (
            TupList(
                {"id_employee": id_employee, "ts": ts, "week": get_week_from_string(ts)}
                for (id_employee, ts) in self.data["works"]
            )
            .to_dict(result_col="ts", indices=["week", "id_employee"])
            .vapply(lambda v: len(v))
        )

    def get_ts_employee(self) -> SuperDict:
        """
        Returns a SuperDict with the time slot as a key and a list of employees that work each time slot as the value
        For example: {"2021-09-06T07:00": [1, 2], "2021-09-06T08:00": [1, 2, 4], ...}
        """
        return TupList([v for v in self.data["works"]]).to_dict(0)
