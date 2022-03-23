# Imports from libraries
import pandas as pd
import json
from numpyencoder import (
    NumpyEncoder,
)  # To avoid TypeError: Object of type 'int64' is not JSON serializable


def excel_to_json(input_file_name, list_of_tables, output_file_name):
    """
    Reads tables from an Excel file, transforms their data to a list of dictionaries, adds these lists to an output dictionary and saves the output dictionary in a json file
    """
    result = {}
    for table in list_of_tables:
        df = pd.read_excel(input_file_name, sheet_name=table)
        content = [
            {
                df.columns[num_columns]: df[df.columns[num_columns]][num_rows]
                for num_columns in range(len(df.columns))
            }
            for num_rows in range(len(df))
        ]
        result[table] = content
    with open(output_file_name, "w") as output_file_name:
        json.dump(result, output_file_name, indent=4, cls=NumpyEncoder)


# Instance to json
input_file = "example_instance_1.xlsx"
tables = [
    "bars",
    "products",
    "demand",
    "cutting_patterns",
]
output_file = "example_instance_1.json"

excel_to_json(input_file, tables, output_file)

# Solution to json
input_file = "example_solution_1.xlsx"
tables = ["detail_cutting_patterns", "number_cutting_patterns"]
output_file = "example_solution_1.json"

excel_to_json(input_file, tables, output_file)
