Cornflow
=========

.. image:: https://github.com/baobabsoluciones/corn/workflows/build/badge.svg?style=svg
    :target: https://github.com/baobabsoluciones/corn/actions

.. image:: https://github.com/baobabsoluciones/corn/workflows/docs/badge.svg?style=svg
    :target: https://github.com/baobabsoluciones/corn/actions

.. image:: https://github.com/baobabsoluciones/corn/workflows/integration/badge.svg?style=svg
    :target: https://github.com/baobabsoluciones/corn/actions

.. image:: https://img.shields.io/pypi/v/cornflow-client.svg?style=svg
   :target: https://pypi.python.org/pypi/cornflow-client

.. image:: https://img.shields.io/pypi/pyversions/cornflow-client.svg?style=svg
   :target: https://pypi.python.org/pypi/cornflow-client

.. image:: https://img.shields.io/badge/License-MIT-blue.svg?style=svg

Cornflow is open source multi-solver optimization server with a REST API built using `flask <https://flask.palletsprojects.com>`_, `airflow <https://airflow.apache.org/>`_ and `pulp <https://coin-or.github.io/pulp/>`_.

It supports generic MIP models via the pulp interface and thus connects to CPLEX, GUROBI, CBC, MOSEK, GLPK, XPRESS, MIPCL and others. In the future it will support a generic CP interface that will connect it to: ORTOOLS, CHOCO and CPO. Finally, it supports specific application "solvers" written in python (natively) or in any other language as long as they can be used from airflow.

The aim of this project is to simplify the deployment of optimization-based applications by handling the following tasks:

* storage of users, instances, solutions and logs.
* deployment and maintenance of models, solvers and algorithms.
* scheduling of executions in remote machines.
* centralizing of commercial licenses.


.. contents:: **Table of Contents**


Installation instructions
-------------------------


Requirements
~~~~~~~~~~~~~~~~~~

* Linux or Windows with WSL
* python >= 3.5
* postgresql

Install cornflow
~~~~~~~~~~~~~~~~~~

Cornflow consists of two projects: cornflow (itself) and airflow (from apache). They are conceived to be deployed independently. Here we will explain the "development deploy" that consists on installing them in the same machine.

Download the Cornflow project::

    git clone git@github.com:baobabsoluciones/corn.git
    cd corn
    python3 -m venv cfvenv
    cfvenv/bin/pip3 install -r requirements-dev.txt

activate the virtual environment::

    source cfvenv/bin/activate

or, in windows::

    cfvenv/Scripts/activate


Setup cornflow database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This local example assumes sqlite as database engine. For an example of postgresql deployment, see the next section.

Initialize the database::

    source cfvenv/bin/activate
    export FLASK_APP=cornflow.app
    export DATABASE_URL=sqlite:///cornflow.db
    python manage.py db upgrade
    python manage.py create_super_user  --user=airflow_test@admin.com --password=airflow_test_password

Launch cornflow server
~~~~~~~~~~~~~~~~~~~~~~~

Each time you run the flask server, execute the following::

    source cfvenv/bin/activate
    export FLASK_APP=cornflow.app
    export FLASK_ENV=development
    export DATABASE_URL=sqlite:///cornflow.db
    export SECRET_KEY=THISNEEDSTOBECHANGED
    export AIRFLOW_URL=http://localhost:8080
    export AIRFLOW_USER=admin
    export AIRFLOW_PWD=admin
    flask run

In windows use ``set`` instead of ``export``.

Install and configure airflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here are the minimal instructions to install and configure airflow with the default dags in this project. The instructions assume Ubuntu.

Create a virtual environment for airflow::

    cd corn
    python3 -m venv afvenv
    source afvenv/bin/activate

Install airflow from pip::

    AIRFLOW_VERSION=2.0.1
    PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
    CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
    pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"

Install the default workers dependencies::

    pip install orloge cornflow_client pulp

Initialize the database and create an admin user::

    export AIRFLOW_HOME="$PWD/airflow_config"
    airflow db init
    airflow users create \
          --username admin \
          --firstname admin \
          --lastname admin \
          --role Admin \
          --password admin \
          --email admin@example.org

Launch airflow server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set the base config::

    source afvenv/bin/activate
    export AIRFLOW_HOME="$PWD/airflow_config"
    export AIRFLOW__CORE__LOAD_EXAMPLES=0
    export AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=0
    export AIRFLOW__API__AUTH_BACKEND=airflow.api.auth.backend.basic_auth
    export AIRFLOW__WEBSERVER__SECRET_KEY=e9adafa751fd35adfc1fdd3285019be15eea0758f76e38e1e37a1154fb36
    export AIRFLOW_CONN_CF_URI=http://airflow_test@admin.com:airflow_test_password@localhost:5000

Start the web server::

    airflow webserver -p 8080 &

Also, start the scheduler::

    airflow scheduler &

airflow gui will be at::

    http://localhost:8080

Using cornflow with the python client
---------------------------------------

