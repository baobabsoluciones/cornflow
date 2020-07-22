import airflow_config.dags.api_functions as af

email = 'some_email@gmail.com'
pwd = 'some_password'
name = 'some_name'

config = dict(email=email, pwd=pwd, name=name)

af.sign_up(**config)
token = af.login(email, pwd)

af.sign_up(email="airflow@noemail.com", pwd="airflow", name="airflow")
token = af.login(email="airflow@noemail.com", pwd="airflow")

import pulp
prob = pulp.LpProblem("test_export_dict_MIP", pulp.LpMinimize)
x = pulp.LpVariable("x", 0, 4)
y = pulp.LpVariable("y", -1, 1)
z = pulp.LpVariable("z", 0, None, pulp.LpInteger)
prob += x + 4 * y + 9 * z, "obj"
prob += x + y <= 5, "c1"
prob += x + z >= 10, "c2"
prob += -y + z == 7.5, "c3"
data = prob.to_dict()

instance_id = af.create_instance(token, data)

config = dict(
    solver="PULP_CBC_CMD",
    mip=True,
    msg=True,
    warmStart=True,
    timeLimit=10,
    options=["donotexist", "thisdoesnotexist"],
    keepFiles=0,
    gapRel=0.1,
    gapAbs=1,
    maxMemory=1000,
    maxNodes=1,
    threads=1,
    logPath="test_export_solver_json.log"
)
execution_id = af.create_execution(token, instance_id, config)
data = af.get_data(token, execution_id)

data['data']['sos1'] = {}
data['data']['sos2'] = {}
_vars, prob = pulp.LpProblem.from_dict(data['data'])

