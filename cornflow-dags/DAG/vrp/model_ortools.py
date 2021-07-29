from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from .experiment import Experiment
from .solution import Solution


class Algorithm(Experiment):
    def __init__(self, instance, solution=None):
        super().__init__(instance, solution)
        return

    @staticmethod
    def get_objective_distance(solut, arcs_dict):
        """
        Returns value of Objective Function when it is computed using distance
        :param solut: Solution of the resolution method
        :param arcs_dict: Dictionary with arc distances
        :return:
        """

        distance = 0
        for i in solut.data["routes"]:

            route = solut.data["routes"][i]
            route_distance = 0

            for j in range(len(route) - 1):
                route_distance += arcs_dict[(route[j], route[j + 1])]

            distance += route_distance

        return distance

    @staticmethod
    def get_solution_ort(manager, routing, solution, nodes_list):
        """
        Retrieves solution from the ORtools optimization engine
        :param manager: object pywrapcp.RoutingIndexManager
        :param routing: object pywrapcp.RoutingModel
        :param solution: return from routing.SolveWithParameters
        :param nodes_list: list that contains the identifier of each node
        :return: dictionary with the routes as dictionaries with vehicle_id as key and a ordered list with the nodes
        """
        solution_export = dict()
        for vehicle_id in range(routing.vehicles()):
            index = routing.Start(vehicle_id)
            solution_export[vehicle_id] = list()
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                solution_export[vehicle_id].append(nodes_list[node_index])
                index = solution.Value(routing.NextVar(index))
            solution_export[vehicle_id].append(nodes_list[manager.IndexToNode(index)])

            if len(solution_export[vehicle_id]) <= 2:
                solution_export.pop(vehicle_id)

        return Solution(dict(routes=solution_export))

    def solve(self, options):
        """
        Method that solves the CP problem with ORtools
        :param options: options to be used in the first solution strategy (not used)
        :return:
        """
        data = self.instance.data
        # Initial data
        depots = data["depots"]
        demand = data["demand"].get_property("demand")
        arcs = data["arcs"]
        parameters = data["parameters"]
        nodes = data["demand"].keys_l()

        # Depots. Operations to adapt to ORTools notation
        depots_l = [i["n"] for i in depots]

        starts = depots_l
        ends = depots_l

        # Defining max number of active routes. If Inf vehicle number --> amount of nodes
        if parameters["numVehicles"] <= 0:
            max_active_vehicles = parameters["size"]
        else:
            max_active_vehicles = parameters["numVehicles"]

        # Defining lists of nodes used as starts and ends
        starts_v = starts * max_active_vehicles
        ends_v = ends * max_active_vehicles
        starts_i = [nodes.index(v) for v in starts_v]
        ends_i = [nodes.index(v) for v in ends_v]

        # Defining total number of router
        total_routes = len(depots_l) * max_active_vehicles

        vehicle_capacities = parameters["capacity"]

        # Operations to create list of vehicle capacities depending on the amount of vehicles
        if parameters["numVehicles"] <= 0:
            parameters["numVehicles"] = parameters["size"]

        if isinstance(vehicle_capacities, list):
            if (len(vehicle_capacities) == 1) & (max_active_vehicles > 1):
                vehicle_capacities = [vehicle_capacities] * total_routes
        else:
            vehicle_capacities = [vehicle_capacities] * total_routes

        manager = pywrapcp.RoutingIndexManager(
            parameters["size"], total_routes, starts_i, ends_i
        )

        routing = pywrapcp.RoutingModel(manager)

        routing.SetMaximumNumberOfActiveVehicles(max_active_vehicles)

        # Create and register a transit callback.
        def distance_callback(from_index, to_index):
            """
            Returns the distance between the two nodes.
            :param from_index: initial node (using position index)
            :param to_index: final node (using position index)
            :return: distance between from_index and to_index (nodes). (Numerical)
            """

            # Convert from routing variable Index to distance matrix NodeIndex.
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return arcs[(nodes[from_node], nodes[to_node])]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Add Capacity constraint.
        def demand_callback(from_index):
            """
            Returns the demand of the node.
            :param from_index: node (index) for which demand is required
            :return: demand for node from_index
            """
            # Convert from routing variable Index to demands NodeIndex.
            from_node = manager.IndexToNode(from_index)
            value = demand[nodes[from_node]]
            return value

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            vehicle_capacities,  # vehicle maximum capacities
            True,  # start cumul to zero
            "Capacity",
        )

        # Setting first solution heuristic.
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.FromSeconds(1)

        # Solve the problem.
        solution = routing.SolveWithParameters(search_parameters)

        # Print solution on console.
        if solution:
            self.solution = self.get_solution_ort(manager, routing, solution, nodes)

        return 2
