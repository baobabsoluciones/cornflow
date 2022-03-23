from DAG.facility_location.core import Instance
import os
from pytups import SuperDict

data_dir = os.path.join(os.path.dirname(__file__), "../data")


def generate_data():
    instance = Instance.from_file(data_dir + "/base_example.xlsx")
    print(instance.check_schema())
    instance.to_json(data_dir + "/input_data_test1.json")


if __name__ == "__main__":
    generate_data()
