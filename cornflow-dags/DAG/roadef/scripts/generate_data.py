from DAG.roadef import Roadef as App
import os

data_dir = os.path.join(os.path.dirname(__file__), "../data")
app = App()


def generate_instance():
    instance = app.instance.from_file(data_dir + "/Instance_V_1.0_ConvertedTo_V2.xml")
    from random import sample

    instance.data["horizon"] = 24
    instance.to_json(os.path.join(data_dir, "example_instance_filtered.json"))
    instance.from_json(os.path.join(data_dir, "example_instance_filtered.json"))
    instance.check_schema()


def generate_solution():

    instance_code = "filtered"
    # instance_code = "1"
    instance = app.instance.from_json(
        data_dir + "/example_instance_{}.json".format(instance_code)
    )

    self = app.get_solver("MIPModel")(instance)
    self.solve(dict(solver="MIPModel.PULP_CBC_CMD", threads=8, timeLimit=60, msg=True))
    # self.solve(dict(solver="CPLEX_CMD", threads=8, timeLimit=60, msg=True))
    solution_file = data_dir + "/example_solution_{}.json".format(instance_code)
    self.solution.to_json(solution_file)
    checks = self.check_solution()
    solution = app.solution.from_json(solution_file)
    solution.check_schema()


if __name__ == "__main__":
    generate_instance()
    generate_solution()
