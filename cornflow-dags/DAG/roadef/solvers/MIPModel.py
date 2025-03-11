from ..core import Experiment, Solution
from .RoutesGenerator import RoutesGenerator
from math import floor
from datetime import datetime
from collections import OrderedDict
import pulp as pl
import pickle
import json
from pytups import SuperDict, TupList
import itertools
from cornflow_client.constants import (
    STATUS_FEASIBLE,
    SOLUTION_STATUS_FEASIBLE
)


class MIPModel(Experiment):
    def __init__(self, instance, solution=None):
        super().__init__(instance, solution)
        self.log = ""
        self.solver = "MIP Model"
        self.routes_generator = RoutesGenerator(self.instance)
        self.range_hours = list(range(self.horizon))
        self.routes = dict()
        self.unused_routes = dict()
        self.value_greedy = None
        self.interval_routes = 6
        self.nb_routes = 1000
        self.start_time = datetime.now()
        self.start_time_string = datetime.now().strftime("%d.%m-%Hh%M")
        self.print_log = False
        self.save_results = False
        self.artificial_quantities = dict()
        self.limit_artificial_round = 0
        self.last_solution_round = -1
        self.solution_greedy = None
        self.locations_in = dict()
        self.unique_locations_in = dict()
        self.hour_of_visit = dict()
        self.k_visit_hour = dict()
        self.nb_visits = dict()
        self.coef_inventory_conservation = 0.8
        self.time_limit = 100000

        # Variables
        self.route_var = SuperDict()
        self.artificial_quantities_var = SuperDict()
        self.artificial_binary_var = SuperDict()
        self.inventory_var = SuperDict()
        self.quantity_var = SuperDict()
        self.trailer_quantity_var = SuperDict()

    @staticmethod
    def get_solver(config):
        solver_name = config.pop("solver")
        if "." in solver_name:
            return solver_name.split(".")[1]
        return "CPLEX_PY"

    def solve(self, config=None):
        self.start_time = datetime.now()
        self.start_time_string = datetime.now().strftime("%d.%m-%Hh%M")

        if config is None:
            config = dict()
        config = dict(config)

        self.time_limit = config.get("timeLimit", 100000)
        self.coef_inventory_conservation = config.get(
            "inventoryConservation", self.coef_inventory_conservation
        )

        self.print_in_console("Started at: ", self.start_time_string)

        self.nb_routes = config.get("nb_routes_per_run", self.nb_routes)

        self.routes = self.generate_initial_routes()
        previous_value = self.value_greedy

        self.unused_routes = pickle.loads(pickle.dumps(self.routes, -1))
        used_routes = dict()
        current_round = 0

        self.print_in_console("=================== ROUND 0 ========================")
        self.print_in_console(
            "Initial empty solving at: ", datetime.now().strftime("%H:%M:%S")
        )
        solver_name = self.get_solver(config)
        config_first = dict(
            solver=solver_name,
            rel_gap=0.1,
            timeLimit=min(200.0, self._get_remaining_time()),
            msg=self.print_log,
        )
        config_first = self.get_solver_config(config_first, lib="pulp")

        def config_iteration(self, warm_start):
            conf = dict(
                solver=solver_name,
                rel_gap=0.05,
                timeLimit=min(100.0, self._get_remaining_time()),
                msg=self.print_log,
                warmStart=warm_start,
            )
            return self.get_solver_config(conf, lib="pulp")

        solver = pl.getSolver(solver=solver_name, **config_first)
        used_routes, previous_value = self.solve_one_iteration(
            solver, used_routes, previous_value, current_round
        )
        current_round += 1
        while len(self.unused_routes) != 0 and self._get_remaining_time() > 0:
            self.print_in_console(
                f"=================== ROUND {current_round} ========================"
            )
            solver = pl.getSolver(solver=solver_name, **config_iteration(self, current_round != 1))

            used_routes, previous_value = self.solve_one_iteration(
                solver, used_routes, previous_value, current_round
            )
            current_round += 1

        self.set_final_id_shifts()
        self.post_process()

        self.print_in_console(used_routes)

        if self.save_results:
            with open(
                f"res/solution-schema-{self.start_time_string}-final.json", "w"
            ) as fd:
                json.dump(self.solution.to_dict(), fd)

        return dict(
            status=STATUS_FEASIBLE,
            status_sol=SOLUTION_STATUS_FEASIBLE
        )

    def solve_one_iteration(self, solver, used_routes, previous_value, current_round):
        if 0 < current_round <= self.limit_artificial_round + 1:
            self.generate_new_routes()
            self.artificial_quantities = dict()

        old_used_routes = pickle.loads(pickle.dumps(used_routes, -1))
        previous_routes_infos = [
            (shift["id_shift"], shift["trailer"], shift["driver"])
            for shift in self.solution.get_all_shifts()
        ]

        if current_round > 0:
            selected_routes = self.select_routes(self.nb_routes)
            used_routes = SuperDict({**used_routes, **selected_routes})
            self.initialize_parameters(used_routes)

        model = self.new_model(
            used_routes,
            previous_routes_infos,
            current_round <= self.limit_artificial_round,
        )
        status = model.solve(solver=solver)

        if status == 1:
            self.to_solution(model, used_routes, current_round)
            if current_round > self.limit_artificial_round:
                self.checkpoint_and_save(current_round)

        if status != 1 or current_round == 0:
            used_routes = old_used_routes
            return used_routes, None

        if not (
            previous_value is None
            or pl.value(model.objective) < previous_value
            or (
                (current_round > self.limit_artificial_round)
                and (self.last_solution_round <= self.limit_artificial_round)
            )
        ):
            return old_used_routes, previous_value

        keep = (
            self.route_var.vfilter(lambda v: pl.value(v) > 0.5)
            .keys_tl()
            .take(0)
            .to_dict(None)
            .vapply(lambda v: True)
        )

        used_routes = {
            r: route for r, route in used_routes.items() if keep.get(r, False)
        }

        if current_round > self.limit_artificial_round:
            previous_value = pl.value(model.objective)
        self.last_solution_round = current_round
        return used_routes, previous_value

    def _get_remaining_time(self) -> float:
        return self.time_limit - (datetime.now() - self.start_time).total_seconds()

    def generate_initial_routes(self):
        """
        Generates shifts from initial methods
        The generated shifts already have a departure time and respect the duration constraint
        :return: A dictionary whose keys are the indices of the shifts and whose values are instances of RouteLabel
        """
        # 'shortestRoutes', 'FromForecast', 'RST'
        (
            routes,
            nb_greedy,
            self.value_greedy,
            self.solution_greedy,
        ) = self.routes_generator.generate_initial_routes(
            methods=["FromClusters"], unique=True, nb_random=0
        )
        self.print_in_console("Value greedy: ", self.value_greedy)

        partial_interval_routes = self.interval_routes
        while nb_greedy * (self.horizon // partial_interval_routes) > 400:
            partial_interval_routes = 2 * partial_interval_routes

        routes = [
            route.copy().get_label_with_start(start)
            for offset in range(0, partial_interval_routes, self.interval_routes)
            for route in routes
            for start in range(offset, self.horizon, partial_interval_routes)
            if start + MIPModel.duration_route(route) < self.horizon
        ]

        self.nb_routes = max(
            self.nb_routes, nb_greedy * (self.horizon // partial_interval_routes)
        )
        self.print_in_console(f"Nb routes from initial generation: {len(routes)}")
        self.print_in_console(f"Nb routes per run: {self.nb_routes}")

        return dict(enumerate(routes))

    def generate_new_routes(self):
        """
        Generates new shifts based on the values of the artificial variables , i.e. based on the ideal deliveries
        :return: A dictionary whose keys are the indices of the shifts and whose values are instances of RouteLabel
        """
        self.print_in_console(
            "Generating new routes at: ", datetime.now().strftime("%H:%M:%S")
        )

        new_routes = self.routes_generator.generate_new_routes(
            self.artificial_quantities, make_clusters=False
        )

        new_routes = [
            route
            for route in new_routes
            if route.start + MIPModel.duration_route(route) <= self.horizon
        ]

        enumerated_new_routes = list(enumerate(new_routes, max(self.routes.keys()) + 1))

        self.print_in_console(f"Generated {len(enumerated_new_routes)} new routes")

        self.routes = OrderedDict(enumerated_new_routes + list(self.routes.items()))
        self.unused_routes = OrderedDict(
            enumerated_new_routes + list(self.unused_routes.items())
        )

    def new_model(self, used_routes, previous_routes_infos, artificial_variables):
        self.print_in_console(
            "Generating new model at: ", datetime.now().strftime("%H:%M:%S")
        )
        model = pl.LpProblem("Roadef", pl.LpMinimize)
        self.create_variables(used_routes, artificial_variables)
        self.warm_start_variables(previous_routes_infos)
        model = self.create_constraints(model, used_routes, artificial_variables)
        return model

    def warm_start_variables(self, previous_routes_infos):
        previous_routes_infos_s = set(previous_routes_infos)
        for k, v in self.route_var.items():
            v.setInitialValue(k in previous_routes_infos_s)

    def create_variables(self, used_routes, artificial_variables=False):
        # Indices
        ind_td_routes = self.get_td_routes(used_routes)
        ind_customers_hours = self.get_customers_hours()

        # Variables : route
        self.route_var = pl.LpVariable.dicts("route", ind_td_routes, 0, 1, pl.LpBinary)
        self.route_var = SuperDict(self.route_var)

        self.print_in_console("Var 'route'")

        # Variables : Artificial Quantity
        if artificial_variables:
            self.artificial_quantities_var = pl.LpVariable.dicts(
                "ArtificialQuantity", ind_customers_hours, None, 0
            )
            self.artificial_binary_var = pl.LpVariable.dicts(
                "ArtificialBinary", ind_customers_hours, 0, 1, pl.LpBinary
            )
        else:
            self.artificial_quantities_var = {}
            self.artificial_binary_var = {}

        self.artificial_quantities_var = SuperDict(self.artificial_quantities_var)
        self.artificial_binary_var = SuperDict(self.artificial_binary_var)

        self.print_in_console("Var 'ArtificialQuantity'")

        # Variables : Inventory
        _capacity = lambda i: self.instance.get_customer_property(i, "Capacity")
        self.inventory_var = {
            (i, h): pl.LpVariable(f"Inventory{i, h}", 0, _capacity(i))
            for (i, h) in self.get_var_inventory_domain()
        }
        self.inventory_var = SuperDict(self.inventory_var)
        self.print_in_console("Var 'inventory'")

        # Variables : quantity
        for (r, i, tr, k) in self.get_var_quantity_s_domain(used_routes):
            self.quantity_var[i, r, tr, k] = pl.LpVariable(
                f"quantity{i, r, tr, k}", lowBound=0
            )

        for (r, i, tr, k) in self.get_var_quantity_p_domain(used_routes):
            self.quantity_var[i, r, tr, k] = pl.LpVariable(
                f"quantity{i, r, tr, k}", upBound=0
            )
        self.print_in_console("Var 'quantity'")

        # Variables : TrailerQuantity
        _capacity = lambda tr: self.instance.get_trailer_property(tr, "Capacity")
        self.trailer_quantity_var = {
            (tr, h): pl.LpVariable(
                f"TrailerQuantity{tr, h}",
                lowBound=0,
                upBound=_capacity(tr),
            )
            for (tr, h) in self.get_var_trailer_quantity_domain()
        }
        self.trailer_quantity_var = SuperDict(self.trailer_quantity_var)
        self.print_in_console("Var 'TrailerQuantity'")

    def create_constraints(self, model, used_routes, artificial_variables):
        # Indices
        ind_td_routes = TupList(self.get_td_routes(used_routes))
        ind_td_routes_r = ind_td_routes.to_dict(result_col=[1, 2])
        ind_customers_hours = self.get_customers_hours()
        _sum_c7_c12_domain = {
            i: self.get_sum_c7_c12_domain(used_routes, i)
            for i in self.instance.get_id_customers()
        }

        # Constraints (1), (2) - Minimize the total cost
        costs = ind_td_routes.to_dict(None).vapply(lambda v: self.cost(*v))
        objective = pl.lpSum(self.route_var * costs)
        if artificial_variables:
            objective += pl.lpSum(2000 * self.artificial_binary_var.values_tl())
        model += objective, "Objective"
        self.print_in_console("Added (Objective) - w/o art. vars.")

        # Constraints : (3) - A shift is only realized by one driver with one driver
        for r, tr_dr in ind_td_routes_r.items():
            model += (
                pl.lpSum(self.route_var[r, tr, dr] for tr, dr in tr_dr) <= 1,
                f"C3_r{r}",
            )
        self.print_in_console("Added (3)")

        # Constraints : (7) - Conservation of the inventory
        for (i, h) in ind_customers_hours:
            artificial_var = 0
            if artificial_variables:
                artificial_var = self.artificial_quantities_var[i, h]
            model += (
                -self.inventory_var[i, h]
                + self.inventory_var[i, h - 1]
                - pl.lpSum(
                    self.quantity_var[i, r, tr, k] * self.k_visit_hour[i, h, r, k]
                    for (r, tr, k) in _sum_c7_c12_domain[i]
                )
                - artificial_var
                - self.instance.get_customer_property(i, "Forecast")[h]
                == 0
            ), f"C7_i{i}_h{h}"

        for i in self.all_customers:
            initial_tank = self.instance.get_customer_property(i, "InitialTankQuantity")
            model += self.inventory_var[i, -1] == initial_tank, f"C7_i{i}_h-1"
        self.print_in_console("Added (7)")

        # Constraints: (A2) - The quantity delivered in an artificial delivery respects quantities constraints
        if artificial_variables:
            for (i, h) in ind_customers_hours:
                model += (
                    self.artificial_quantities_var[i, h]
                    + self.artificial_binary_var[i, h]
                    * min(
                        self.instance.get_customer_property(i, "Capacity"),
                        self.routes_generator.max_trailer_capacities,
                    )
                    >= 0
                ), f"CA2_i{i}_h{h}"
            self.print_in_console(f"Added (A2)")

        # Constraints : (9) - Conservation of the trailers' inventories
        _sum_c9_domain = self.get_sum_c9_domain(used_routes)
        for (tr, h) in self.get_c4_c9_domain():
            model += (
                pl.lpSum(
                    self.quantity_var[i, r, tr, k] * self.k_visit_hour[(i, h, r, k)]
                    for (r, i, k) in _sum_c9_domain
                )
                + self.trailer_quantity_var[tr, h - 1]
                == self.trailer_quantity_var[tr, h]
            ), f"C9_tr{tr}_h{h}"

        for tr in self.instance.get_id_trailers():
            initial_quantity = self.instance.get_trailer_property(tr, "InitialQuantity")
            model += (
                self.trailer_quantity_var[tr, -1] == initial_quantity,
                f"C9_tr{tr}_h-1",
            )
        self.print_in_console("Added (9)")

        # Constraints: (15) - Conservation of the total inventory between the beginning of the time horizon and the end
        model += (
            pl.lpSum(
                self.coef_inventory_conservation * self.inventory_var[i, -1]
                - self.inventory_var[i, self.horizon - 1]
                for i in self.instance.get_id_customers()
            )
            <= 0
        ), f"C15"
        self.print_in_console("Added (15)")

        # Constraints: (10) - Quantities delivered don't exceed trailer capacity
        _drivers = self.instance.get_id_drivers()
        for (r, i, tr, k) in self.get_c10_domain(used_routes):
            _capacity = self.instance.get_customer_property(i, "Capacity")
            model += (
                pl.lpSum(self.route_var[r, tr, dr] * _capacity for dr in _drivers)
                >= -self.quantity_var[i, r, tr, k],
                f"C10_i{i}_r{r}_tr{tr}_k{k}",
            )
        self.print_in_console("Added (10)")

        # Constraints: (11), (12)
        for (r, route, i, tr, k) in self.get_c11_c12_domain(used_routes):
            # Constraint: (11) - Quantities delivered don't exceed the quantity in the trailer
            visited = lambda j: route.visited[j][0]
            q_tup = lambda j, kp: (visited(j), r, tr, kp)
            hour_tup = lambda j, kp: (
                visited(j),
                self.hour_of_visit[i, r, k],
                r,
                kp,
            )
            visit_tup = lambda j, kp: (r, visited(j), kp, i, k)

            model += (
                pl.lpSum(
                    (
                        self.quantity_var[q_tup(j, kp)]
                        * self.k_visit_hour[hour_tup(j, kp)]
                        * self.visit_before_on_route(*visit_tup(j, kp))
                    )
                    for (j, kp) in self.get_sum_c11_c14_domain(i, r, k)
                )
                + self.quantity_var[i, r, tr, k]
                + self.trailer_quantity_var[(tr, self.hour_of_visit[i, r, k] - 1)]
                >= 0
            ), f"C11_i{i}_r{r}_tr{tr}_k{k}"

            # Constraint: (12) - Quantities delivered don't exceed available space in customer tank
            model += (
                pl.lpSum(
                    (
                        self.quantity_var[i, rp, trp, kp]
                        * self.k_visit_hour[i, self.hour_of_visit[i, r, k], rp, kp]
                        * self.visit_before(i, r, k, rp, kp),
                    )
                    for (rp, trp, kp) in _sum_c7_c12_domain[i]
                    if r != rp and tr != trp
                )
                - self.inventory_var[i, self.hour_of_visit[i, r, k] - 1]
                + self.quantity_var[i, r, tr, k]
                + self.instance.get_customer_property(i, "Capacity")
                >= 0
            ), f"C12_i{i}_r{r}_tr{tr}_k{k}"
        self.print_in_console("Added (11), (12)")

        # Constraints: (13) - Quantities loaded at a source don't exceed trailer capacity
        _drivers = self.instance.get_id_drivers()
        for (r, i, tr, k) in self.get_c13_domain(used_routes):
            _capacity = self.instance.get_trailer_property(tr, "Capacity")
            model += (
                self.quantity_var[i, r, tr, k]
                <= pl.lpSum(self.route_var[r, tr, dr] for dr in _drivers) * _capacity
            ), f"C13_i{i}_r{r}_tr{tr}_k{k}"
        self.print_in_console("Added (13)")

        # Constraints: (14) - Quantities loaded at a source don't exceed free space in the trailer
        for (r, route, i, tr, k) in self.get_c14_domain(used_routes):
            visited = lambda j: route.visited[j][0]
            q_tup = lambda j, kp: (visited(j), r, tr, kp)
            hour_tup = lambda j, kp: (
                visited(j),
                self.hour_of_visit[(i, r, k)],
                r,
                kp,
            )
            visit_tup = lambda j, kp: (r, visited(j), kp, i, k)
            model += (
                pl.lpSum(
                    (
                        self.quantity_var[q_tup(j, kp)]
                        * self.k_visit_hour[hour_tup(j, kp)]
                        * self.visit_before_on_route(*visit_tup(j, kp)),
                    )
                    for (j, kp) in self.get_sum_c11_c14_domain(i, r, k)
                )
                + self.quantity_var[i, r, tr, k]
                + self.trailer_quantity_var[(tr, self.hour_of_visit[(i, r, k)] - 1)]
                <= self.instance.get_trailer_property(tr, "Capacity")
            ), f"C14_i{i}_r{r}_tr{tr}_k{k}"
        self.print_in_console("Added (14)")

        # Constraints (4), (5) - Two shifts with same trailer can't happen at the same time
        #   and two shifts realized by the same driver must leave time for the driver to rest between both
        _sum_c4_domain = self.get_sum_c4_domain(used_routes)
        _sum_c5_domain = self.get_sum_c5_domain(used_routes)
        for (tr, h) in self.get_c4_c9_domain():
            model += (
                pl.lpSum(
                    self.route_var[r, tr, dr]
                    for r, route, dr in _sum_c4_domain
                    if self.runs_at_hour(r, h)
                )
                <= 1,
                f"C4_tr{tr}_h{h}",
            )
        self.print_in_console("Added (4)")

        for (dr, h) in self.get_c5_domain():
            model += (
                pl.lpSum(
                    self.route_var[r, tr, dr]
                    for r, route, tr in _sum_c5_domain
                    if self.blocks_driver_at_hour(r, dr, h)
                )
                <= 1,
                f"C5_dr{dr}_h{h}",
            )
        self.print_in_console("Added (5)")

        return model

    def select_routes(self, nb=500):
        """
        Selects the indicated number of shifts from self.unused_routes and deletes them from self.unused_routes
        :return: A dictionary whose keys are the indices of the shifts and whose values are instances of RouteLabel
        """
        self.print_in_console(
            "Selecting routes at: ", datetime.now().strftime("%H:%M:%S")
        )
        selected_routes = dict()
        nb = min(nb, len(self.unused_routes))

        for r in list(self.unused_routes.keys())[0:nb]:
            selected_routes[r] = self.unused_routes[r]
            del self.unused_routes[r]
        self.print_in_console(selected_routes)
        return selected_routes

    def checkpoint_and_save(self, current_round):
        """Checks the solution and, in some cases, saves the log in a file"""
        self.print_in_console(
            "Checking solution at: ", datetime.now().strftime("%H:%M:%S")
        )
        self.calculate_inventories()
        check_dict = self.check_solution()
        check_log = self.generate_log(check_dict)

        if self.save_results:
            with open(
                f"res/log-{self.start_time_string}-R{current_round}.txt", "w"
            ) as fd2:
                fd2.write(f"Objective: {self.get_objective()}\n")
                fd2.write(check_log)

        self.print_in_console(check_log)
        self.print_in_console(f"Objective: {self.get_objective()}")

    def cost(self, r, tr, dr):
        """Returns the cost of performing a shift with given trailer and given driver"""
        route = self.routes[r]
        total_time = route.visited[-1][1] - route.visited[0][1]
        time_cost = self.instance.get_driver_property(dr, "TimeCost")
        total_dist = 0

        for i in range(1, len(route.visited)):
            total_dist += self.instance.get_distance_between(
                route.visited[i - 1][0], route.visited[i][0]
            )
        dist_cost = self.instance.get_trailer_property(tr, "DistanceCost")
        return total_time * time_cost + total_dist * dist_cost

    def duration(self, r):
        """Returns the duration of the route of index r"""
        route = self.routes[r]
        return (route.visited[-1][1] - route.visited[0][1]) / 60

    @staticmethod
    def duration_route(route):
        """Returns the duration of the given route"""
        return (route.visited[-1][1] - route.visited[0][1]) / 60

    def get_nb_visits(self, i, r):
        """Returns the number of visits to location i on the route of index r"""
        return self.locations_in[r].count(i)

    def get_hour_of_visit(self, i, r, k):
        """Returns the time at which route r visits the location i for the k_th time"""
        route = self.routes[r]
        hour = None
        th = 1
        for step in route.visited:
            if step[0] == i and th == k:
                hour = step[1] / 60
            if step[0] == i:
                th += 1
        return floor(route.start + hour)

    def get_k_visit_hour(self, i, h, r, k):
        """Returns 1 if route r visits location i for the k_th time at hour h"""
        route = self.routes[r]
        th = 1
        visit = 0
        for step in route.visited:
            if step[0] == i and th == k:
                if floor(route.start + step[1] / 60) == h:
                    visit = 1
            if step[0] == i:
                th += 1
        return visit

    def initialize_parameters(self, used_routes):
        """Caches the values of some of the functions to avoid recalculating each time"""
        self.locations_in = dict(
            (r, self.get_locations_in_r(self.routes[r])) for r in used_routes
        )
        self.unique_locations_in = dict(
            (r, self.get_unique_locations_in(self.routes[r])) for r in used_routes
        )
        self.nb_visits = dict(
            ((i, r), self.get_nb_visits(i, r))
            for i in self.all_locations
            for r in used_routes
        )
        self.hour_of_visit = dict(
            ((i, r, k), self.get_hour_of_visit(i, r, k))
            for i in self.all_locations
            for r in used_routes
            for k in range(1, self.nb_visits[i, r] + 1)
        )
        self.k_visit_hour = dict(
            ((i, h, r, k), self.get_k_visit_hour(i, h, r, k))
            for i in self.all_locations
            for r in used_routes
            for h in self.range_hours
            for k in range(1, self.nb_visits[i, r] + 1)
        )

    def visit_before(self, i, r, k, rp, kp):
        """
        :return: 1 if route r visits i before rp does, 0 otherwise
        """
        h = self.hour_of_visit[i, r, k]
        hp = self.hour_of_visit[i, rp, kp]
        if h is None or hp is None:
            return 0
        elif h < hp:
            return 1
        return 0

    def visit_before_on_route(self, r, i, k, ip, kp):
        """
        :return: 1 if route r visits i before ip, 0 otherwise
        """
        h = self.hour_of_visit[i, r, k]
        hp = self.hour_of_visit[ip, r, kp]
        if h is None or hp is None:
            return 0
        elif h < hp:
            return 1
        return 0

    def runs_at_hour(self, r, h):
        """
        :return: 1 if route r is being 'executed' at hour h
        """
        route = self.routes[r]
        return floor(route.start) <= h <= route.start + self.duration(r)

    def blocks_driver_at_hour(self, r, dr, h):
        """
        :return: 1 if at hour h, the driver dr would be on route r or resting after shift r
            if he was assigned to route r
        """
        route = self.routes[r]
        return (
            floor(route.start)
            <= h
            <= (
                route.start
                + self.duration(r)
                + self.instance.get_driver_property(dr, "minInterSHIFTDURATION") / 60
            )
        )

    def k_position(self, i, r, k):
        """
        :return: the position of the k_th visit at location i on route r
        """
        route = self.routes[r]
        th = 1
        pos = None
        for j, step in enumerate(route.visited):
            if step[0] == i and th == k:
                pos = j
            if step[0] == i:
                th += 1
        return pos

    def to_solution(self, model, used_routes, current_round):
        """Converts the variables returned by the solver into an instance of Solution"""
        self.print_in_console(
            "Converting to Solution at: ", datetime.now().strftime("%H:%M:%S")
        )
        self.solution = Solution(dict())
        shifts = dict()
        self.artificial_quantities = dict()

        if self.save_results:
            with open(
                f"res/solution-{self.start_time_string}-R{current_round}.txt", "w"
            ) as fd:
                for var in model.variables():
                    fd.write(var.name + f": {var.varValue}\n")

        selected_r_tr_dr = self.route_var.vfilter(
            lambda v: round(pl.value(v), 2) == 1
        ).keys_tl()

        for (r, tr, dr) in selected_r_tr_dr:
            label = used_routes[r]
            route = [
                dict(
                    location=step[0],
                    departure=step[1] + 60 * label.start,
                    layover_before=0,
                    driving_time_before_layover=0,
                )
                for step in label.visited
            ]

            for s, step in enumerate(route):
                if self.is_customer_or_source(step["location"]):
                    route[s]["arrival"] = step[
                        "departure"
                    ] - self.instance.get_location_property(
                        step["location"], "setupTime"
                    )
                elif self.is_base(step["location"]):
                    route[s]["arrival"] = step["departure"]
                    route[s]["quantity"] = 0
            shifts[r] = dict(
                driver=dr,
                trailer=tr,
                route=route,
                id_shift=r,
                departure_time=60 * label.start,
            )
        self.artificial_quantities = dict(
            self.artificial_quantities_var.vfilter(
                lambda v: round(pl.value(v), 3) != 0
            ).vapply(lambda v: round(pl.value(v), 3))
        )
        nb_artificial_deliveries = len(self.artificial_quantities)
        self.print_in_console("Nb Artificial deliveries: ", nb_artificial_deliveries)

        delivered_quantities = self.quantity_var.vapply(lambda v: round(pl.value(v), 3))
        for (i, r, tr, k), val in delivered_quantities.items():
            if shifts.get(r, None) is None:
                continue
            if shifts[r]["trailer"] != tr:
                continue
            th = 1

            for j, step in enumerate(shifts[r]["route"]):
                if step["location"] == i and th == k:
                    shifts[r]["route"][j]["quantity"] = val
                if step["location"] == i:
                    th += 1
        trailer_quantities = self.trailer_quantity_var.vapply(
            lambda v: round(pl.value(v), 3)
        )

        for (tr, h), val in trailer_quantities.items():
            for r, route in shifts.items():
                if route["trailer"] != tr:
                    continue
                if route["departure_time"] // 60 != h + 1:
                    continue
                shifts[r]["initial_quantity"] = val

        self.solution = Solution(shifts)

    def set_final_id_shifts(self):
        """Changes the indices of all the shifts so that the indices start from 1 and count by one"""
        new_dict = dict()
        id_shift = 1
        for r, route in self.solution.get_id_and_shifts():
            new_dict[id_shift] = route
            new_dict[id_shift]["id_shift"] = id_shift
            id_shift += 1
        self.solution = Solution(new_dict)

    def post_process(self):
        """
        Removes steps from routes if the quantities delivered/loaded are 0
        """
        new_solution = dict()
        for (id_shift, shift) in self.solution.get_id_and_shifts():
            shift_copy = pickle.loads(pickle.dumps(shift, -1))
            removed = 0

            for (id_step, step) in enumerate(shift["route"]):
                new_id_step = id_step - removed
                if step["quantity"] == 0 and step["location"] != 0:
                    del shift_copy["route"][new_id_step]
                    removed += 1
            if removed == 0:
                new_solution[id_shift] = shift
                continue

            for (id_step, step) in enumerate(shift_copy["route"]):
                if step["location"] == 0:
                    continue
                time_from_last = self.instance.get_time_between(
                    shift_copy["route"][id_step - 1]["location"], step["location"]
                )
                shift_copy["route"][id_step]["arrival"] = (
                    shift_copy["route"][id_step - 1]["departure"]
                    + time_from_last
                    + (
                        self.instance.get_driver_property(
                            shift["driver"], "LayoverDuration"
                        )
                        * shift_copy["route"][id_step]["layover_before"]
                    )
                )
                shift_copy["route"][id_step]["departure"] = shift_copy["route"][
                    id_step
                ]["arrival"] + self.instance.get_location_property(
                    step["location"], "setupTime"
                )
                shift_copy["route"][id_step]["cumulated_driving_time"] = (
                    shift_copy["route"][id_step - 1]["cumulated_driving_time"]
                    + time_from_last
                )

            if len(shift_copy["route"]) > 2:
                new_solution[id_shift] = shift_copy
        self.solution = Solution(new_solution)
        self.set_final_id_shifts()
        self.calculate_inventories()

    def get_td_routes(self, used_routes):
        """Returns a list of every possible truple (index_route, index_trailer, index_driver)"""
        return list(
            itertools.product(
                used_routes,
                self.instance.get_id_trailers(),
                self.instance.get_id_drivers(),
            )
        )

    def get_customers_hours(self):
        return list(itertools.product(self.all_customers, self.range_hours))

    def get_var_inventory_domain(self):
        return [(i, h) for i in self.all_customers for h in self.range_hours + [-1]]

    def get_var_trailer_quantity_domain(self):
        return [
            (tr, h)
            for tr in self.instance.get_id_trailers()
            for h in self.range_hours + [-1]
        ]

    def get_var_quantity_s_domain(self, used_routes):
        return [
            (r, i, tr, k)
            for r in used_routes
            for i in self.all_sources
            for tr in self.instance.get_id_trailers()
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    def get_var_quantity_p_domain(self, used_routes):
        return [
            (r, i, tr, k)
            for r in used_routes
            for i in self.all_customers
            for tr in self.instance.get_id_trailers()
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    def get_sum_c4_domain(self, used_routes):
        return [
            (r, route, dr)
            for r, route in used_routes.items()
            for dr in self.instance.get_id_drivers()
        ]

    def get_sum_c5_domain(self, used_routes):
        return [
            (r, route, tr)
            for r, route in used_routes.items()
            for tr in self.instance.get_id_trailers()
        ]

    def get_sum_c9_domain(self, used_routes):
        return [
            (r, i, k)
            for r in used_routes
            for i in self.unique_locations_in[r]
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    def get_sum_c7_c12_domain(self, used_routes, i):
        return [
            (r, tr, k)
            for r in used_routes
            for tr in self.instance.get_id_trailers()
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    def get_sum_c11_c14_domain(self, i, r, k):
        return [
            (j, kp)
            for j in range(1, self.k_position(i, r, k))
            for kp in range(1, self.nb_visits[self.routes[r].visited[j][0], r] + 1)
        ]

    def get_c4_c9_domain(self):
        return [
            (tr, h) for tr in self.instance.get_id_trailers() for h in self.range_hours
        ]

    def get_c5_domain(self):
        return [
            (dr, h) for dr in self.instance.get_id_drivers() for h in self.range_hours
        ]

    def get_c10_domain(self, used_routes):
        return [
            (r, i, tr, k)
            for r in used_routes
            for i in self.all_customers
            for tr in self.instance.get_id_trailers()
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    def get_c11_c12_domain(self, used_routes):
        return [
            (r, route, i, tr, k)
            for r, route in used_routes.items()
            for i in self.unique_customers_in(route)
            for tr in self.instance.get_id_trailers()
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    def get_c13_domain(self, used_routes):
        return [
            (r, i, tr, k)
            for r in used_routes
            for i in self.instance.get_id_sources()
            for tr in self.instance.get_id_trailers()
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    def get_c14_domain(self, used_routes):
        return [
            (r, route, i, tr, k)
            for r, route in used_routes.items()
            for i in self.unique_sources_in(route)
            for tr in self.instance.get_id_trailers()
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    # Locations visited by r
    def get_locations_in_r(self, route):
        """
        :return: A list of all the sources and customers in the given route
        """
        return [step[0] for step in route.visited if not self.is_base(step[0])]

    def get_unique_locations_in(self, route):
        """
        :return: A unique list of all the sources and customers in the given route
        """
        return TupList(
            [step[0] for step in route.visited if not self.is_base(step[0])]
        ).unique()

    def unique_customers_in(self, route):
        """
        :return: A unique list of all the customers in the given route
        """
        return TupList(
            [step[0] for step in route.visited if self.is_customer(step[0])]
        ).unique()

    def unique_sources_in(self, route):
        """
        :return: A unique list of all the sources in the given route
        """
        return TupList(
            [step[0] for step in route.visited if self.is_source(step[0])]
        ).unique()

    @property
    def all_locations(self):
        """Returns the indices of all the sources and customers"""
        return list(self.instance.get_id_sources()) + list(
            self.instance.get_id_customers()
        )

    @property
    def all_customers(self):
        """Returns the indices of all the customers"""
        return list(self.instance.get_id_customers())

    @property
    def all_sources(self):
        """Returns the indices of all the sources"""
        return list(self.instance.get_id_sources())

    def print_in_console(self, *args):
        if self.print_log:
            print(*args)
