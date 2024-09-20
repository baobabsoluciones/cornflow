import os
from cornflow_client import InstanceCore, get_empty_schema
from cornflow_client.core.tools import load_json
import pytups as pt
import math
from .tools import pos_to_row_col, add_pos_square, row_col_to_pos, row_col_to_square

from typing import Optional


class Instance(InstanceCore):
    schema = load_json(os.path.join(os.path.dirname(__file__), "../schemas/input.json"))
    schema_checks = get_empty_schema()
    data: pt.SuperDict

    def __init__(self, data: dict):
        data = pt.SuperDict(data)
        data["initial_values"] = pt.TupList(data["initial_values"])
        super().__init__(data)

    @classmethod
    def from_txt_file(
        cls, filePath, line_number: int = 0, contents: Optional[str] = None
    ):
        # if content is given, filePath is ignored:
        if contents is None:
            with open(filePath, "r") as f:
                contents = f.read().splitlines()
        else:
            contents = [contents]
            line_number = 0
        empty_chars = {".", "0"}
        my_chars = [
            el if el not in empty_chars else None for el in contents[line_number]
        ]

        size = int(math.sqrt(len(my_chars)))
        value_by_position = (
            pt.TupList(my_chars)
            .kvapply(lambda k, v: dict(pos=k, value=v))
            .vfilter(lambda v: v["value"] is not None)
        )

        def get_element(el):
            row, col = pos_to_row_col(el["pos"], size)
            return pt.SuperDict(row=row, col=col, value=int(el["value"]))

        data = pt.SuperDict(
            initial_values=value_by_position.vapply(get_element),
            parameters=dict(size=size),
        )

        return Instance.from_dict(data)

    def get_initial_values(self) -> pt.TupList[dict]:
        my_size = self.data["parameters"]["size"]
        return add_pos_square(self.data["initial_values"], my_size)

    def get_parameter(self, key=None) -> pt.SuperDict | int | str | None:
        if key is None:
            return self.data["parameters"]
        return self.data["parameters"][key]

    def get_size(self):
        return self.get_parameter("size")

    @classmethod
    def from_dict(self, data: dict) -> "Instance":
        return Instance(data)

    def to_dict(self) -> pt.SuperDict:
        my_data = self.data.copy_deep()
        return my_data

    def generate_all_positions(self):
        size = self.get_size()
        all_positions = (
            pt.SuperDict(
                row=row,
                col=col,
                pos=row_col_to_pos(row, col, size),
                square=row_col_to_square(row, col, int(math.sqrt(size))),
            )
            for row in range(size)
            for col in range(size)
        )
        all_positions = pt.TupList(all_positions).to_dict(
            None, indices="pos", is_list=False
        )
        return all_positions

    def values_to_matrix(self, values):
        size = self.get_size()
        my_matrix = [[0 for _ in range(size)] for _ in range(size)]
        for el in values:
            my_matrix[el["row"]][el["col"]] = el["value"]
        return my_matrix

    def print(self):
        values = self.get_initial_values()
        board = self.values_to_matrix(values)
        return self.generate_board(board)

    def generate_board(self, board):
        # Taken from response of Alain. T in https://stackoverflow.com/a/56581709/6508131
        side = self.get_size()
        base = int(math.sqrt(side))

        def expandLine(line):
            return (
                line[0] + line[5:9].join([line[1:5] * (base - 1)] * base) + line[9:13]
            )

        line0 = expandLine("╔═══╤═══╦═══╗")
        line1 = expandLine("║ . │ . ║ . ║")
        line2 = expandLine("╟───┼───╫───╢")
        line3 = expandLine("╠═══╪═══╬═══╣")
        line4 = expandLine("╚═══╧═══╩═══╝")

        symbol = " 1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        nums = [[""] + [symbol[n] for n in row] for row in board]
        print(line0)
        for r in range(1, side + 1):
            print("".join(n + s for n, s in zip(nums[r - 1], line1.split("."))))
            print([line2, line3, line4][(r % side == 0) + (r % base == 0)])
