"""

"""

# Full imports
import io
import json
import pandas as pd
import pickle

# Partial imports
from openpyxl import load_workbook
from openpyxl.formatting import Rule
from openpyxl.styles import PatternFill, Font, Border, Side
from openpyxl.styles.differential import DifferentialStyle
from openpyxl.utils import get_column_letter
from pytups import OrderSet
from typing import Optional


def new_set(seq):
    """
    :param seq: a (hopefully unique) list of elements (tuples, strings, etc.)
    Returns a new ordered set
    """
    return OrderSet(seq)


def load_json(path):
    with open(path) as json_file:
        file = json.load(json_file)
    return file


def save_json(data, path):
    with open(path, "w") as outfile:
        json.dump(data, outfile)


def copy(dictionary):
    return pickle.loads(pickle.dumps(dictionary, -1))


def to_excel_memory_file(data: dict) -> Optional[io.BytesIO]:
    """
    Converts a json into an Excel memory file
    :param data: a json dictionary
    :return: Formatted Excel file in memory as a BytesIO object
    """
    if not data:
        return None
    # Save Excel
    memory_file = io.BytesIO()
    used_table_names = {}
    max_length = 31
    with pd.ExcelWriter(memory_file) as writer:
        for table_name, table_data in data.items():
            # Handle the case where sheet names are too long.
            truncated_name = table_name
            if len(table_name) > max_length:
                truncated_name = table_name[:max_length]
            if truncated_name in used_table_names:
                current_suffix = used_table_names[truncated_name] + 1
                truncated_name_w_suffix = (
                    f"{truncated_name[:max_length - 3]}_{current_suffix}"
                )
            used_table_names[truncated_name] = 0
            truncated_name = truncated_name_w_suffix

            df = pd.DataFrame(table_data)
            df.to_excel(writer, sheet_name=truncated_name, index=False)

    memory_file.seek(0)
    memory_file = format_excel_file(memory_file)

    return memory_file


def format_excel_file(memory_file: io.BytesIO) -> io.BytesIO:
    """
    Formats an Excel file with the frontend format
    :param memory_file: Excel file in memory as a BytesIO object
    :return: Formatted Excel file in memory as a BytesIO object
    """
    wb = load_workbook(memory_file)
    ws = wb.active
    styles = {
        "header": {
            "fill": PatternFill(
                start_color="4A90E2", end_color="4A90E2", fill_type="solid"
            ),
            "font": Font(bold=True, color="FFFFFF"),
            "border": Border(
                left=Side(style="thin", color="FFFFFF"),
                right=Side(style="thin", color="FFFFFF"),
                top=Side(style="thin", color="FFFFFF"),
                bottom=Side(style="thin", color="FFFFFF"),
            ),
        },
        "even_row": {
            "fill": PatternFill(
                start_color="F8F9FA", end_color="F8F9FA", fill_type="solid"
            ),
            "font": Font(bold=False, color="000000"),
            "border": Border(
                left=Side(style="thin", color="E1E5E9"),
                right=Side(style="thin", color="E1E5E9"),
                top=Side(style="thin", color="E1E5E9"),
                bottom=Side(style="thin", color="E1E5E9"),
            ),
        },
        "odd_row": {
            "fill": PatternFill(
                start_color="FFFFFF", end_color="FFFFFF", fill_type="solid"
            ),
            "font": Font(bold=False, color="000000"),
            "border": Border(
                left=Side(style="thin", color="E1E5E9"),
                right=Side(style="thin", color="E1E5E9"),
                top=Side(style="thin", color="E1E5E9"),
                bottom=Side(style="thin", color="E1E5E9"),
            ),
        },
    }
    max_row = ws.max_row
    max_col = get_column_letter(ws.max_column)
    max_cell = f"{max_col}{max_row}"

    dfx_header = DifferentialStyle(
        fill=styles["header"]["fill"],
        font=styles["header"]["font"],
        border=styles["header"]["border"],
    )
    r = Rule(
        type="expression",
        dxf=dfx_header,
        formula=["ROW()=1"],
    )
    ws.conditional_formatting.add(f"A1:{max_cell}", r)

    dfx_even_rows = DifferentialStyle(
        fill=styles["even_row"]["fill"],
        font=styles["even_row"]["font"],
        border=styles["even_row"]["border"],
    )
    r = Rule(
        type="expression",
        dxf=dfx_even_rows,
        formula=["AND(MOD(ROW(),2)=0, ROW()<>1)"],
    )
    ws.conditional_formatting.add(f"A1:{max_cell}", r)

    dfx_odd_rows = DifferentialStyle(
        fill=styles["odd_row"]["fill"],
        font=styles["odd_row"]["font"],
        border=styles["odd_row"]["border"],
    )
    r = Rule(
        type="expression",
        dxf=dfx_odd_rows,
        formula=["AND(MOD(ROW(),2)=1, ROW()<>1)"],
    )
    ws.conditional_formatting.add(f"A1:{max_cell}", r)

    for j, col in enumerate(ws.iter_cols()):
        max_str_length = max(len(str(cell.value)) for cell in col[: min(max_row, 1000)])
        ws.column_dimensions[get_column_letter(j + 1)].width = (
            max(max_str_length, 8) * 1.2
        )

    memory_file = io.BytesIO()
    wb.save(memory_file)
    memory_file.seek(0)

    return memory_file
