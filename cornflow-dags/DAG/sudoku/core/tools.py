import math
import pytups as pt
from typing import Tuple


def row_col_to_pos(row: int, col: int, size: int) -> int:
    return row * size + col


def row_col_to_square(row: int, col: int, len_square: int) -> int:
    return math.floor(row / len_square) * len_square + math.floor(col / len_square)


def pos_to_row_col(pos: int, size: int) -> Tuple[int, int]:
    row = math.floor(pos / size)
    return row, pos - row * size


def add_pos_square(values: pt.TupList[pt.SuperDict], size: int):
    # I make a copy of the dictionaries inside the list:
    values = values.vapply(lambda v: pt.SuperDict(v))

    # we expand the contents of the initial values with two columns:
    # pos: the position of the element.
    values.vapply_col("pos", lambda v: row_col_to_pos(v["row"], v["col"], size))
    # square: the square number of the element
    len_square = math.floor(math.sqrt(size))
    values.vapply_col(
        "square", lambda v: row_col_to_square(v["row"], v["col"], len_square)
    )
    return values
