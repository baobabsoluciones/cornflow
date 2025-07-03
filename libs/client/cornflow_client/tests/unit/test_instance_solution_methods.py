""" """

import json
import os
import pickle
from datetime import datetime, timedelta
from unittest import TestCase
from cornflow_client.core import InstanceSolutionCore

from cornflow_client import InstanceCore, ExperimentCore

from cornflow_client.schema.tools import get_empty_schema


# Constants
path_to_tests_dir = os.path.dirname(os.path.abspath(__file__))


# Helper functions
def _load_file(_file):
    with open(_file) as f:
        temp = json.load(f)
    return temp


def _get_file(relative_path):
    return os.path.join(path_to_tests_dir, relative_path)


class TestSimpleApplicationDag(TestCase):
    def setUp(self):
        self.class_to_use = SimpleInstance
        self.instance_filename = _get_file("../data/gc_input.json")
        self.instance_data = _load_file(self.instance_filename)
        self.schema = get_empty_schema()

    def tearDown(self):
        pass

    def instance_from_dict(self):
        return self.class_to_use.from_dict(self.instance_data)

    def instance_from_json(self):
        return self.class_to_use.from_json(self.instance_filename)

    def test_instance_from_dict(self):
        instance = self.instance_from_dict()
        self.assertEqual(self.instance_data, instance.data)

    def test_instance_to_dict(self):
        instance = self.instance_from_dict()
        self.assertEqual(self.instance_data, instance.to_dict())

    def test_instance_from_json(self):
        instance = self.instance_from_json()
        self.assertEqual(self.instance_data, instance.data)

    def test_instance_to_json(self):
        instance = self.instance_from_json()
        instance.to_json(_get_file("../data/gc_input_export.json"))
        read_data = _load_file(_get_file("../data/gc_input.json"))
        self.assertEqual(self.instance_data, read_data)
        os.remove(_get_file("../data/gc_input_export.json"))

    def test_instance_schema(self):
        instance = self.instance_from_dict()
        self.assertEqual(self.schema, instance.schema)

    def test_schema_validation(self):
        instance = self.instance_from_dict()
        self.assertEqual([], instance.check_schema())

    def test_schema_generation(self):
        instance = self.instance_from_dict()
        schema = _load_file(_get_file("../data/graph_coloring_input.json"))
        schema["properties"]["pairs"].pop("description")
        self.assertEqual(schema, instance.generate_schema())

    def test_to_excel(self):
        instance = self.instance_from_dict()
        instance.to_excel(_get_file("../data/gc_input_export.xlsx"))
        instance_2 = self.class_to_use.from_excel(
            _get_file("../data/gc_input_export.xlsx")
        )
        self.assertEqual(instance.data, instance_2.data)
        os.remove(_get_file("../data/gc_input_export.xlsx"))

    def test_dict_to_int_or_float(self):
        # Test with simple input
        input_dict = {"a": "4", "b": "7.8"}
        expected_output = {"a": 4, "b": 7.8}
        self.assertEqual(
            InstanceSolutionCore.dict_to_int_or_float(input_dict), expected_output
        )

        # Test with nested dictionary and list
        input_dict = {"a": "4", "b": {"c": "7", "d": ["8.7", "9"]}}
        expected_output = {"a": 4, "b": {"c": 7, "d": [8.7, 9]}}
        self.assertEqual(
            InstanceSolutionCore.dict_to_int_or_float(input_dict), expected_output
        )
        input_dict = {"a": "4", "b": {"c": "7", "d": "not_a_number"}}
        expected_output = {"a": 4, "b": {"c": 7, "d": "not_a_number"}}
        self.assertEqual(
            InstanceSolutionCore.dict_to_int_or_float(input_dict), expected_output
        )

    def test_from_element_or_list_to_dict(self):
        # Test with list input
        input_list = [{"index": 4, "value": 5}, {"index": 7, "value": 8}]
        expected_output = {4: {"index": 4, "value": 5}, 7: {"index": 7, "value": 8}}
        self.assertEqual(
            InstanceSolutionCore.from_element_or_list_to_dict(input_list),
            expected_output,
        )

        # Test with single element input
        input_dict = {"index": 4, "value": 5}
        expected_output = {4: {"index": 4, "value": 5}}
        self.assertEqual(
            InstanceSolutionCore.from_element_or_list_to_dict(input_dict),
            expected_output,
        )

    def test_get_date_from_string(self):
        date_string = "2022-01-01"
        expected_output = datetime.strptime(date_string, "%Y-%m-%d")
        self.assertEqual(
            InstanceSolutionCore.get_date_from_string(date_string), expected_output
        )

    def test_get_datetime_from_string(self):
        datetime_string = "2022-01-01T12:34"
        expected_output = datetime.strptime(datetime_string, "%Y-%m-%dT%H:%M")
        self.assertEqual(
            InstanceSolutionCore.get_datetime_from_string(datetime_string),
            expected_output,
        )

    def test_get_datetimesec_from_string(self):
        string = "2022-01-01T00:00:00"
        expected_result = datetime(2022, 1, 1, 0, 0, 0)
        self.assertEqual(
            InstanceSolutionCore.get_datetimesec_from_string(string), expected_result
        )

    def test_get_datetime_from_date_hour(self):
        date = "2022-01-01"
        hour = 0
        expected_result = datetime(2022, 1, 1, 0)
        self.assertEqual(
            InstanceSolutionCore.get_datetime_from_date_hour(date, hour),
            expected_result,
        )

    def test_get_date_hour_from_string_with_zero_to_twenty_four(self):
        # Test with zero_to_twenty_four set to True
        string = "2021-01-01T00:00:00"
        date, hour = InstanceSolutionCore.get_date_hour_from_string(string, True)
        self.assertEqual(date, "2020-12-31")
        self.assertEqual(hour, 24)

    def test_get_date_hour_from_string_without_zero_to_twenty_four(self):
        # Test with zero_to_twenty_four set to False
        string = "2021-01-01T00:00:00"
        date, hour = InstanceSolutionCore.get_date_hour_from_string(string, False)
        self.assertEqual(date, "2021-01-01")
        self.assertEqual(hour, 0)

    def test_get_date_hour_from_string_with_noon_time(self):
        # Test with a string representing noon time
        string = "2021-01-01T12:00:00"
        date, hour = InstanceSolutionCore.get_date_hour_from_string(string, False)
        self.assertEqual(date, "2021-01-01")
        self.assertEqual(hour, 12)

    def test_get_date_string_from_ts(self):
        ts = datetime(2022, 1, 1, 0, 0, 0)
        expected_result = "2022-01-01"
        self.assertEqual(
            InstanceSolutionCore.get_date_string_from_ts(ts), expected_result
        )

    def test_get_datetime_string_from_ts(self):
        ts = datetime(2022, 1, 1, 0, 0, 0)
        expected_result = "2022-01-01T00:00"
        self.assertEqual(
            InstanceSolutionCore.get_datetime_string_from_ts(ts), expected_result
        )

    def test_get_datetimesec_string_from_ts(self):
        ts = datetime(2022, 1, 1, 0, 0, 0)
        expected_result = "2022-01-01T00:00:00"
        self.assertEqual(
            InstanceSolutionCore.get_datetimesec_string_from_ts(ts), expected_result
        )

    def test_get_next_hour_datetime_string(self):
        string = "2022-01-01T00:00:00"
        expected_result = "2022-01-01T01:00:00"
        self.assertEqual(
            InstanceSolutionCore.get_next_hour_datetime_string(string), expected_result
        )

    def test_get_next_hour_datetimesec_string(self):
        string = "2022-01-01T00:00:00"
        expected_result = "2022-01-01T01:00:00"
        self.assertEqual(
            InstanceSolutionCore.get_next_hour_datetimesec_string(string),
            expected_result,
        )

    def test_get_next_hour(self):
        ts = datetime(2022, 1, 1, 12)
        expected = datetime(2022, 1, 1, 13)
        self.assertEqual(InstanceSolutionCore.get_next_hour(ts), expected)

    def test_get_previous_hour_datetime_string(self):
        input_string = "2022-10-11T15:45:30"
        expected_output = "2022-10-11T14:45:30"
        self.assertEqual(
            InstanceSolutionCore.get_previous_hour_datetime_string(input_string),
            expected_output,
        )

    def test_get_previous_hour_datetimesec_string(self):
        input_string = "2022-10-11T15:45:30.123456"
        expected_output = "2022-10-11T14:45:30.123456"
        self.assertEqual(
            InstanceSolutionCore.get_previous_hour_datetimesec_string(input_string),
            expected_output,
        )

    def test_get_previous_hour(self):
        input_ts = datetime(2022, 10, 11, 15, 45, 30)
        expected_output = datetime(2022, 10, 11, 14, 45, 30)
        self.assertEqual(
            InstanceSolutionCore.get_previous_hour(input_ts), expected_output
        )

    def test_get_date_string_from_ts_string(self):
        input_ts = "2022-10-11T15:45:30"
        expected_output = "2022-10-11"
        self.assertEqual(
            InstanceSolutionCore.get_date_string_from_ts_string(input_ts),
            expected_output,
        )

    def test_get_hour_from_ts(self):
        input_ts = datetime(2022, 10, 11, 15, 45, 30)
        expected_output = 15.75
        self.assertEqual(
            InstanceSolutionCore.get_hour_from_ts(input_ts), expected_output
        )

    def test_add_time_to_ts(self):
        input_ts = datetime(2022, 10, 11, 15, 45, 30)
        expected_output = datetime(2022, 10, 18, 15, 45, 30)
        self.assertEqual(
            InstanceSolutionCore.add_time_to_ts(input_ts, days=7), expected_output
        )

    def test_add_time_to_date_string(self):
        instance = self.class_to_use.from_dict(self.instance_data)
        initial_date = "2022-10-11"
        expected_date = (
            datetime.strptime(initial_date, "%Y-%m-%d").date() + timedelta(days=7)
        ).strftime("%Y-%m-%d")
        result = instance.add_time_to_date_string(initial_date, days=7)
        self.assertEqual(result, expected_date)

    def test_add_time_to_datetime_string(self):
        initial_datetime = "2022-01-01T12:00:00"
        expected_datetime = (
            datetime.strptime(initial_datetime, "%Y-%m-%dT%H:%M:%S")
            + timedelta(weeks=2, days=3, minutes=45, seconds=30)
        ).strftime("%Y-%m-%dT%H:%M:%S")
        result = InstanceSolutionCore.add_time_to_datetime_string(
            initial_datetime, weeks=2, days=3, minutes=45, seconds=30
        )
        self.assertEqual(result, expected_datetime)

    def test_add_time_to_datetimesec_string(self):
        string = "2022-01-01T12:00:00"
        result = InstanceSolutionCore.add_time_to_datetimesec_string(string, days=1)
        expected = "2022-01-02T12:00:00"
        self.assertEqual(result, expected)

    def test_get_week_from_ts(self):
        ts = datetime(2022, 1, 1)
        result = InstanceSolutionCore.get_week_from_ts(ts)
        expected = 52
        self.assertEqual(result, expected)

    def test_get_week_from_date_string(self):
        string = "2022-01-01"
        result = InstanceSolutionCore.get_week_from_date_string(string)
        expected = 52
        self.assertEqual(result, expected)

    def test_get_week_from_datetime_string(self):
        string = "2022-01-01T12:00"
        result = InstanceSolutionCore.get_week_from_datetime_string(string)
        expected = 52
        self.assertEqual(result, expected)

    def test_get_week_from_datetimesec_string(self):
        string = "2022-01-01T12:00:00"
        result = InstanceSolutionCore.get_week_from_datetimesec_string(string)
        expected = 52
        self.assertEqual(result, expected)

    def test_get_weekday_from_ts(self):
        ts = datetime(2022, 1, 1)
        result = InstanceSolutionCore.get_weekday_from_ts(ts)
        expected = 6
        self.assertEqual(result, expected)

    def test_get_weekday_from_date_string(self):
        string = "2022-01-01"
        result = InstanceSolutionCore.get_weekday_from_date_string(string)
        expected = 6
        self.assertEqual(result, expected)

    def test_get_weekday_from_datetime_string(self):
        string = "2022-01-01T12:00:00"
        result = InstanceSolutionCore.get_weekday_from_datetime_string(string)
        expected = 6
        self.assertEqual(result, expected)

    def test_get_weekday_from_datetimesec_string(self):
        string = "2022-01-01T12:00:00"
        result = InstanceSolutionCore.get_weekday_from_datetimesec_string(string)
        expected = 6
        self.assertEqual(result, expected)

    def test_get_hour_from_datetime_string(self):
        datetime_string = "2023-01-01T12:00:00"
        expected_hour = 12
        result = InstanceSolutionCore.get_hour_from_datetime_string(datetime_string)
        self.assertEqual(result, expected_hour)

    def test_get_hour_from_datetimesec_string(self):
        datetime_string = "2023-01-01T12:00:00"
        expected_hour = 12
        result = InstanceSolutionCore.get_hour_from_datetimesec_string(datetime_string)
        self.assertEqual(result, expected_hour)


