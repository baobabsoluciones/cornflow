import os
from cornflow_client.constants import DATASCHEMA

path_to_tests_dir = os.path.dirname(os.path.abspath(__file__))


def _get_file(relative_path):
    return os.path.join(path_to_tests_dir, relative_path)


dict_example = dict(
    CoefficientSchema=[
        dict(
            name="name",
            type="String",
            required=True,
            allow_none=False,
            many=False,
            strict=True,
        ),
        dict(
            name="value",
            type="Float",
            required=True,
            allow_none=False,
            many=False,
            strict=True,
        ),
    ],
    ObjectiveSchema=[
        dict(
            name="name",
            type="String",
            required=False,
            allow_none=True,
            many=False,
            strict=True,
        ),
        dict(name="coefficients", type="CoefficientSchema", many=True, required=True),
    ],
    ConstraintsSchema=[
        dict(
            name="name",
            type="String",
            required=True,
            allow_none=False,
            many=False,
            strict=True,
        ),
        dict(
            name="sense",
            type="Integer",
            required=True,
            allow_none=False,
            many=False,
            strict=True,
        ),
        dict(
            name="pi",
            type="Float",
            required=True,
            allow_none=True,
            many=False,
            strict=True,
        ),
        dict(
            name="constant",
            type="Float",
            required=False,
            allow_none=True,
            many=False,
            strict=True,
        ),
        dict(name="coefficients", type="CoefficientSchema", many=True, required=True),
    ],
    VariablesSchema=[
        dict(
            name="name",
            type="String",
            required=True,
            allow_none=False,
            many=False,
            strict=True,
        ),
        dict(
            name="lowBound",
            type="Float",
            allow_none=True,
            required=False,
            many=False,
            strict=True,
        ),
        dict(
            name="upBound",
            type="Float",
            allow_none=True,
            required=False,
            many=False,
            strict=True,
        ),
        dict(
            name="cat",
            type="String",
            required=True,
            allow_none=False,
            many=False,
            strict=True,
        ),
        dict(
            name="dj",
            type="Float",
            allow_none=True,
            required=False,
            many=False,
            strict=True,
        ),
        dict(
            name="varValue",
            type="Float",
            allow_none=True,
            required=False,
            many=False,
            strict=True,
        ),
    ],
    ParametersSchema=[
        dict(
            name="name",
            type="String",
            required=True,
            allow_none=False,
            many=False,
            strict=True,
        ),
        dict(
            name="sense",
            type="Integer",
            required=True,
            allow_none=False,
            many=False,
            strict=True,
        ),
        dict(
            name="status",
            type="Integer",
            allow_none=False,
            many=False,
            required=False,
            strict=True,
        ),
        dict(
            name="sol_status",
            type="Integer",
            allow_none=False,
            many=False,
            required=False,
            strict=True,
        ),
    ],
    Sos1Schema=[
        dict(
            name="placeholder",
            type="String",
            required=False,
            allow_none=False,
            many=False,
            strict=True,
        ),
    ],
    Sos2Schema=[
        dict(
            name="placeholder",
            type="String",
            required=False,
            allow_none=False,
            many=False,
            strict=True,
        ),
    ],
)

dict_example.update(
    {
        DATASCHEMA: [
            dict(name="objective", type="ObjectiveSchema", required=True, many=False),
            dict(name="parameters", type="ParametersSchema", required=True, many=False),
            dict(
                name="constraints", type="ConstraintsSchema", many=True, required=True
            ),
            dict(name="variables", type="VariablesSchema", many=True, required=True),
            dict(name="sos1", type="Sos1Schema", many=True, required=False),
            dict(name="sos2", type="Sos2Schema", many=True, required=False),
        ]
    }
)

PULP_EXAMPLE = _get_file("./data/pulp_example_data.json")

PUBLIC_DAGS = [
    "solve_model_dag",
    "graph_coloring",
    "timer",
    "bar_cutting",
    "facility_location",
    "graph_coloring",
    "hk_2020_dag",
    "knapsack",
    "roadef",
    "rostering",
    "tsp",
    "vrp",
]
