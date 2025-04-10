from ..core import Experiment, Solution
from ..core.const import FIRST_DAY, SECOND_DAY, DAYS
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
    PYOMO_STOP_MAPPING,
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
            "sDays": {None: DAYS},
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

        def c0_not_allowed_flows(model, origin, destination):
            """ensure that the flows not allowed in the network are equal to 0"""
            if (origin, destination) not in model.sNotAllowedFlows:
                return Constraint.Skip
            return (
                sum(
                    model.vFlow[origin, destination, product, day]
                    for product in model.sProducts
                    for day in model.sDays
                )
                == 0
            )

        def c1_1_consistency_suppliers(model, day, product):
            """the amount of doses delivered by suppliers must reach customers"""
            return (
                sum(
                    model.vFlow[supplier, warehouse, product, day]
                    for supplier in model.sL1Suppliers
                    for warehouse in model.sAllWarehouses
                )
            ) == (
                sum(
                    model.vFlow[warehouse, client, product, day]
                    for warehouse in model.sAllWarehouses
                    for client in model.sClients
                )
            )

        def c1_2_consistency_warehouses(model, warehouse, day, product):
            """the amount of doses which enter a warehouse one day
            is equal to the number of doses that are sent that same day from the warehouse
            """
            return (
                sum(
                    model.vFlow[supplier, warehouse, product, day]
                    for supplier in model.sL1Suppliers
                )
                + sum(
                    model.vFlow[warehouse_p, warehouse, product, day]
                    for warehouse_p in model.sAllWarehouses
                    if self.instance.is_lower_level(warehouse_p, warehouse)
                )
            ) == (
                sum(
                    model.vFlow[warehouse, warehouse_s, product, day]
                    for warehouse_s in model.sAllWarehouses
                    if self.instance.is_higher_level(warehouse_s, warehouse)
                )
                + sum(
                    model.vFlow[warehouse, client, product, day]
                    for client in model.sClients
                )
            )

        def c2_limit_suppliers(model, supplier, product):
            """the amount of doses delivered by a supplier cannot exceed its initial availability"""
            return (
                model.vPurchaseFromSupplier[supplier, product]
                <= model.pSupplierLimit[supplier, product]
            )

        def c3_purchases(model, supplier, product):
            """determine the amount of doses of each vaccine purchased from each supplier"""
            return (
                sum(
                    model.vFlow[supplier, warehouse, product, day]
                    for day in model.sDays
                    for warehouse in model.sAllWarehouses
                )
                + sum(
                    model.vFlow[supplier, client, product, day]
                    for day in model.sDays
                    for client in model.sClients
                )
            ) == model.vPurchaseFromSupplier[supplier, product]

        def c4_usage_warehouse(model, warehouse, day):
            """determine the usage (number of doses stored) of a warehouse per day"""
            return (
                sum(
                    model.vFlow[supplier, warehouse, product, day]
                    for supplier in model.sL1Suppliers
                    for product in model.sProducts
                )
                + sum(
                    model.vFlow[warehouse_p, warehouse, product, day]
                    for warehouse_p in model.sAllWarehouses
                    for product in model.sProducts
                    if self.instance.is_lower_level(warehouse_p, warehouse)
                )
                == model.vUsage[warehouse, day]
            )

        def c5_capacity_limit_warehouse(model, warehouse, day):
            """the amount of doses stored in a warehouse each day cannot exceed its maximum capacity"""
            return (
                model.vUsage[warehouse, day]
                <= model.pCapacity[warehouse] * model.v01IsOpen[warehouse]
            )

        # Pfizer, Moderna and AstraZeneca vaccines require two doses. If one day a locality receives
        # a certain number doses of this vaccines, the next day at least the same amount must be received

        def c6_second_doses(model, client, product):
            """guarantee the reception of the second doses"""
            if model.pNumberDoses[product] == 1:
                return Constraint.Skip
            return (
                sum(
                    model.vFlow[supplier, client, product, FIRST_DAY]
                    for supplier in model.sL1Suppliers
                )
                + sum(
                    model.vFlow[warehouse, client, product, FIRST_DAY]
                    for warehouse in model.sAllWarehouses
                )
            ) <= (
                sum(
                    model.vFlow[supplier, client, product, SECOND_DAY]
                    for supplier in model.sL1Suppliers
                )
                + sum(
                    model.vFlow[warehouse, client, product, SECOND_DAY]
                    for warehouse in model.sAllWarehouses
                )
            )

        # The demand of every client must be satisfied
        def c7_satisfy_demand(model, client):
            """two doses of Pfizer, Moderna and AstraZeneca and one dose of Janssen
            per person are required to meet demand"""
            return model.pClientDemand[client] <= (
                sum(
                    model.vFlow[supplier, client, product, day]
                    / model.pNumberDoses[product]
                    for supplier in model.sL1Suppliers
                    for day in model.sDays
                    for product in model.sProducts
                )
                + sum(
                    model.vFlow[warehouse, client, product, day]
                    / model.pNumberDoses[product]
                    for warehouse in model.sAllWarehouses
                    for day in model.sDays
                    for product in model.sProducts
                )
            )

        def obj_expression(model):
            """minimize the total cost"""
            fixed_costs = sum(
                model.pFixedCost[warehouse] * model.v01IsOpen[warehouse]
                for warehouse in model.sAllWarehouses
            )

            variable_costs = sum(
                model.pVariableCost[warehouse] * model.vUsage[warehouse, day]
                for warehouse in model.sAllWarehouses
                for day in model.sDays
            )

            purchase_costs = sum(
                model.pUnitProductCost[product]
                * model.vPurchaseFromSupplier[supplier, product]
                for supplier in model.sL1Suppliers
                for product in model.sProducts
            )

            transport_costs = sum(
                model.pUnitFlowCost[origin, destination]
                * model.vFlow[origin, destination, product, day]
                for destination in model.sLocations
                for origin in model.sLocations
                for day in model.sDays
                for product in model.sProducts
            )

            return fixed_costs + variable_costs + purchase_costs + transport_costs

        # Active constraints
        model.c0_not_allowed_flows = Constraint(
            model.sLocations, model.sLocations, rule=c0_not_allowed_flows
        )
        model.c1_1_consistency_suppliers = Constraint(
            model.sDays, model.sProducts, rule=c1_1_consistency_suppliers
        )
        model.c1_2_consistency_warehouses = Constraint(
            model.sAllWarehouses,
            model.sDays,
            model.sProducts,
            rule=c1_2_consistency_warehouses,
        )
        model.c2_limit_suppliers = Constraint(
            model.sL1Suppliers, model.sProducts, rule=c2_limit_suppliers
        )
        model.c3_purchases = Constraint(
            model.sL1Suppliers, model.sProducts, rule=c3_purchases
        )
        model.c4_usage_warehouse = Constraint(
            model.sAllWarehouses, model.sDays, rule=c4_usage_warehouse
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
        opt.options.update(self.get_solver_config(config))
        results = opt.solve(model_instance, tee=config.get("msg", True))

        status = results.solver.status
        termination_condition = PYOMO_STOP_MAPPING[results.solver.termination_condition]

        # Check status
        if status in ["error", "unknown", "warning"]:
            self.log += "Infeasible, check data \n"
            return dict(
                status=termination_condition, status_sol=SOLUTION_STATUS_INFEASIBLE
            )
        elif status == "aborted":
            self.log += "Aborted \n"
            if termination_condition != STATUS_TIME_LIMIT:
                return dict(
                    status=termination_condition, status_sol=SOLUTION_STATUS_INFEASIBLE
                )

        solution_dict = dict()
        solution_dict["flows"] = [
            dict(
                origin=origin,
                destination=destination,
                product=product,
                day=day,
                flow=value(model_instance.vFlow[origin, destination, product, day]),
            )
            for origin in model_instance.sLocations
            for destination in model_instance.sLocations
            for product in model_instance.sProducts
            for day in model_instance.sDays
            if value(model_instance.vFlow[origin, destination, product, day]) > 0
        ]

        self.solution = Solution.from_dict(solution_dict)

        self.log += "Solving complete\n"

        return dict(status=termination_condition, status_sol=SOLUTION_STATUS_FEASIBLE)
