

schemas_path = \
    dict(pulp_data_schema = "pulp_json_schema.json",
         hk_data_schema = "hk_data_schema.json"
         )

# factory of solvers
def get_path(name='pulp_data_schema'):
    return "./json_schemas/" + schemas_path[name]


