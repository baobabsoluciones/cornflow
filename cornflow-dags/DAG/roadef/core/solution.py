from cornflow_client import SolutionCore
from cornflow_client.core.tools import load_json
from pytups import SuperDict, TupList
from .tools import copy
import os


class Solution(SolutionCore):
    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/solution.json")
    )

    def __init__(self, data):
        super(Solution, self).__init__(dict(shifts=data))

    def to_dict(self):
        info_shifts = [
            dict(
                id_shift=id_shift,
                driver=shift["driver"],
                trailer=shift["trailer"],
                departure_time=shift["departure_time"],
                initial_quantity=shift["initial_quantity"],
                nb_steps=len(shift["route"]),
            )
            for id_shift, shift in self.data["shifts"].items()
        ]

        details_shifts = [
            dict(
                id_shift=id_shift,
                day=shift["departure_time"] // (60 * 24),
                position=i,
                location=step["location"],
                quantity=step["quantity"],
                arrival=step["arrival"],
                departure=step["departure"],
                layover_before=step["layover_before"],
                driving_time_before_layover=step["driving_time_before_layover"],
                cumulated_driving_time=step["cumulated_driving_time"],
            )
            for id_shift, shift in self.data["shifts"].items()
            for i, step in enumerate(shift["route"])
        ]

        return dict(info_shifts=info_shifts, details_shifts=details_shifts)

    @classmethod
    def from_dict(cls, data_dict):

        rows = SuperDict(
            {
                (el["id_shift"], el["position"]): SuperDict(el)
                for el in data_dict["details_shifts"]
            }
        )
        details = rows.to_dictdict().vapply(
            lambda v: v.values_tl().sorted(key=lambda x: x["position"])
        )

        data = {
            shift["id_shift"]: SuperDict(shift) for shift in data_dict["info_shifts"]
        }
        for shift in data:
            data[shift]["route"] = details[shift]

        return cls(data)

    def copy(self) -> "Solution":
        return Solution(copy(self.data["shifts"]))

    def get_shifts_dict(self) -> SuperDict:
        return self.data["shifts"]

    def get_all_shifts(self) -> TupList:
        """ Returns a list with all the shifts """
        return self.data["shifts"].values_tl()

    def get_id_and_shifts(self) -> TupList:
        """ Returns a tuplist whose items are pairs composed by the id of the shift and the shift itself """
        return self.data["shifts"].items_tl()

    def get_shift_property(self, id_shift, prop):
        """ Returns property prop of the shift of given index """
        return self.data["shifts"][id_shift][prop]

    def nb_shifts(self):
        """ Returns the total number of shifts in the solution"""
        return len(self.data["shifts"])