######################################################
class TestCustomInstanceDag(TestSimpleApplicationDag):
    def setUp(self):
        super().setUp()
        self.class_to_use = Instance
        self.schema = _load_file(_get_file("../data/graph_coloring_input.json"))

    def test_instance_from_dict(self):
        """Here as to be not equal as the data has been processed on the from_dict method"""
        instance = self.class_to_use.from_dict(self.instance_data)
        self.assertNotEqual(self.instance_data, instance.data)

    def test_instance_from_json(self):
        """Here as to be not equal as the data has been processed on the from_dict method"""
        instance = self.class_to_use.from_json(self.instance_filename)
        self.assertNotEqual(self.instance_data, instance.data)


class TestExperimentCore(TestCase):
    def setUp(self):
        self.class_to_use = SimpleExperiment
        self.schema = get_empty_schema()

    def test_get_solver_config_pulp(self):
        initial_config = {
            "solver": "mip.GUROBI_CMD",
            "timeLimit": 10,
            "iteration_limit": 10,
        }
        res = self.class_to_use.get_solver_config(initial_config, lib="pulp")
        self.assertEqual(res, {"timeLimit": 10, "IterationLimit": 10})

    def test_get_solver_config_pyomo(self):
        initial_config = {"solver": "mip.scip", "timeLimit": 10, "iteration_limit": 10}
        res = self.class_to_use.get_solver_config(initial_config)
        self.assertEqual(res, {"limits/time": 10, "lp/iterlim": 10})

    def test_get_solver_config_with_remove_unknow(self):
        """testing the function get_solver_config when config has solver and solver_config arguments"""
        config = dict(
            solver="milp_solver.gurobi",
            msg=True,
            abs_gap=5,
            aditional_in_config=True,
            solver_config=dict(
                time_limit=10 * 60, rel_gap=0.001, additional_in_solver_config=True
            ),
        )

        expected = {
            "TimeLimit": 600,
            "MIPGap": 0.001,
            "MIPGapAbs": 5,
            "OutputFlag": True,
            "additional_in_solver_config": True,
        }
        result = self.class_to_use.get_solver_config(config, remove_unknown=True)
        msg = "if remove_unknown is true, unmapped argument should be removed from config but not from solver_config"
        self.assertEqual(expected, result, msg=msg)

    def test_get_solver_config_without_remove_unknow(self):
        """testing the function get_solver_config when the argument remove_unknown is False"""
        config = dict(
            solver="milp_solver.gurobi",
            msg=True,
            abs_gap=5,
            aditional_in_config=True,
            solver_config=dict(
                time_limit=10 * 60, rel_gap=0.001, additional_in_solver_config=True
            ),
        )

        expected = {
            "TimeLimit": 600,
            "MIPGap": 0.001,
            "MIPGapAbs": 5,
            "additional_in_solver_config": True,
            "aditional_in_config": True,
            "OutputFlag": True,
        }
        result = self.class_to_use.get_solver_config(config, remove_unknown=False)
        msg = "if remove_unknown is false, unmapped argument should not be removed from config and solver_config"
        self.assertEqual(expected, result, msg=msg)

    def test_get_solver_config_without_remove_unknow_and_solver_config(self):
        """testing the function get_solver_config when the argument remove_unknown is False and solver_config does not exist"""
        config = dict(
            solver="milp_solver.gurobi",
            msg=True,
            abs_gap=5,
            additional=True,
        )

        expected = {"MIPGapAbs": 5, "OutputFlag": True, "additional": True}
        result = self.class_to_use.get_solver_config(config, remove_unknown=False)
        msg = "if remove_unknown is false, unmapped argument should not be removed from config"
        self.assertEqual(expected, result, msg=msg)

    def test_get_solver_config_with_remove_unknow_without_solver_config(self):
        """testing the function get_solver_config when the argument remove_unknown is True and solver_config does not exist"""
        config = dict(
            solver="milp_solver.gurobi",
            msg=True,
            abs_gap=5,
            additional=True,
        )

        expected = {"MIPGapAbs": 5, "OutputFlag": True}
        result = self.class_to_use.get_solver_config(config, remove_unknown=True)
        msg = (
            "if remove_unknown is true, unmapped argument should be removed from config"
        )
        self.assertEqual(expected, result, msg=msg)

    def test_get_solver_config_without_remove_unknow_with_Outputflag(self):
        """testing the function get_solver_config when the argument remove_unknown is True and solver_config does not exist"""
        config = dict(
            solver="milp_solver.gurobi",
            OutputFlag=True,
            abs_gap=5,
        )

        expected = {"MIPGapAbs": 5, "OutputFlag": True}
        result = self.class_to_use.get_solver_config(config, remove_unknown=False)
        msg = "if remove_unknown is false, unmapped argument should not be removed from config"
        self.assertEqual(expected, result, msg=msg)

    def test_get_solver_config_with_remove_unknow_with_Outputflag(self):
        """testing the function get_solver_config when the argument remove_unknown is True and solver_config does not exist"""
        config = dict(
            solver="milp_solver.gurobi",
            OutputFlag=True,
            abs_gap=5,
        )

        expected = {"MIPGapAbs": 5}
        result = self.class_to_use.get_solver_config(config, remove_unknown=True)
        msg = (
            "if remove_unknown is true, unmapped argument should be removed from config"
        )
        self.assertEqual(expected, result, msg=msg)

    def test_get_solver_config_empty(self):
        """testing the function get_solver_config when the argument config is empty"""
        config = dict()

        expected = {}
        result = self.class_to_use.get_solver_config(config)
        msg = "the dictionary has to be empty"
        self.assertEqual(expected, result, msg=msg)

    def test_get_solver_config(self):
        """testing the function get_solver_config when config has only solver and solver_config arguments"""
        config = dict(
            solver="milp_solver.gurobi",
            solver_config=dict(time_limit=10 * 60, rel_gap=0.001),
        )

        expected = {"TimeLimit": 600, "MIPGap": 0.001}
        result = self.class_to_use.get_solver_config(config)
        msg = "only solver_config arguments has to be included"
        self.assertEqual(expected, result, msg=msg)

    def test_cornflow_mapping(self):
        """testing the function get_solver_config mapping msg to OutputFlag and abs_gap to MIPGapAbs"""
        config = dict(
            solver="milp_solver.gurobi",
            msg=True,
            abs_gap=5,
        )

        expected = {"MIPGapAbs": 5, "OutputFlag": True}
        result = self.class_to_use.get_solver_config(config)
        msg = "msg has to be mapped to OutputFlag and abs_gap to MIPGapAbs"
        self.assertEqual(expected, result, msg=msg)

    def test_get_solver_config_pyomo_2(self):
        initial_config = {
            "solver": "mip.scip",
            "solver_config": {"timeLimit": 10, "iteration_limit": 10},
        }
        res = self.class_to_use.get_solver_config(initial_config)
        self.assertEqual(res, {"limits/time": 10, "lp/iterlim": 10})


class SimpleInstance(InstanceCore):
    schema = get_empty_schema()
    schema_checks = get_empty_schema()

    def check(self) -> dict:
        return {}


class Instance(InstanceCore):
    schema = _load_file(_get_file("../data/graph_coloring_input.json"))
    schema_checks = get_empty_schema()

    @classmethod
    def from_dict(cls, data):
        tables = ["pairs"]

        data_p = {el: {(v["n1"], v["n2"]): v for v in data[el]} for el in tables}

        return cls(data_p)

    def to_dict(self):
        tables = ["pairs"]

        data_p = {el: self.data[el].values_l() for el in tables}
        return pickle.loads(pickle.dumps(data_p, -1))

    def check(self) -> dict:
        return {}


class SimpleExperiment(ExperimentCore):
    schema_checks = get_empty_schema()

    def solve(self) -> dict:
        return 0, 0

    def get_objective(self) -> float:
        return 0

    def check_solution(self):
        return dict()
