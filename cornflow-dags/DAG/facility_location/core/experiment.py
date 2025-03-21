from cornflow_client.core.tools import load_json
from cornflow_client import ExperimentCore
from .instance import Instance
from .solution import Solution
from pytups import SuperDict, TupList
import os


class Experiment(ExperimentCore):
    schema_checks = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/solution_checks.json")
    )

    def __init__(self, instance, solution):
        if solution is None:
            solution = Solution(SuperDict(flows=SuperDict()))
        super().__init__(instance, solution)

    @property
    def instance(self) -> Instance:
        return super().instance

    @property
    def solution(self) -> Solution:
        return super().solution

    @solution.setter
    def solution(self, value):
        self._solution = value

    def check_availability(self):
        """Checks that the supplier don't supply more product than what they theoretically have"""
        availability_dict = self.instance.get_availability()
        purchases_dict = self.solution.get_amount_supplied().kfilter(
            lambda k: k[0] in self.instance.get_suppliers()
        )
        checks = TupList(
            [
                {
                    "id_supplier": k[0],
                    "id_product": k[1],
                    "quantity": availability_dict[k] - purchases_dict[k],
                }
                for k in availability_dict
            ]
        )
        return checks.vfilter(lambda v: v["quantity"] < 0)

    def check_demand(self):
        """Checks that the demand is covered"""
        demand = self.instance.get_demand()
        first_dose_received = (
            TupList(self.solution.data["flows"])
            .take(["destination", "product", "flow"])
            .to_dict(result_col=2, is_list=True)
            .vapply(lambda v: sum(v))
            .to_dictdict()
            .vapply(
                lambda v: sum(
                    v.kvapply(
                        lambda k, vv: vv / self.instance.get_nb_doses()[k]
                    ).values()
                )
            )
        )

        return (
            demand.kvapply(lambda k, v: first_dose_received[k] - v)
            .vfilter(lambda v: v < 0)
            .to_tuplist()
            .vapply(lambda v: {"id_client": v[0], "missing_first_doses": v[1]})
        )

    def check_second_dose(self):
        """Checks that every patient that receives a first dose also received a second dose"""
        nb_doses = self.instance.get_nb_doses()
        clients = self.instance.get_clients()
        first_doses = (
            TupList(self.solution.data["flows"])
            .vfilter(
                lambda v: v["day"] == "Day 1"
                and v["destination"] in clients
                and nb_doses[v["product"]] > 1
            )
            .take(["destination", "product", "flow"])
            .to_dict(result_col=2, is_list=True)
            .vapply(lambda v: sum(v))
        )
        second_doses = (
            TupList(self.solution.data["flows"])
            .vfilter(
                lambda v: v["day"] == "Day 2"
                and v["destination"] in clients
                and nb_doses[v["product"]] > 1
            )
            .take(["destination", "product", "flow"])
            .to_dict(result_col=2, is_list=True)
            .vapply(lambda v: sum(v))
        )
        return (
            second_doses.kvapply(lambda k, v: v - first_doses.get(k, 0))
            .kvfilter(lambda k, v: v < 0)
            .to_tuplist()
            .vapply(
                lambda v: {
                    "id_client": v[0],
                    "id_product": v[1],
                    "missing_second_doses": v[2],
                }
            )
        )

    def check_restricted_flows(self):
        """Checks that no product is transported between pairs of nodes where it is not allowed"""
        restricted_flows = self.instance.get_restricted_flows()
        return (
            TupList(self.solution.data["flows"])
            .vfilter(lambda v: (v["origin"], v["destination"]) in restricted_flows)
            .take(["origin", "destination", "flow"])
            .to_dict(result_col=2, is_list=True)
            .vapply(lambda v: sum(v))
            .to_tuplist()
            .vapply(lambda v: {"origin": v[0], "destination": v[1], "total_flow": v[2]})
        )

    def check_warehouse_capacity(self):
        """Checks that the quantity of product stored in the warehouses never exceeds their capacities"""
        warehouses = self.instance.get_warehouses()
        capacities = self.instance.get_capacity()
        return (
            TupList(self.solution.data["flows"])
            .vfilter(lambda v: v["destination"] in warehouses)
            .take(["destination", "day", "flow"])
            .to_dict(result_col=2, is_list=True)
            .vapply(lambda v: sum(v))
            .kvapply(lambda k, v: v - capacities[k[0]])
            .vfilter(lambda v: v > 0)
            .to_tuplist()
            .vapply(
                lambda v: {"id_warehouse": v[0], "day": v[1], "excess_quantity": v[2]}
            )
        )

    def check_consistency_warehouses(self):
        """Checks that everything that arrives into a warehouse also leaves the warehouse"""
        warehouses = self.instance.get_warehouses()
        flows = TupList(self.solution.data["flows"])
        flow_in = (
            flows.vfilter(lambda v: v["destination"] in warehouses)
            .take(["destination", "day", "product", "flow"])
            .to_dict(result_col=3, is_list=True)
            .vapply(lambda v: sum(v))
        )
        flow_out = (
            flows.vfilter(lambda v: v["origin"] in warehouses)
            .take(["origin", "day", "product", "flow"])
            .to_dict(result_col=3, is_list=True)
            .vapply(lambda v: sum(v))
        )
        return (
            flow_out.kvapply(lambda k, v: v - flow_in.get(k, 0))
            .update(flow_in.kvapply(lambda k, v: flow_out.get(k, 0) - v))
            .vfilter(lambda v: v != 0)
            .to_tuplist()
            .vapply(
                lambda v: {
                    "id_warehouse": v[0],
                    "day": v[1],
                    "id_product": v[2],
                    "difference_flow": v[3],
                }
            )
        )

    def check_consistency_suppliers(self):
        """
        Checks that the quantity supplied by all the suppliers is
        equal to the quantity received by all the clients
        """
        suppliers = self.instance.get_suppliers()
        clients = self.instance.get_clients()
        flows = TupList(self.solution.data["flows"])
        sent = (
            flows.vfilter(lambda v: v["origin"] in suppliers)
            .take(["day", "product", "flow"])
            .to_dict(result_col=2, is_list=True)
            .vapply(lambda v: sum(v))
        )
        received = (
            flows.vfilter(lambda v: v["destination"] in clients)
            .take(["day", "product", "flow"])
            .to_dict(result_col=2, is_list=True)
            .vapply(lambda v: sum(v))
        )
        return (
            received.kvapply(lambda k, v: v - sent.get(k, 0))
            .update(sent.kvapply(lambda k, v: received.get(k, 0) - v))
            .vfilter(lambda v: v != 0)
            .to_tuplist()
            .vapply(
                lambda v: {"day": v[0], "id_product": v[1], "difference_flow": v[2]}
            )
        )

    def get_objective(self):
        flows_sol = self.solution.get_pair_of_nodes_flows()
        transport_costs_dict = self.instance.get_unit_flow_cost()
        fixed_costs_dict = self.instance.get_fixed_cost()
        variable_cost_dict = self.instance.get_variable_cost()
        unit_cost_dict = self.instance.get_unit_cost()
        warehouses = self.instance.get_warehouses()

        used_warehouses = self.solution.get_used_nodes().vfilter(
            lambda v: v in warehouses
        )

        variable_cost = sum(
            variable_cost_dict[origin] * v
            for (origin, product), v in self.solution.get_amount_supplied().items()
            if origin in used_warehouses
        )

        fixed_cost = sum(fixed_costs_dict[w] for w in used_warehouses)

        purchases_cost = sum(
            unit_cost_dict[product] * v
            for (origin, product), v in self.solution.get_amount_supplied().items()
            if origin in self.instance.get_suppliers()
        )

        transport_cost = sum(flows_sol[i] * transport_costs_dict[i] for i in flows_sol)

        return variable_cost + fixed_cost + purchases_cost + transport_cost

    def solve(self, options: dict) -> dict:
        raise NotImplementedError()
