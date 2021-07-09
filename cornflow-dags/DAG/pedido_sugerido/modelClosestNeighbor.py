from .experiment import Experiment
from .solution import Solution


class Algorithm(Experiment):
    def __init__(self, instance, solution=None):
        super().__init__(instance, solution)
        return

    def solve(self, options):

        data = self.instance.data
        nodes = data["demand"].keys_l()
        # arcs indexed by node:
        arcs_i = data["arcs"].to_dictdict()
        demand = data["demand"].get_property("demand")
        max_capacity = data["parameters"].get("capacity", 10000)

        # iterations
        depot = node = data["depots"][0]["n"]
        route = 0
        solution = {route: [node]}
        remaining_nodes = set(nodes)
        remaining_nodes.remove(node)
        route = 0
        rem_cap = max_capacity

        # we will look for the nearest neighbor at each time:
        while len(remaining_nodes):
            # get remaining neighbors:
            neighbors = arcs_i[node].filter(remaining_nodes)
            # get closest distance and neighbor
            min_options = min(neighbors.values_tl())
            node = neighbors.vfilter(lambda v: v == min_options).keys_l(0)
            # check if capacity is reached:
            if rem_cap >= demand[node]:
                # we're good: we decrease current route capacity
                rem_cap -= demand[node]
                # and we add the node to the current route:
                solution[route].append(node)
                # finally: we remove it from remaining nodes:
                remaining_nodes.remove(node)
                continue
            # we're not good: we close the previous route:
            node = depot
            solution[route].append(node)
            # and we start another route from the depot!
            rem_cap = max_capacity
            route += 1
            solution[route] = [node]

        # we close the last route:
        solution[route].append(depot)
        self.solution = Solution(dict(routes=solution))
        return 2
