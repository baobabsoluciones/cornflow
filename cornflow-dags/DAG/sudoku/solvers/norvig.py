from cornflow_client.constants import (
    STATUS_OPTIMAL,
    STATUS_UNDEFINED,
    SOLUTION_STATUS_FEASIBLE,
    SOLUTION_STATUS_INFEASIBLE,
)
import pytups as pt
from ..core import Solution, Experiment
from ..core.tools import pos_to_row_col

# this method implements Peter Norvig's method as explained here:
# credit goes to Peter Norvig
# https://github.com/norvig/pytudes/blob/main/ipynb/Sudoku.ipynb
import re
from typing import Dict, Optional, List


def cross(A, B) -> tuple:
    "Cross product of strings in A and strings in B."
    return tuple(a + b for a in A for b in B)


Digit = str  # e.g. '1'
digits = "123456789"
DigitSet = str  # e.g. '123'
rows = "ABCDEFGHI"
cols = digits
Square = str  # e.g. 'A9'
squares = cross(rows, cols)
Grid = Dict[Square, DigitSet]  # E.g. {'A9': '123', ...}
all_boxes = [
    cross(rs, cs) for rs in ("ABC", "DEF", "GHI") for cs in ("123", "456", "789")
]
all_units = [cross(rows, c) for c in cols] + [cross(r, cols) for r in rows] + all_boxes
units = {s: tuple(u for u in all_units if s in u) for s in squares}
peers = {s: set().union(*units[s]) - {s} for s in squares}
Picture = str


def is_solution(solution: Grid, puzzle: Grid) -> bool:
    "Is this proposed solution to the puzzle actually valid?"
    return (
        solution is not None
        and all(solution[s] in puzzle[s] for s in squares)
        and all({solution[s] for s in unit} == set(digits) for unit in all_units)
    )


def constrain(grid) -> Grid:
    "Propagate constraints on a copy of grid to yield a new constrained Grid."
    result: Grid = {s: digits for s in squares}
    for s in grid:
        if len(grid[s]) == 1:
            fill(result, s, grid[s])
    return result


def fill(grid: Grid, s: Square, d: Digit) -> Optional[Grid]:
    """Eliminate all the digits except d from grid[s]."""
    if grid[s] == d or all(eliminate(grid, s, d2) for d2 in grid[s] if d2 != d):
        return grid
    else:
        return None


def eliminate(grid: Grid, s: Square, d: Digit) -> Optional[Grid]:
    """Eliminate d from grid[s]; implement the two constraint propagation strategies."""
    if d not in grid[s]:
        return grid  ## Already eliminated
    grid[s] = grid[s].replace(d, "")
    if not grid[s]:
        return None  ## None: no legal digit left
    elif len(grid[s]) == 1:
        # 1. If a square has only one possible digit, then eliminate that digit as a possibility for each of the square's peers.
        d2 = grid[s]
        if not all(eliminate(grid, s2, d2) for s2 in peers[s]):
            return None  ## None: can't eliminate d2 from some square
    for u in units[s]:
        dplaces = [s for s in u if d in grid[s]]
        # 2. If a unit has only one possible square that can hold a digit, then fill the square with the digit.
        if not dplaces or (len(dplaces) == 1 and not fill(grid, dplaces[0], d)):
            return None  ## None: no place in u for d
    return grid


def parse(picture) -> Grid:
    """Convert a Picture to a Grid."""
    vals = re.findall(r"[.1-9]|[{][1-9]+[}]", picture)
    assert len(vals) == 81
    return {
        s: digits if v == "." else re.sub(r"[{}]", "", v) for s, v in zip(squares, vals)
    }


def picture(grid) -> Picture:
    """Convert a Grid to a Picture string, one line at a time."""
    if grid is None:
        return "None"

    def val(d: DigitSet) -> str:
        return "." if d == digits else d if len(d) == 1 else "{" + d + "}"

    maxwidth = max(len(val(grid[s])) for s in grid)
    dash1 = "-" * (maxwidth * 3 + 2)
    dash3 = "\n" + "+".join(3 * [dash1])

    def cell(r, c):
        return val(grid[r + c]).center(maxwidth) + ("|" if c in "36" else " ")

    def line(r):
        return "".join(cell(r, c) for c in cols) + (dash3 if r in "CF" else "")

    return "\n".join(map(line, rows))


def search(grid) -> Optional[Grid]:
    "Depth-first search with constraint propagation to find a solution."

    if grid is None:
        return None
    s = min(
        (s for s in squares if len(grid[s]) > 1),
        default=None,
        key=lambda s: len(grid[s]),
    )
    if s is None:  # No squares with multiple possibilities; the search has succeeded
        return grid
    for d in grid[s]:
        solution = search(fill(grid.copy(), s, d))
        if solution:
            return solution
    return None


def solve_puzzles(puzzles: List[Grid], verbose=True) -> int:
    "Solve and verify each puzzle, and if `verbose`, print puzzle and solution."
    for puzzle in puzzles:
        solution = search(constrain(puzzle))
        assert is_solution(solution, puzzle)
        if verbose:
            print_side_by_side(
                "\nPuzzle:\n" + picture(puzzle), "\nSolution:\n" + picture(solution)
            )
    return len(puzzles)


def print_side_by_side(left, right, width=20):
    """Print two strings side-by-side, line-by-line, each side `width` wide."""
    for L, R in zip(left.splitlines(), right.splitlines()):
        print(L.ljust(width), R.ljust(width))


class Norvig(Experiment):
    fail_counter: int

    def search(self, grid) -> Optional[Grid]:
        """
        "Depth-first search with constraint propagation to find a solution."
        Note: we have modified the original stateless function so we can count the number of failed searches.
        """

        if grid is None:
            self.fail_counter += 1
            return None
        s = min(
            (s for s in squares if len(grid[s]) > 1),
            default=None,
            key=lambda s: len(grid[s]),
        )
        if (
            s is None
        ):  # No squares with multiple possibilities; the search has succeeded
            return grid
        for d in grid[s]:
            solution = self.search(fill(grid.copy(), s, d))
            if solution:
                return solution
        self.fail_counter += 1
        return None

    def solve(self, options: dict):
        # we need to convert the instance into the right format.
        initial_values = self.instance.get_initial_values()
        size = self.instance.get_size()
        if size != 9:
            raise ValueError("This method only solves size-9 sudokus")

        # we initialize the grid and then fill the initial values:
        grid = {s: digits for s in squares}
        for value in initial_values:
            grid[squares[value["pos"]]] = str(value["value"])
        # we initialize the fail counter
        self.fail_counter = 0
        # we run the "constrain + search" procedure
        solution = self.search(constrain(grid))
        if not is_solution(solution, grid):
            return dict(
                status=STATUS_UNDEFINED,
                status_sol=SOLUTION_STATUS_INFEASIBLE,
            )
        # we put the solution in the right format
        solution_data = pt.TupList()
        for pos, s in enumerate(squares):
            value = int(solution[s])
            row, col = pos_to_row_col(pos, size)
            solution_data.append(pt.SuperDict(row=row, col=col, value=value))
        self.solution = Solution.from_dict(
            pt.SuperDict(
                assignment=solution_data,
                indicators=dict(num_fails=self.fail_counter),
            )
        )
        return dict(status=STATUS_OPTIMAL, status_sol=SOLUTION_STATUS_FEASIBLE)
