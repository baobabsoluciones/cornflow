from ..core import Experiment, Solution
from pyomo.environ import (
    AbstractModel,
    Set,
    Param,
    Var,
    Constraint,
    Objective,
    SolverFactory,
    Binary,
    NonNegativeIntegers,
    minimize,
    value,
)
from cornflow_client.constants import (
    STATUS_TIME_LIMIT,
    SOLUTION_STATUS_FEASIBLE,
    SOLUTION_STATUS_INFEASIBLE,
    PYOMO_STOP_MAPPING
)

class PyomoSolver(Experiment):
    def __init__(self, instance, solution=None):
        self.log = ""
        if solution is None:
            solution = Solution({"include": []})
        super().__init__(instance, solution)
        self.log += "Initialized\n"
        self.data = self.get_pyomo_dict_data()

    def get_pyomo_dict_data(self):
        """Creates the dictionary according to pyomo format"""
        pyomo_instance = {
            "sL1Suppliers": {None: self.instance.get_suppliers()},
            "sProducts": {None: self.instance.get_products()},
            "sClients": {None: self.instance.get_clients()},
            "sAllWarehouses": {None: self.instance.get_warehouses()},
            "sDays": {None: ["Day 1", "Day 2"]},
            "sLocations": {None: self.instance.get_all_locations()},
            "sNotAllowedFlows": {None: self.instance.get_restricted_flows()},
            "pSupplierLimit": self.instance.get_availability(),
            "pClientDemand": self.instance.get_demand(),
            "pUnitProductCost": self.instance.get_unit_cost(),
            "pNumberDoses": self.instance.get_nb_doses(),
            "pCapacity": self.instance.get_capacity(),
            "pFixedCost": self.instance.get_fixed_cost(),
            "pVariableCost": self.instance.get_variable_cost(),
            "pDistanceKm": self.instance.get_distances(),
            "pUnitFlowCost": self.instance.get_unit_flow_cost(),
        }
        return {None: pyomo_instance}

    def get_facility_location_model(self):
        """This function builds the model to solve the SC Facility Location"""

        # Create model
        model = AbstractModel()

        # Create sets
        # the days to be considered
        model.sDays = Set()
        # the products that have to be distributed
        model.sProducts = Set()
        # this set contains all the nodes
        model.sLocations = Set()
        # list of suppliers
        model.sL1Suppliers = Set()
        # list of all warehouses
        model.sAllWarehouses = Set()
        # list of clients
        model.sClients = Set()

        # Create subset
        # this subset stores the flows between nodes that are restricted in the network
        model.sNotAllowedFlows = Set(dimen=2)

        # Create parameters
        # max number of doses that can pass through a warehouse
        model.pCapacity = Param(model.sLocations, mutable=True)
        # max number of doses of each product that a supplier has available for the period
        # if one supplier does not have an specific product, it will not appear in the database and it is set as 0 by default
        model.pSupplierLimit = Param(
            model.sL1Suppliers, model.sProducts, mutable=True, default=0
        )
        # number of people who have to be vaccinated
        model.pClientDemand = Param(model.sClients, mutable=True)
        # cost of each dose
        model.pUnitProductCost = Param(model.sProducts, mutable=True)
        # number of doses required for each vaccine
        model.pNumberDoses = Param(model.sProducts, mutable=False)
        # cost of keeping a warehouse open
        model.pFixedCost = Param(model.sLocations, mutable=True)
        # cost of storing each dose in a warehouse
        model.pVariableCost = Param(model.sLocations, mutable=True)
        # matrix of distances
        # The distance from one node to that same exact node is not included due it is equal to 0 and it is set by default
        model.pDistanceKm = Param(
            model.sLocations, model.sLocations, mutable=True, default=0
        )
        # cost of transporting each dose between two nodes (proportional to the distance)
        model.pUnitFlowCost = Param(
            model.sLocations, model.sLocations, mutable=True, default=0
        )

        # Create variables
        # whether the warehouse remains open or not
        model.v01IsOpen = Var(model.sLocations, domain=Binary)
        # number of doses that go through a warehouse each day
        model.vUsage = Var(model.sLocations, model.sDays, domain=NonNegativeIntegers)
        # number of doses of each product transported between nodes in a certain day
        model.vFlow = Var(
            model.sLocations,
            model.sLocations,
            model.sProducts,
            model.sDays,
            domain=NonNegativeIntegers,
            initialize=0,
        )
        # the total amount of doses of each vaccine bought from a supplier
        model.vPurchaseFromSupplier = Var(
            model.sL1Suppliers, model.sProducts, domain=NonNegativeIntegers
        )

        # Create constraints

        def c0_not_allowed_flows(model, iOrigin, iDestination):
            """ensure that the flows not allowed in the network are equal to 0"""
            if (iOrigin, iDestination) not in model.sNotAllowedFlows:
                return Constraint.Skip
            return (
                sum(
                    model.vFlow[iOrigin, iDestination, iProduct, iDay]
                    for iProduct in model.sProducts
                    for iDay in model.sDays
                )
                == 0
            )

        def c1_1_consistency_Suppliers(model, iDay, iProduct):
            """the amount of doses delivered by suppliers must reach customers"""
            return (
                sum(
                    model.vFlow[iSupplier, iW, iProduct, iDay]
                    for iSupplier in model.sL1Suppliers
                    for iW in model.sAllWarehouses
                )
            ) == (
                sum(
                    model.vFlow[iW, iClient, iProduct, iDay]
                    for iW in model.sAllWarehouses
                    for iClient in model.sClients
                )
            )

        def c1_2_consistency_Warehouses(model, iW, iDay, iProduct):
            """the amount of doses which enter a warehouse one day
            is equal to the number of doses that are sent that same day from the warehouse"""
            return (
                sum(
                    model.vFlow[iSupplier, iW, iProduct, iDay]
                    for iSupplier in model.sL1Suppliers
                ) + sum(
                    model.vFlow[iWLp, iW, iProduct, iDay]
                    for iWLp in model.sAllWarehouses
                    if self.instance.is_lower_level(iWLp, iW)
                )
            ) == (
                sum(
                    model.vFlow[iW, iWLs, iProduct, iDay]
                    for iWLs in model.sAllWarehouses
                    if self.instance.is_higher_level(iWLs, iW)
                ) + sum(
                    model.vFlow[iW, iClient, iProduct, iDay]
                    for iClient in model.sClients
                )
            )

        def c2_limit_suppliers(model, iSupplier, iProduct):
            """the amount of doses delivered by a supplier cannot exceed its initial availability"""
            return (
                model.vPurchaseFromSupplier[iSupplier, iProduct]
                <= model.pSupplierLimit[iSupplier, iProduct]
            )

        def c3_purchases(model, iSupplier, iProduct):
            """determine the amount of doses of each vaccine purchased from each supplier"""
            return (
                sum(
                    model.vFlow[iSupplier, iW, iProduct, iDay]
                    for iDay in model.sDays
                    for iW in model.sAllWarehouses
                )
                + sum(
                    model.vFlow[iSupplier, iClient, iProduct, iDay]
                    for iDay in model.sDays
                    for iClient in model.sClients
                )
            ) == model.vPurchaseFromSupplier[iSupplier, iProduct]

        def c4_usage_W(model, iW, iDay):
            """determine the usage (number of doses stored) of a warehouse per day"""
            return (
                sum(
                    model.vFlow[iSupplier, iW, iProduct, iDay]
                    for iSupplier in model.sL1Suppliers
                    for iProduct in model.sProducts
                ) + sum(
                    model.vFlow[iWp, iW, iProduct, iDay]
                    for iWp in model.sAllWarehouses
                    for iProduct in model.sProducts
                    if self.instance.is_lower_level(iWp, iW)
                )
                == model.vUsage[iW, iDay]
            )

        def c5_capacity_limit_warehouse(model, iW, iDay):
            """the amount of doses stored in a warehouse each day cannot exceed its maximum capacity"""
            return model.vUsage[iW, iDay] <= model.pCapacity[iW] * model.v01IsOpen[iW]

        # Pfizer, Moderna and AstraZeneca vaccines require two doses. If one day a locality receives
        # a certain number doses of this vaccines, the next day at least the same amount must be received

        def c6_second_doses(model, iClient, iProduct):
            """guarantee the reception of the second doses"""
            if model.pNumberDoses[iProduct] == 1:
                return Constraint.Skip
            return (
                sum(
                    model.vFlow[iSupplier, iClient, iProduct, "Day 1"]
                    for iSupplier in model.sL1Suppliers
                )
                + sum(
                    model.vFlow[iW, iClient, iProduct, "Day 1"]
                    for iW in model.sAllWarehouses
                )
            ) <= (
                sum(
                    model.vFlow[iSupplier, iClient, iProduct, "Day 2"]
                    for iSupplier in model.sL1Suppliers
                )
                + sum(
                    model.vFlow[iW, iClient, iProduct, "Day 2"]
                    for iW in model.sAllWarehouses
                )
            )

        # The demand of every client must be satisfied
        def c7_satisfy_demand(model, iClient):
            """two doses of Pfizer, Moderna and AstraZeneca and one dose of Janssen
            per person are required to meet demand"""
            return model.pClientDemand[iClient] <= (
                sum(
                    model.vFlow[iSupplier, iClient, iProduct, iDay]
                    / model.pNumberDoses[iProduct]
                    for iSupplier in model.sL1Suppliers
                    for iDay in model.sDays
                    for iProduct in model.sProducts
                )
                + sum(
                    model.vFlow[iW, iClient, iProduct, iDay]
                    / model.pNumberDoses[iProduct]
                    for iW in model.sAllWarehouses
                    for iDay in model.sDays
                    for iProduct in model.sProducts
                )
            )

        def obj_expression(model):
            """minimize the total cost"""
            fixed_costs = sum(
                model.pFixedCost[iW] * model.v01IsOpen[iW]
                for iW in model.sAllWarehouses
            )

            variable_costs = sum(
                model.pVariableCost[iW] * model.vUsage[iW, iDay]
                for iW in model.sAllWarehouses
                for iDay in model.sDays
            )

            purchase_costs = sum(
                model.pUnitProductCost[iProduct]
                * model.vPurchaseFromSupplier[iSupplier, iProduct]
                for iSupplier in model.sL1Suppliers
                for iProduct in model.sProducts
            )

            transport_costs = sum(
                model.pUnitFlowCost[iOrigin, iDestination]
                * model.vFlow[iOrigin, iDestination, iProduct, iDay]
                for iDestination in model.sLocations
                for iOrigin in model.sLocations
                for iDay in model.sDays
                for iProduct in model.sProducts
            )

            return fixed_costs + variable_costs + purchase_costs + transport_costs

        # Active constraints
        model.c0_not_allowed_flows = Constraint(
            model.sLocations, model.sLocations, rule=c0_not_allowed_flows
        )
        model.c1_1_consistency_Suppliers = Constraint(
            model.sDays, model.sProducts, rule=c1_1_consistency_Suppliers
        )
        model.c1_2_consistency_Warehouses = Constraint(
            model.sAllWarehouses, model.sDays, model.sProducts, rule=c1_2_consistency_Warehouses
        )
        model.c2_limit_suppliers = Constraint(
            model.sL1Suppliers, model.sProducts, rule=c2_limit_suppliers
        )
        model.c3_purchases = Constraint(
            model.sL1Suppliers, model.sProducts, rule=c3_purchases
        )
        model.c4_usage_W = Constraint(
            model.sAllWarehouses, model.sDays, rule=c4_usage_W
        )
        model.c5_capacity_limit_warehouse = Constraint(
            model.sAllWarehouses, model.sDays, rule=c5_capacity_limit_warehouse
        )
        model.c6_1_second_doses = Constraint(
            model.sClients, model.sProducts, rule=c6_second_doses
        )
        model.c7_satisfy_demand = Constraint(model.sClients, rule=c7_satisfy_demand)

        # Add objective function
        model.f_obj = Objective(rule=obj_expression, sense=minimize)

        return model

    def solve(self, config):
        data = self.data
        model = self.get_facility_location_model()
        model_instance = model.create_instance(data)

        solver_name = config.get("solver", "cbc")
        if "." in solver_name:
            _, solver_name = solver_name.split(".")

        opt = SolverFactory(solver_name)
        opt.options.update(config)
        results = opt.solve(model_instance)

        status = results.solver.status
        termination_condition = PYOMO_STOP_MAPPING[results.solver.termination_condition]

        # Check status
        if status in ["error", "unknown", "warning"]:
            self.log += "Infeasible, check data \n"
            return dict(status=termination_condition, status_sol=SOLUTION_STATUS_INFEASIBLE)
        elif status == "aborted":
            self.log += "Aborted \n"
            if termination_condition != STATUS_TIME_LIMIT:
                return dict(status=termination_condition, status_sol=SOLUTION_STATUS_INFEASIBLE)
            else:
                pass

        solution_dict = dict()
        solution_dict["flows"] = [
            dict(
                origin=o,
                destination=d,
                product=p,
                day=day,
                flow=value(model_instance.vFlow[o, d, p, day]),
            )
            for o in model_instance.sLocations
            for d in model_instance.sLocations
            for p in model_instance.sProducts
            for day in model_instance.sDays
            if value(model_instance.vFlow[o, d, p, day]) > 0
        ]

        self.solution = Solution.from_dict(solution_dict)

        self.log += "Solving complete\n"

        return dict(status=termination_condition, status_sol=SOLUTION_STATUS_FEASIBLE)
