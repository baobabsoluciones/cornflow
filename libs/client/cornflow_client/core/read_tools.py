"""

"""
# Full imports
import math

# Partial imports
from pytups import TupList, SuperDict
import numbers


def read_excel(path: str, param_tables_names: list = None) -> dict:
    """
    Read an entire excel file.

    :param path: path of the excel file
    :param param_tables_names: names of the parameter tables
    :return: a dict with a list of dict (records format) for each table.
    """
    is_xl_type(path)

    try:
        import openpyxl
    except (ModuleNotFoundError, ImportError) as e:
        raise Exception("You must install openpyxl package to use this method")

    try:
        import pandas as pd
    except (ModuleNotFoundError, ImportError):
        raise Exception("You must install pandas package to use this method")

    data = pd.read_excel(path, sheet_name=None)

    data_tables = {
        name: TupList(content.to_dict(orient="records")).vapply(
            lambda v: SuperDict(v).vapply(lambda vv: format_value(vv))
        )
        for name, content in data.items()
        if name not in param_tables_names
    }

    parameters_tables = {
        t: SuperDict(read_param_table(path, t)).vapply(lambda v: format_value(v))
        for t in param_tables_names
    }

    return {**data_tables, **parameters_tables}


def read_param_table(path: str, table: str) -> dict:
    """
    Read a list of parameters and their values from excel as a dict.

    :param path: the excel file path
    :param table: the table name
    :return: a dict {param1: val1}
    """

    content = read_excel_table(path, table, header=None)
    return {d[0]: d[1] for d in content}


def read_excel_table(path: str, table: str, **kwargs):
    """
    Read a table from excel

    :param path: the excel file path
    :param table: the table name
    :return: a list of dict
    """
    try:
        import pandas as pd
    except (ModuleNotFoundError, ImportError):
        raise Exception("You must install pandas package to use this method")

    data = pd.read_excel(path, sheet_name=table, **kwargs)

    return data.to_dict(orient="records")


def format_value(value):
    """"""
    if isinstance(value, str):
        if value in ["TRUE", "True"]:
            return True
        if value in ["FALSE", "False"]:
            return False
        return value
    if isinstance(value, bool):
        return value

    if not isinstance(value, numbers.Number):
        return str(value)
    if math.isnan(value):
        return None
    return value


def is_xl_type(path: str):
    """
    Check if a path is an excel file. Raises an error if the file is not an excel file

    :param path: path of the file
    """
    if not any(ext in path for ext in [".xlsx", ".xls", ".xlsm"]):
        raise ConnectionError(
            "Excel_file argument should be a string with an excel extension"
        )
