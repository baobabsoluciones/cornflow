from cornflow_client import CornFlow, SchemaManager
from hackathonbaobab2020.tests import get_test_instance
from hackathonbaobab2020 import get_solver
import json
import os


email = 'pchtsp789@gmail.com'
pwd = 'some_password'
name = 'some_name'


def run_example():
    server = "https://devsm.cornflow.baobabsoluciones.app"
    server = "http://127.0.0.1:5000"
    server = 'http://34.76.18.17:5000/'
    client = CornFlow(url=server)

    config = dict(email=email, pwd=pwd, name=name)
    # a = client.sign_up(**config)
    a = client.login(email, pwd)
    insName = 'j102_6'
    description = 'j102_6 from j10.mm'
    #'j102_2.mm', 'j102_4.mm', 'j102_5.mm', 'j102_6.mm'
    instance_obj = get_test_instance('j10.mm.zip', 'j102_6.mm')

    data = instance_obj.to_dict()

    instance = client.create_instance(data,
                                      name=insName,
                                      description=description,
                                      data_schema='hk_2020_dag')

    config = dict(solver="default", timeLimit=10)
    execution = client.create_execution(
        instance['id'], config, name='default1', description='',
        dag_name='hk_2020_dag'
    )
    client.get_status(execution['id'])['state']
    data = client.get_solution(execution['id'])


def test_schema_solution():
    instance_obj = get_test_instance('j10.mm.zip', 'j102_6.mm')
    solver = get_solver('ortools')
    exp = solver(instance_obj)
    solution = exp.solve({})
    solution_dict = exp.solution.to_dict()
    file_name = os.path.join(os.path.dirname(__file__), "..", 'DAG', 'hk_2020_dag_output.json')
    os.path.exists(file_name)
    with open(file_name, 'r') as f:
        schema = json.load(f)
    marshmallow_obj = SchemaManager(schema).jsonschema_to_flask()
    data = marshmallow_obj().load(solution_dict)
    # marshmallow_obj().fields['jobs'].nested().fields['successors']


if __name__ == '__main__':
    test_schema_solution()