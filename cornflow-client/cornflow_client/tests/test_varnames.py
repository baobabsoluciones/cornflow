import unittest
import pulp
from cornflow_client import group_variables_by_name


class VarsGroup(unittest.TestCase):

    # TODO: something should be asserted
    def test_export_pb_vars_1(self):
        prob = pulp.LpProblem("test_export_pb_vars_1", pulp.LpMaximize)
        x = pulp.LpVariable("x", 0, 4)
        y = pulp.LpVariable("y", -1, 1)
        z = pulp.LpVariable("z", 0)
        w = pulp.LpVariable("w", 0)
        prob += x + 4 * y + 9 * z, "obj"
        prob += x + y <= 5, "c1"
        prob += x + z >= 10, "c2"
        prob += -y + z == 7, "c3"
        prob += w >= 0, "c4"
        data = prob.to_dict()
        var1, prob1 = pulp.LpProblem.from_dict(data)
        group_variables_by_name(var1, ["x", "y", "z", "w"])
        x, y, z, w = [var1[name] for name in ["x", "y", "z", "w"]]

    # TODO: something should be asserted
    def test_export_pb_vars_2(self):
        prob = pulp.LpProblem("test_export_pb_vars_2", pulp.LpMaximize)
        x = pulp.LpVariable("decision_x", 0, 4)
        y = pulp.LpVariable("decision_y", -1, 1)
        z = pulp.LpVariable("decision_z", 0)
        w = pulp.LpVariable("decision_special_w", 0)
        prob += x + 4 * y + 9 * z, "obj"
        prob += x + y <= 5, "c1"
        prob += x + z >= 10, "c2"
        prob += -y + z == 7, "c3"
        prob += w >= 0, "c4"
        data = prob.to_dict()
        var1, prob1 = pulp.LpProblem.from_dict(data)
        grouped_dict = group_variables_by_name(var1, ["decision_special", "decision"])
        x, y, z = [grouped_dict["decision"][name] for name in ["x", "y", "z"]]
        w = grouped_dict["decision_special"]["w"]

    def test_read_vars_stringTuples(self):
        plants = ["San_Francisco", "Los_Angeles", "Phoenix", "Denver"]
        stores = ["San_Diego", "Barstow", "Tucson", "Dallas"]

        plant_store = [(p, s) for p in plants for s in stores]
        # Creates the problem variables of the Flow on the Arcs
        flow = pulp.LpVariable.dicts("Route", plant_store, 0, None, pulp.LpInteger)
        _flow = {v.name: v for v in flow.values()}
        a = group_variables_by_name(_flow, ["Route"])
        self.assertEqual(flow, a["Route"])

    def test_read_vars_intStringTuples(self):
        plants = range(1, 5)
        stores = ["San_Diego", "Barstow", "Tucson", "Dallas"]

        plant_store = [(p, s) for p in plants for s in stores]
        # Creates the problem variables of the Flow on the Arcs
        flow = pulp.LpVariable.dicts("Route", plant_store, 0, None, pulp.LpInteger)
        _flow = {v.name: v for v in flow.values()}
        a = group_variables_by_name(_flow, ["Route"])
        self.assertEqual(flow, a["Route"])

    def test_read_vars_stringInts(self):
        plants_int = ["1", "2", "4", "5"]
        build_int = pulp.LpVariable.dicts(
            "BuildaPlant_int", plants_int, 0, 1, pulp.LpInteger
        )
        _build_int = {v.name: v for v in build_int.values()}
        b = group_variables_by_name(_build_int, ["BuildaPlant_int"])
        self.assertEqual(build_int, b["BuildaPlant_int"])

    def test_read_vars_string(self):
        plants = ["San Francisco", "Los Angeles", "Phoenix", "Denver"]
        # Creates the master problem variables of whether to build the Plants or not
        build = pulp.LpVariable.dicts("BuildaPlant", plants, 0, 1, pulp.LpInteger)
        _build = {v.name: v for v in build.values()}
        b = group_variables_by_name(
            _build, ["BuildaPlant"], replace_underscores_with_spaces=True
        )
        self.assertEqual(build, b["BuildaPlant"])

    def test_read_vars_tup_string_spaces(self):
        plants = ["San Francisco", "Los Angeles", "Phoenix", "Denver"]
        stores = ["San Diego", "Barstow", "Tucson", "Dallas"]
        plant_store = [(p, s) for p in plants for s in stores]
        flow = pulp.LpVariable.dicts("Route", plant_store, 0, None, pulp.LpInteger)
        _flow = {v.name: v for v in flow.values()}
        a = group_variables_by_name(
            _flow, ["Route"], replace_underscores_with_spaces=True
        )
        self.assertEqual(flow, a["Route"])

    def test_read_vars_twoVars(self):
        plants_int = range(1, 6)
        plants = ["San_Francisco", "Los_Angeles", "Phoenix", "Denver"]
        # Creates the master problem variables of whether to build the Plants or not
        build_int = pulp.LpVariable.dicts(
            "BuildaPlant_int", plants_int, 0, 1, pulp.LpInteger
        )
        build = pulp.LpVariable.dicts("BuildaPlant", plants, 0, 1, pulp.LpInteger)
        _build = {v.name: v for v in build_int.values()}
        _build.update({v.name: v for v in build.values()})
        b = group_variables_by_name(
            _build, ["BuildaPlant_int", "BuildaPlant"], force_number=True
        )
        self.assertEqual(build_int, b["BuildaPlant_int"])
        self.assertEqual(build, b["BuildaPlant"])
