# Cornflow

The aim of this repository is to create an open source optimization server.

## How to run it locally

### Setup cornflow database

In order to create the database, execute the follwing:

- > py manage.py db init
- > py manage.py db migrate
- > py manage.py db upgrade

### Starting flask server

Each time you run the flask server, execute the following:

- > set FLASK_APP=flaskr.app
- > set FLASK_ENV=development
- > set DATABASE_URL=postgres://postgres:postgresadmin@127.0.0.1:5432/cornflow
- > set SECRET_KEY=THISNEEDSTOBECHANGED
- > flask run

### Install airflow

#### On Linux

- install from pypi using pip
> pip3 install apache-airflow

- Create the dags folder in `user/airflow/dags`

- Copy `api_functions.py` and `optim_dag.py` from corn repository in the dags folder

- Edit airflow config (`airflow.cfg`)
    * `dags_folder = /home/[your user name]/dags`
    * `sql_alchemy_conn = postgres://postgres:postgresadmin@127.0.0.1:5432/airflow`
    * `load_examples = False`

- initialize the database
> airflow initdb

- Reset the database (if necesaary)
> airflow resetdb

- If necessary, give execution rights to your user in the airflow folder
> sudo chmod -R  a+rwx airflow

#### On windows

- Install Linux subsistems for linux
https://docs.microsoft.com/es-es/windows/wsl/install-win10

- Install Ubuntu from windows store

- Install python in Ubuntu and follow Linux installations instructions above.

### Launch airflow

Open two differents command prompts and execute the following commands:

- start the web server, default port is 8080
> airflow webserver -p 8080

- start the scheduler
> airflow scheduler

- airflow gui will be at
> localhost:8080

### Using cornflow

- Launch airflow and the flask server

- In order to use cornflow api, import api functions
> from api_functions import *

- Create a user:
> sign_up(email, pwd, name)

- log in
> token = login(email, pwd)

- create and log in as airflow user ( necessary until airflow is made a superuser)
> sign_up(email="airflow@noemail.com", pwd="airflow", name="airflow")
> token = login(email="airflow@noemail.com", pwd="airflow")

- create an instance
> instance_id = create_instance(token, data)

- Solve an instance
> execution_id = create_execution(token, instance_id, config)

- config format:
> config = {
    "solver": "PULP_CBC_CMD",
    "mip": True,
    "msg": True,
    "warmStart": True,
    "timeLimit": 10,
    "options": ["donotexist", "thisdoesnotexist"],
    "keepFiles": 0,
    "gapRel": 0.1,
    "gapAbs": 1,
    "maxMemory": 1000,
    "maxNodes": 1,
    "threads": 1,
    "logPath": "test_export_solver_json.log"
}


### Run an execution in airflow api (not necessary)

The execution id has to be passed like this:

<code>conf = "{\"exec_id\":\"%s\"}" % execution_id

response = requests.post(
        "http://localhost:8080/api/experimental/dags/solve_model_dag/dag_runs",
        json={"conf":conf})</code>
