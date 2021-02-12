

schemas_path = dict(
    pulp_data_schema = "pulp_json_schema.json",
    hk_data_schema = "hk_data_schema.json",
    hk_solution_schema = "hk_solution_schema.json"
)

dag_schemas_input = dict(
    hk_2020_dag = "hk_data_schema",
    solve_model_dag = "pulp_data_schema",
)

def get_path(name='pulp_data_schema'):
    
    if name in schemas_path:
        return "./json_schemas/" + schemas_path[name]
    else:
        return None
    
    
def get_dag_schema(name = "solve_model_dag"):
    
    if name not in dag_schemas_input:
        return None
    schema_name = dag_schemas_input[name]
    
    path = get_path(schema_name)
    
    return path
    
    


