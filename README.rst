Cornflow
=========

An open source multi-solver optimization server with a REST API.

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

**Possible error with psycopg2:**

The installation of the psycopg2 may generate an error because it does not find the pg_config file.

One way to solve this problem is to previously install libpq-dev which install pg_config::

    sudo apt install libpq-dev

Setup cornflow database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Initialize the database::

    source cfvenv/bin/activate
    export FLASK_APP=cornflow.app
    export DATABASE_URL=postgres://postgres:postgresadmin@127.0.0.1:5432/cornflow
    python manage.py db upgrade
    python manage.py create_super_user

Starting flask server
~~~~~~~~~~~~~~~~~~~~~~~

Each time you run the flask server, execute the following::

    source cfvenv/bin/activate
    export FLASK_APP=cornflow.app
    export FLASK_ENV=development
    export DATABASE_URL=postgres://postgres:postgresadmin@127.0.0.1:5432/cornflow
    export SECRET_KEY=THISNEEDSTOBECHANGED
    export AIRFLOW_URL=http://localhost:8080
    export CORNFLOW_URL=http://localhost:5000
    export AIRFLOW_USER=admin
    export AIRFLOW_PWD=admin
    flask run

In windows use ``set`` instead of ``export``.

Install and configure airflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The instructions assume Ubuntu. For windows see below.

In Ubuntu
------------

Create a virtual environment for airflow::

    cd corn
    python3 -m venv afvenv
    source afvenv/bin/activate

Then we install it with pip::

    AIRFLOW_VERSION=2.0.0
    PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
    CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
    pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"

If in development, some additional packages are needed for the workers::

    pip install orloge cornflow_client pulp

We now initialize the database and create an admin user::

    export AIRFLOW_HOME="$PWD/airflow_config"
    airflow db init
    airflow users create \
          --username admin \
          --firstname admin \
          --lastname admin \
          --role Admin \
          --password admin \
          --email admin@example.org

On Windows
------------

For windows, Windows subsystem for Linux (WSL) is used.

Download and install WSL:

- Install Linux subsystems for linux (https://docs.microsoft.com/es-es/windows/wsl/install-win10).
- Install Ubuntu 20.04 from windows store.
- Open the Ubuntu 20.04 terminal.

Then, we will list the changes to the Ubuntu installing sequence.

Update and install some basic tools that help building python packages::

    sudo apt install -y build-essential libssl-dev libffi-dev python3-dev

Creation of airflow directory::

    cd
    mkdir airflow
    python3 -m venv afvenv
    source afvenv/bin/activate

Then, install airflow and the development dependencies just as in Ubuntu::

    see above!

Copy the dags from the original repository::

    mkdir airflow_config
    cp -R /mnt/c/PATH_TO_CORNFLOW_PROJECT/airflow_config/dags airflow_config/dags
    chmod -R 775 airflow_config

Finally, initialize the database in the same way::

    see above!

Launch airflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We start the web server, default port is 8080.

To set the base config and start the web server::

    source afvenv/bin/activate
    export AIRFLOW_HOME="$PWD/airflow_config"
    export AIRFLOW__CORE__LOAD_EXAMPLES=0
    export AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=0
    export AIRFLOW__API__AUTH_BACKEND=airflow.api.auth.backend.basic_auth
    export AIRFLOW__WEBSERVER__SECRET_KEY=e9adafa751fd35adfc1fdd3285019be15eea0758f76e38e1e37a1154fb36
    airflow webserver -p 8080 &

Also, start the scheduler::

    airflow scheduler &

airflow gui will be at::

    http://localhost:8080

Deployment of airflow with PostgreSQL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For deployment with postgresql, some extra steps need to be done.

Install the postgres plugin for airflow, as well as the postgres python package::

    AIRFLOW_VERSION=2.0.0
    PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
    CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
    pip install "apache-airflow-postgres==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
    pip install psycopg2

In the case of windows WSL, the python package in the last line is::

    pip install psycopg2-binary

Create the `airflow` database in postgresql::

    sudo su - postgres
    psql -c "create database airflow"
    exit

Tell airflow where the database is, **before initializing it, and before launching it**::

    export AIRFLOW__CORE__SQL_ALCHEMY_CONN=postgres://postgres:postgresadmin@127.0.0.1:5432/airflow


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

Launch airflow (webserver and scheduler) and cornflow server.

In order to use the cornflow api, the `cornflow-client` python package is needed::

    pip install cornflow-client

A complete example is shown in `examples/basic_functions.py`. Below is an extract.
Then, the packages is used like so::

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

    instance_id = client.create_instance(data,
                                         name='test_export_dict_MIP',
                                         description='very small example')

Solve an instance::

    config = dict(
        solver = "PULP_CBC_CMD",
        timeLimit = 10
    )
    execution_id = client.create_execution(instance_id['id'], config,
                                           name='execution1',
                                           description='execution of a very small instance')

Retrieve a solution::

    results = client.get_results(execution_id['id'])


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

Inspect container::

    docker exec -it containerid bash

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


Test cornflow
~~~~~~~~~~~~~~~~~~

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

