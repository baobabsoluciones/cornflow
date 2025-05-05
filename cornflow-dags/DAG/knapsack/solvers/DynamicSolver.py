from ..core import Solution
from ..core import Experiment
import numpy as np
from cornflow_client.constants import STATUS_FEASIBLE, SOLUTION_STATUS_FEASIBLE


class DynamicSolver(Experiment):
    def __init__(self, instance, solution=None):
        self.log = ""
        if solution is None:
            solution = Solution({"include": []})
        super().__init__(instance, solution)
        self.log += "Initialized\n"

    def solve(self, config):
        self.log += "Converting data lists to arrays\n"
        self.weights = np.array(self.instance.data["weights"])
        self.values = np.array(self.instance.data["values"])

        self.log += "Solver chosen : Dynamic\n"
        idx = self.weights.argsort()
        self.weights = self.weights[idx]
        self.values = self.values[idx]

        self.log += "Launching dynamic solver \n"
        res = self.dyn_solver()
        self.log += "Sorting the final arrays\n"
        idx2 = idx.argsort()
        res["include"] = (np.array(res["include"])[idx2]).tolist()
        self.solver = "Dynamic"

        for i in range(len(res["include"])):
            if res["include"][i] == 1:
                self.solution.data["include"].append({"id": i})

        return dict(status=STATUS_FEASIBLE, status_sol=SOLUTION_STATUS_FEASIBLE)

    def dyn_solver(self):
        """
        Solves the 0/1 knapsack problem using standard dynamic programming.
        Returns a dictionary containing the list of included items.
        """
        n = self.instance.data["nb_objects"]
        W = self.instance.data["weight_capacity"]
        weights = self.weights
        values = self.values

        # dp[i][w]: max value using items 0..i-1 with capacity w
        # We add 1 to dimensions for easier 1-based indexing corresponding to items
        dp = np.zeros((n + 1, W + 1))

        # keep[i][w]: 1 if item i-1 is included in optimal solution for dp[i][w], 0 otherwise
        # Helps in reconstructing the solution path
        keep = np.zeros((n + 1, W + 1), dtype=int)

        self.log += "Filling DP table\n"
        # Iterate through items (1 to n)
        for i in range(1, n + 1):
            # Get the 0-based index for the current item
            item_idx = i - 1
            weight_i = weights[item_idx]
            value_i = values[item_idx]

            # Iterate through capacities (0 to W)
            for w in range(W + 1):
                # Option 1: Don't include item i-1. Value is the same as for i-1 items.
                value_without_i = dp[i - 1, w]

                # Option 2: Include item i-1 (only if capacity allows)
                value_with_i = -1.0  # Sentinel: assume not possible initially
                if weight_i <= w:
                    # Value is value of item + max value for remaining capacity using previous items
                    value_with_i = dp[i - 1, w - weight_i] + value_i

                # Decide whether including item i-1 is better
                if value_with_i > value_without_i:
                    dp[i, w] = value_with_i
                    keep[i, w] = 1  # Mark that item i-1 was included for this state
                else:
                    dp[i, w] = value_without_i
                    keep[i, w] = 0  # Mark that item i-1 was not included

        self.log += "Tracing back solution\n"
        include = [0] * n  # Initialize solution list
        current_w = W  # Start with the maximum capacity

        # Iterate backwards through items (from n down to 1)
        for i in range(n, 0, -1):
            item_idx = i - 1  # 0-based index

            # Check if item i-1 was included in the optimal solution for dp[i][current_w]
            if keep[i, current_w] == 1:
                include[item_idx] = 1
                # Reduce capacity by the weight of the included item
                current_w -= weights[item_idx]

                # Sanity check: capacity should not become negative
                if current_w < 0:
                    self.log += (
                        f"Error: Negative capacity ({current_w}) reached during traceback "
                        f"at item {item_idx}. Aborting traceback.\n"
                    )
                    # Depending on desired behavior, could raise an error or return partial solution
                    break  # Stop the traceback

        # Prepare the result dictionary as expected by the caller
        res_dict = {"include": include}

        # Optional: Calculate and add final weight and value to the log or dict if needed
        final_value = dp[n, W]
        final_weight = sum(weights[idx] for idx, inc in enumerate(include) if inc == 1)
        self.log += f"Solving complete. Max value: {final_value}, Total weight: {final_weight}\n"

        return res_dict
