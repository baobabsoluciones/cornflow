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

Killing airflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for the code of the process in Linux::

    ps aux | grep airflow

Kill it::

    kill -9 CODE

If you're feeling lucky::

    kill -9 $(ps aux | grep 'airflow' | awk '{print $2}')


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

Docker deployment for Cornflow App
------------------------------------

From the beginning of the project, we thought that the best way to offer a cornflow deployment would be through container technology. Following the agile methodology allows us to translate the development to any system in a precise and immutable way. We will continue to work to provide a kubernetes installation template and other code-infrastructure deployment methods.
In this repository you can find various templates for `docker-compose <https://docs.docker.com/compose/>`_ in which to test different types of deployment.

The ``docker-compose.yml`` describes the build of this services::

    cornflow application
    postgres service for cornflow internal database
    airflow webserver and scheduler service

Since to run cornflow it is essential to have the airflow application, the ``docker-compose.yml`` file includes a deployment of said platform.

**Before you begin**

Follow these steps to install the necessary tools:

1. Install `Docker Community Edition (CE) <https://docs.docker.com/engine/installation/>`_ on your workstation. Depending on the OS, you may need to configure your Docker instance to use 4.00 GB of memory for all containers to run properly. Please refer to the Resources section if using Docker for Windows or Docker for Mac for more information.
2. Install `Docker Compose <https://docs.docker.com/compose/install/>`_ and newer on your workstation.

Older versions of docker-compose do not support all features required by docker-compose.yml file, so double check that it meets the minimum version requirements.

**docker-compose.yml**

To deploy cornflow on Docker Compose, you should fetch docker-compose.yml::

    curl -LfO 'https://raw.githubusercontent.com/baobabsoluciones/corn/master/docker-compose.yml'

Before starting cornflow for the first time, You need to prepare your environment, i.e. create the necessary files, directories and initialize the database.
On Linux, the mounted volumes in container use the native Linux filesystem user/group permissions, so you have to make sure the container and host computer have matching file permissions::

    mkdir -p ./airflow_config/dags
    cp "yourpathtofilerequirements.txt" ./airflow_config/requirements.txt

**Running cornflow**

Now you can start all services::

    docker-compose up -d

Cornflow service available at http://localhost:5000
Airflow service available at http://localhost:8080

In the second terminal you can check the condition of the containers and make sure that no containers are in unhealthy condition::

    docker ps

**Stop and clean docker environment**

Stop the docker services and remove all volumes::

    docker-compose down --volumes --rmi all

Cornflow docker stack
~~~~~~~~~~~~~~~~~~~~~~~

**Image build**

The Dockerfile in `cornflow github project <https://github.com/baobabsoluciones/corn>`_ is builded from python3-slim-buster docker image.
Installation path of cornflow app is ``/usr/src/app``.
There is no docker volumes attached to deployment for cornflow app.

You can customize certain environment variables after building the image. To build the image in a custom way, run the command::

    docker build . --tag my-image:my-tag 

Where my-image is the name you want to name it and my-tag is the tag you want to tag the image with.

**Environment variables**

Main cornflow environment variables::

    ADMIN_USER - cornflow root admin user
    ADMIN_PWD - cornflow root admin pwd
    AIRFLOW_USER - airflow admin user
    AIRFLOW_PWD - airflow admin pwd
    AIRFLOW_URL - airflow url service
    CORNFLOW_URL - cornflow url service 
    CORNFLOW_DB_CONN - postgresql connection for cornflow database
    SECRET_KEY - encrypted key like fernet for keep data safe
    FLASK_APP - python3 cornflow app (cornflow.app) 
    FLASK_ENV - cornflow deployment environment

**Entrypoint**

If you are using the default entrypoint of the production image, it will execute ``initapp.sh`` script wich use and initialize environment variables to work with postgresql and airflow defined in ``docker-compose.yml``.
The image entrypoint works as follows::

    A new fernet secret key it will be generated.
    Check cornflow postgresql database connection.
    The migrations and upgrade of the database is executed on every deployment.
    For the very first time will create the cornflow superuser.
    Finally launch gunicorn server with 3 gevent workers.

**Airflow docker image**

For this project we have created a custom Ariflow image that we will maintain for the life cycle of the Cornflow application.
Airflow has different execution modes: `SecuentialExecutor`, `CeleryExecutor` and `KubernetesExecutor`. At the moment we have focused on the first two execution modes and next we will develop an image to be used with Kubernetes.
By default is set on ``SequentialExecutor`` which allows you to perform resolutions sequentially. That is, when you enter a resolution, the next one is not executed until the previous one has finished.

The airflow environment variables included in ``docker-compose.yml`` are::

    AIRFLOW_USER - airflow administrator´s username
    AIRFLOW_PWD - airflow administrator´s password
    AIRFLOW_DB_HOST - airflow postgresql server
    AIRFLOW_DB_PORT - airflow postgresql server port
    AIRFLOW_DB_USER - airflow database username
    AIRFLOW_DB_PASSWORD - airflow database password
    AIRFLOW_DB - airflow database name

The airflow deployment requires mounting two volumes linked to the directory created on the host::

    airflow_config/dags:/usr/local/airflow/dags - DAG folder inside of installation path.
    airflow_config/requirements.txt:/requirements.txt - development packages required to install.

These volumes allow you to persist the DAG files and also link the development packages necessary for their execution.

**PostgreSQL docker image**

The image displayed in the container will be the official image of the popular `PostgreSQL <https://hub.docker.com/_/postgres>`_ database engine.
The postgresql environment variables included in ``docker-compose.yml`` are::

    POSTGRES_USER - database username of service 
    POSTGRES_PASSWORD - database user´s password of service 
    POSTGRES_DB - database name of service
   
The postgresql deployment requires mounting one volume linked to the directory created on the host::

    postgres_cf_data:/var/lib/postgresql/data/ - This volume stores the database files

**Running cornflow with simultaneous resolutions**

For do this kind of deployment, you could use the template ``docker-compose-cornflow-celery.yml``.
Airflow service allow you to run with CeleryExecutor. For more information, see `Basic airflow architecture <https://airflow.apache.org/docs/apache-airflow/stable/concepts.html#architecture>`_.

For running with CeleryExecutor is::

    docker-compose up -f docker-compose-cornflow-celery.yml -d

The number of ``workers`` deployed depends on ``--scale`` argument. For example, if number of workers needed is 2::

    docker-compose up -f docker-compose-cornflow-celery.yml -d --scale worker=2

If you are running cornflow with multiple workers, there are additional services that must be provided in your deployment::

    airflow worker service
    airflow flower service
    redis message broker service

New environment variables must also be taken into account for services running in Celery mode::

    EXECUTOR - Airflow execution mode. You must enter as a value ``Celery``.
    FERNET_KEY - A fernet key is used to encrypt and decrypt tokens managed by aiflow. All airflow related services must have the same key value.

Flower service available at http://localhost:5555

Other deployment options
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Running airflow with reverse proxy**

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

**Setup cornflow database with PostgreSQL**

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
    
**Connect to your own airflow deployment**

Recommendations for production
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Recommended arguments customization**

**Enforce security**

**LDAP configuration**

**SSL**

Operations and logs
~~~~~~~~~~~~~~~~~~~~~

**Manage users**

**Service log**
    
    - Cornflow log
    
    - Airflow log
    
    - Solver log

Known problems
~~~~~~~~~~~~~~~~

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
