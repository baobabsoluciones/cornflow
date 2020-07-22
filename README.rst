Cornflow
=========

The aim of this repository is to create an open source optimization server.

Requirements
~~~~~~~~~~~~~~~~~~

* Linux or Windows with WSL
* python >= 3.5
* postgresql

Install cornflow
~~~~~~~~~~~~~~~~~~

do::

    git clone git@github.com:ggsdc/corn.git
    cd corn
    python3 -m venv venv
    source venv/bin/activate
    pip3 install -r requirements.txt

You now need to create a user and password in postgresql (we will be using `postgres` and `postgresadmin`). And also you need to create a database (we will be using one with the name `cornflow`).


Setup cornflow database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every time cornflow is used, PostgreSQL and airflow needs to be configured::

    export FLASK_APP=flaskr.app
    export FLASK_ENV=development
    export DATABASE_URL=postgres://postgres:postgresadmin@127.0.0.1:5432/cornflow
    export SECRET_KEY=THISNEEDSTOBECHANGED

In order to create the database, execute the following::

    python manage.py db init
    python manage.py db migrate
    python manage.py db upgrade

Starting flask server
~~~~~~~~~~~~~~~~~~~~~~~

Each time you run the flask server, execute the following::

    flask run


Configure airflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

airflow gets installed with cornFlow since it's listed as a dependency in the `requirements.py` file.

**On Linux**

    export AIRFLOW_HOME=PATH/TO/corn/airflow_config
    export AIRFLOW_HOME=/home/pchtsp/Documents/projects/corn/airflow_config
    airflow -h

If you want to use postgresql with airflow too you need to edit the existing values in airflow config (corn/airflow/airflow.cfg)::

    sql_alchemy_conn = postgres://postgres:postgresadmin@127.0.0.1:5432/airflow

In the same file, if you do not want the examples::

    load_examples = False

Create the `airflow` database in postgresql::

    MISSING (I did it using pgadmin3)

initialize the database::

    airflow initdb

Reset the database (if necessary, I did not need this)::

    airflow resetdb

If necessary, give execution rights to your user in the airflow folder (I did not need this) ::
    sudo chmod -R  a+rwx airflow

**On windows**

- Install Linux subsystems for linux: https://docs.microsoft.com/es-es/windows/wsl/install-win10
- Install Ubuntu from windows store
- Install python in Ubuntu and follow Linux installations instructions above.

Launch airflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open two differents command prompts and execute the following commands:

start the web server, default port is 8080::

    airflow webserver -p 8080 &

start the scheduler::

    airflow scheduler &

airflow gui will be at::

    localhost:8080

Select the DAG in the web and click on ON.

Killing airflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for the code of the process in Linux::

    ps aux | grep airflow

Kill it::

    kill -9 CODE

If you're filling lucky::
    
    kill -9 $(ps aux | grep 'airflow' | awk '{print $2}')

Using cornflow
~~~~~~~~~~~~~~~~~~

Launch airflow and the flask server

In order to use cornflow api, import api functions::

    from airflow_config.dags.api_functions import *

Create a user::

    sign_up(email, pwd, name)

log in::

    token = login(email, pwd)

create and log in as airflow user ( necessary until airflow is made a superuser)::

    sign_up(email="airflow@noemail.com", pwd="airflow", name="airflow")
    token = login(email="airflow@noemail.com", pwd="airflow")

create an instance::
    
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

    instance_id = create_instance(token, data)

Solve an instance::

    config = dict(
        solver = "PULP_CBC_CMD",
        mip = True,
        msg = True,
        warmStart = True,
        timeLimit = 10,
        options = ["donotexist", "thisdoesnotexist"],
        keepFiles = 0,
        gapRel = 0.1,
        gapAbs = 1,
        maxMemory = 1000,
        maxNodes = 1,
        threads = 1,
        logPath = "test_export_solver_json.log"
    )
    execution_id = create_execution(token, instance_id, config)

Retrieve a solution::

    data = get_data(token, execution_id)


Run an execution in airflow api (not needed)
~~~~~~~~~~~~~~~~~~

The execution id has to be passed like this:

<code>conf = "{\"exec_id\":\"%s\"}" % execution_id

response = requests.post(
        "http://localhost:8080/api/experimental/dags/solve_model_dag/dag_runs",
        json={"conf":conf})</code>