Launch airflow (webserver and scheduler) and cornflow server (see sections above).

We're going to test the cornflow server by using the `cornflow-client` and the `pulp` python package::

    pip install cornflow-client pulp

A complete example is shown in `examples/basic_functions.py`. Below is an extract.

Initialize the api client::

    from cornflow_client import CornFlow
    email = 'some_email@gmail.com'
    pwd = 'some_password'
    name = 'some_name'
    client = CornFlow(url="http://127.0.0.1:5000")

Create a user::

    config = dict(email=email, pwd=pwd, name=name)
    client.sign_up(**config)

log in::

    client.login(email, pwd)

Prepare an instance::

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
    insName = 'test_export_dict_MIP'
    description = 'very small example'

Send instance::

    instance = client.create_instance(data, name=insName, description=description)

Solve an instance::

    config = dict(
        solver = "PULP_CBC_CMD",
        timeLimit = 10
    )
    execution = client.create_execution(
        instance['id'], config, name='execution1', description='execution of a very small instance'
    )

Check the status of an execution::

    status = client.get_solution(execution['id'])
    print(status['state'])
    # 1 means "finished correctly"

Retrieve a solution::

    results = client.get_solution(execution['id'])
    print(results['data'])
    # returns a json with the solved pulp object
    _vars, prob = pulp.LpProblem.from_dict(results['data'])

Retrieve the log of the solver::

    log = client.get_log(execution['id'])
    print(log['log'])
    # json format of the solver log

Other deployment options
--------------------------

Deploying with docker-compose
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The docker-compose.yml file write in version '3' of the syntax describes the build of four docker containers::

    app python3 cornflow service
    airflow service based on puckel/docker-airflow image
    cornflow postgres database service
    airflow postgres database service

Create containers::

    docker-compose up --build -d
	
List containers::

    docker-compose ps

Interact with container::

    docker exec -it CONTAINER_ID bash

See the logs for a particular service (e.g., SERVICE=cornflow)::

    docker-compose logs SERVICE

Stop the containers::
    
    docker-compose down
	
destroy all container and images (be careful! this destroys all docker images of non running container)::

    docker system prune -af

Appended in this repository are three more docker-compose files for different kind of deployment::
	
    Use "docker-compose -f docker-compose-cornflow-celery.yml up -d" for deploy cornflow with airflow celery executor and one worker. If a larger number of workers are required, use --scale parameter of docker-compose.

    Use "docker-compose -f docker-compose-cornflow-separate.yml up -d" for deploy cornflow and postgres without the airflow platform. Please, replace "airflowurl" string inside with your airflow address.

    Use "docker-compose -f docker-compose-airflow-celery-separate.yml up -d" for deploy just the airflow celery executor and two workers.

Running airflow with reverse proxy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cornflow does not have any reverse proxy configuration like airflow does. Just redirect all http request to cornflow port.
Eg.::

    [Nginx]
    server {
    listen 80;
    server_name localhost;
    location / {
      proxy_pass http://localhost:5000;
	}

If you want to run the solution with reverse proxy like Nginx, Amazon ELB or GCP Cloud Balancer, just make changes on airflow.cfg through environment variables::
	
	[webserver]
	AIRFLOW__WEBSERVER__BASE_URL=http://my_host/myorg/airflow
    AIRFLOW__WEBSERVER__ENABLE_PROXY_FIX=True
	[flower]
	AIRFLOW__CELERY__FLOWER_URL_PREFIX=/myorg/flower

More information in airflow doc page https://airflow.apache.org/docs/apache-airflow/stable/howto/run-behind-proxy.html

Setup cornflow database with PostgreSQL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You now need to create a user and password in postgresql (we will be using `postgres` and `postgresadmin`). And also you need to create a database (we will be using one with the name `cornflow`).

Create a new user::

    sudo -u postgres psql

Edit the password for the user ``postgres``::

    ALTER USER postgres PASSWORD 'postgresadmin';
    \q

Create a new database::

    sudo su - postgres
    psql -c "create database cornflow"
    exit

Finally, the environment variable needs to be changed::

    export DATABASE_URL=postgres://postgres:postgresadmin@127.0.0.1:5432/cornflow

**Possible error with psycopg2:**

The installation of the psycopg2 may generate an error because it does not find the pg_config file.

One way to solve this problem is to previously install libpq-dev which installs pg_config::

    sudo apt install libpq-dev

Running tests and coverage
------------------------------

Then you have to run the following commands::

    export FLASK_ENV=testing

Finally you can run all the tests with the following command::

    python -m unittest discover -s cornflow.tests

If you want to only run the unit tests (without a local airflow webserver)::

    python -m unittest discover -s cornflow.tests.unit

If you want to only run the integration test with a local airflow webserver::

    python -m unittest discover -s cornflow.tests.integration

After if you want to check the coverage report you need to run::

    coverage run  --source=./cornflow/ -m unittest discover -s=./cornflow/tests/
    coverage report -m

or to get the html reports::

    coverage html
