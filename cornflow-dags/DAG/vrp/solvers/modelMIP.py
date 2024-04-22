# Imports from libraries
from pyomo.environ import (
    SolverFactory,
    AbstractModel,
    Set,
    Param,
    Var,
    value,
    Constraint,
    Objective,
    minimize,
    NonNegativeIntegers,
    Binary,
)
from cornflow_client.constants import (
    STATUS_TIME_LIMIT,
    STATUS_NOT_SOLVED,
    PYOMO_STOP_MAPPING,
    SOLUTION_STATUS_INFEASIBLE,
    SOLUTION_STATUS_FEASIBLE,
)

# Imports from internal modules
from ..core import Experiment, Solution


class modelMIP(Experiment):
    def __init__(self, instance, solution=None):
        self.log = ""
        if solution is None:
            solution = Solution({"routes": {}})
        super().__init__(instance, solution)
        self.log += "Initialized\n"
        self.data = self.get_pyomo_dict_data()
        return

    def get_pyomo_dict_data(self):
        """
        Creates the dictionary according to pyomo format
        :return: pyomo dict
        """
        pyomo_instance = {
            # Sets
            "sNodes": self.instance.get_nodes(),
            "sArcs": self.instance.get_arcs(),
            "sVehicles": self.instance.get_vehicles(),
            "sDepots": self.instance.get_depots(),
            "sNodeSubset": {},  # initialized empty for first resolution. Using sSubtours as keys
            "sSubtours": [],  # initialized empty for first resolution
            # Parameters
            "pWeight": self.instance.get_weights(),
            "pDemand": self.instance.get_demand(),
            "pCapacity": self.instance.get_capacity(),
        }
        return pyomo_instance

    @staticmethod
    def get_mip_model():
        """
        Model created with pyomo. MIP formulation for CVRP
        :return: model
        """
        # Create model
        model = AbstractModel()

        # Model sets
        model.sNodes = Set()  # list of nodes to visit
        model.sArcs = Set()  # arcs between nodes
        model.sVehicles = Set()  # list of vehicles available
        model.sDepots = Set(within=model.sNodes)  # first and last node in every route

        model.sSubtours = Set()  # list of subnets to break in constraint 5
        model.sNodeSubset = Set(
            model.sSubtours, within=model.sNodes
        )  # subset of sNodes for every subtour

        # Model parameters
        model.pWeight = Param(
            model.sArcs, mutable=True, default=1
        )  # distance between nodes in an arc
        model.pDemand = Param(
            model.sNodes, mutable=True, default=0
        )  # demand in every node
        model.pCapacity = Param(mutable=True, default=0)  # vehicle capacity

        # Model variables
        # Binary variable, 1 if the vehicle travels from one node to another in an arc
        model.v01ArcInRoute = Var(model.sVehicles, model.sArcs, domain=Binary)

        # Model constraints
        # 1. Vehicle leaves every node that it enters
        def c1_vehicle_exits_node(model, iVehicle, iNode2):
            return sum(
                model.v01ArcInRoute[iVehicle, (iNode1, iNode2)]
                for iNode1 in model.sNodes
                if (iNode1, iNode2) in model.sArcs
            ) == sum(
                model.v01ArcInRoute[iVehicle, (iNode2, iNode3)]
                for iNode3 in model.sNodes
                if (iNode2, iNode3) in model.sArcs
            )

        # 2. Ensure that every node is entered once except the depot
        def c2_every_node_entered(model, iNode2):
            if iNode2 in model.sDepots:
                return Constraint.Skip
            return (
                sum(
                    model.v01ArcInRoute[iVehicle, (iNode1, iNode2)]
                    for iNode1 in model.sNodes
                    for iVehicle in model.sVehicles
                    if (iNode1, iNode2) in model.sArcs and iNode1 != iNode2
                )
                == 1
            )

        # 3. Every vehicle leaves a depot once
        def c3_vehicles_exit_depot(model, iVehicle):
            return (
                sum(
                    model.v01ArcInRoute[iVehicle, (iDepot, iNode2)]
                    for iDepot in model.sDepots
                    for iNode2 in model.sNodes
                    if (iDepot, iNode2) in model.sArcs
                )
                == 1
            )

        # 4. Capacity constraint
        def c4_vehicle_capacity(model, iVehicle):
            return (
                sum(
                    model.v01ArcInRoute[iVehicle, (iNode1, iNode2)]
                    * model.pDemand[iNode2]
                    for iNode1 in model.sNodes
                    for iNode2 in model.sNodes
                    if (iNode1, iNode2) in model.sArcs
                )
                <= model.pCapacity
            )

        # 5. Subtour elimination constraints. The number of arcs between nodes in the subset should be less than
        # the number of nodes in the subset
        def c5_subtour_elimination(model, iSubtour):
            if (
                len(model.sNodeSubset[iSubtour]) < 2
                or len(model.sNodeSubset[iSubtour]) > len(model.sNodes) - 2
            ):
                return Constraint.Skip
            return (
                sum(
                    model.v01ArcInRoute[iVehicle, (iNode1, iNode2)]
                    for iNode1 in model.sNodeSubset[iSubtour]
                    for iNode2 in model.sNodeSubset[iSubtour]
                    for iVehicle in model.sVehicles
                    if (iNode1, iNode2) in model.sArcs
                )
                <= len(model.sNodeSubset[iSubtour]) - 1
            )

        # Objective function definition
        def objective_function(model):
            return sum(
                model.pWeight[(iNode1, iNode2)]
                * model.v01ArcInRoute[iVehicle, (iNode1, iNode2)]
                for iNode1 in model.sNodes
                for iNode2 in model.sNodes
                for iVehicle in model.sVehicles
            )

        # Activate constraints
        model.c1_vehicle_exits_node = Constraint(
            model.sVehicles, model.sNodes, rule=c1_vehicle_exits_node
        )
        model.c2_every_node_entered = Constraint(
            model.sNodes, rule=c2_every_node_entered
        )
        model.c3_vehicles_exit_depot = Constraint(
            model.sVehicles, rule=c3_vehicles_exit_depot
        )
        model.c4_vehicle_capacity = Constraint(
            model.sVehicles, rule=c4_vehicle_capacity
        )
        model.c5_subtour_elimination = Constraint(
            model.sSubtours, rule=c5_subtour_elimination
        )

        # Activate objective function
        model.objective_function = Objective(rule=objective_function, sense=minimize)

        return model

    def get_nodesubset(self, solution_list):
        """
        Get node tours from solution
        :param solution_list with {"vehicle" iVehicle, "origin": iNode1, "destination": iNode1}
        for every v01ArcInRoute[iVehicle, (iNode1, iNode2)] == 1
        :return: list of tours
        """
        tours = []
        sNodes_vehicle = dict.fromkeys(
            self.instance.get_vehicles()
        )  # key: vehicles, values: list of nodes visited

        for (
            iVehicle
        ) in (
            sNodes_vehicle.keys()
        ):  # one route per vehicle. Max number of routes = number of vehicles
            sNodes_vehicle[iVehicle] = [
                j["origin"] for j in solution_list if j["vehicle"] == iVehicle
            ]
            iNode = sNodes_vehicle[iVehicle][0]
            subtour = []
            while len(sNodes_vehicle[iVehicle]) != 0:
                if iNode not in subtour:
                    subtour.append(iNode)
                if iNode not in sNodes_vehicle[iVehicle]:
                    iNode = sNodes_vehicle[iVehicle][0]
                    tours.append(subtour)
                    subtour = []
                else:
                    sNodes_vehicle[iVehicle].remove(iNode)
                    iNode = [
                        j["destination"]
                        for j in solution_list
                        if j["origin"] == iNode and j["vehicle"] == iVehicle
                    ][0]
            tours.append(subtour)

        return tours

    def update_subtours(self, tours):
        """
        Update model data sets with previous solution tours to create new constraints
        :param tours: previous solution tours
        :return:
        """

        def visit_one_depot(tour, depots):
            for i_depot in depots:
                if i_depot in tour:
                    return True
            return False

        if len(tours) == self.instance.get_num_vehicles():
            return
        subtours = [
            i_tours
            for i_tours in tours
            if not visit_one_depot(i_tours, self.instance.get_depots())
            and len(i_tours) >= 2
        ]
        for i_subtours in subtours:
            if i_subtours not in self.data["sNodeSubset"].values():
                num_subtour = len(self.data["sSubtours"]) + 1
                self.data["sSubtours"].append(num_subtour)
                self.data["sNodeSubset"][num_subtour] = i_subtours

        return

    def solve(self, options):
        """
        Solve the MIP formulation of the VRP
        :param options: configuration of solver
        :return:
        """
        SOLVER_PARAMETERS = dict(
            timeLimit=options.get("timeLimit", 360),
            abs_gap=options.get("abs_gap", 1),
            rel_gap=options.get("rel_gap", 0.01),
            solver="cbc"
        )
        SOLVER_PARAMETERS = self.get_solver_config(SOLVER_PARAMETERS)
        mip_vrp = self.get_mip_model()
        opt = SolverFactory("cbc", tee=options.get("msg", 1))
        opt.options.update(SOLVER_PARAMETERS)
        termination_condition = STATUS_NOT_SOLVED

        tours = [1] * (self.instance.get_num_vehicles() + 1)
        while len(tours) > self.instance.get_num_vehicles():
            mip_vrp_instance = mip_vrp.create_instance({None: self.data})

            result = opt.solve(mip_vrp_instance)

            status = result.solver.status
            termination_condition = PYOMO_STOP_MAPPING[result.solver.termination_condition]
            # Check status
            if status in ["error", "unknown", "warning"]:
                self.log += "Infeasible, check data \n"
                return dict(
                    status=termination_condition,
                    status_sol=SOLUTION_STATUS_INFEASIBLE
                )
            elif status == "aborted":
                if termination_condition != STATUS_TIME_LIMIT:
                    self.log += "Infeasible, check data \n"
                    return dict(
                        status=termination_condition,
                        status_sol=SOLUTION_STATUS_INFEASIBLE
                    )

            solution_list = self.get_solution_data(mip_vrp_instance)
            tours = self.get_nodesubset(solution_list)
            self.update_subtours(tours)

        # Order_routes and create Solution
        ordered_routes = self.order_routes(tours)
        self.solution = Solution(dict(routes=ordered_routes))

        self.log += "Solving complete\n"

        return dict(
            status=termination_condition,
            status_sol=SOLUTION_STATUS_FEASIBLE
        )

    def get_solution_data(self, model_instance):
        """
        Get solution list with {"vehicle" iVehicle, "origin": iNode1, "destination": iNode1}
        for every v01ArcInRoute[iVehicle, (iNode1, iNode2)] == 1
        :param model_instance: solved model instance
        :return: solution_list
        """
        solution_list = [
            dict(
                vehicle=iVehicle,
                origin=iNode1,
                destination=iNode2,
            )
            for iVehicle in model_instance.sVehicles
            for iNode1 in model_instance.sNodes
            for iNode2 in model_instance.sNodes
            if value(model_instance.v01ArcInRoute[iVehicle, (iNode1, iNode2)]) == 1
        ]
        return solution_list

    def order_routes(self, tours):
        """
        Ordered routes for every vehicle, starting and ending at a depot and visiting the nodes in order
        :param tours: solution tours
        :return: routes in order for every vehicle
        """
        vehicles = self.instance.get_vehicles()
        depots = self.instance.get_depots()
        active_tours = [
            i_tours for i_tours in tours if len(i_tours) > 1
        ]  # Eliminate routes that don't exit depots
        routes = dict.fromkeys(range(len(active_tours)))
        for (vehicle_index, i_tours) in enumerate(
            active_tours
        ):  # get the depot in the subtour and append it as origin and continue
            origin = [iDepot for iDepot in i_tours if iDepot in depots][0]
            origin_index = i_tours.index(origin)
            first_half = i_tours[origin_index:]
            second_half = i_tours[:origin_index]
            routes[vehicle_index] = first_half + second_half
            routes[vehicle_index].append(origin)  # End the route with the depot

        return routes