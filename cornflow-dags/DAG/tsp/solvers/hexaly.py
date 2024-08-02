import hexaly.optimizer
from pytups import TupList, SuperDict
from ..core import Solution, Experiment
import numpy as np


class Hexaly(Experiment):
    """
    The following model was taken from the hexaly python examples: https://www.hexaly.com/docs/last/exampletour/tsp.html
    """

    def solve(self, options: dict):

        # nb_cities
        distances_per_arc = (
            self.instance.get_arcs()
            .to_dict(result_col=["w"], indices=["n1", "n2"], is_list=False)
            .kfilter(lambda k: k[0] != k[1])
        )
        # key -> position
        my_cities = distances_per_arc.keys_tl().take(0).unique().to_dict(None)
        dist_matrix_data = np.zeros([len(my_cities), len(my_cities)])
        for k, v in distances_per_arc.items():
            dist_matrix_data[my_cities[k[0]], my_cities[k[1]]] = v
        city_order, status = solve(hexaly, dist_matrix_data, options)
        nodes = TupList(city_order).kvapply(lambda k, v: SuperDict(pos=k, node=v))
        self.solution = Solution(dict(route=nodes))

        return dict(status=status, status_sol=None)


def solve(hexaly, dist_matrix_data, options):
    with hexaly.optimizer.HexalyOptimizer() as optimizer:
        nb_cities = len(dist_matrix_data) + 1
        #
        # Declare the optimization model
        model = optimizer.model

        # A list variable: cities[i] is the index of the ith city in the tour
        cities = model.list(nb_cities)

        # All cities must be visited
        model.constraint(model.count(cities) == nb_cities)

        # Create an Hexaly array for the distance matrix in order to be able
        # to access it with "at" operators
        dist_matrix = model.array(dist_matrix_data)

        # Minimize the total distance
        dist_lambda = model.lambda_function(
            lambda i: model.at(dist_matrix, cities[i - 1], cities[i])
        )
        obj = model.sum(model.range(1, nb_cities), dist_lambda) + model.at(
            dist_matrix, cities[nb_cities - 1], cities[0]
        )
        model.minimize(obj)

        model.close()

        # Parameterize the optimizer
        optimizer.param.time_limit = int(options.get("timeLimit", 5))

        status = optimizer.solve()

        return [c for c in cities.value], status
