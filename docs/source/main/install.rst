Installation instructions
====================================

Requirements
~~~~~~~~~~~~~~~~~~

* Linux or Windows with WSL
* python >= 3.5

Install cornflow
~~~~~~~~~~~~~~~~~~

Cornflow consists of two projects: cornflow (itself) and airflow (from apache). They are conceived to be deployed independently. Here we will explain the "development deploy" that consists on installing them in the same machine.

Download the Cornflow project::

    git clone git@github.com:baobabsoluciones/cornflow-server.git
    cd corn
    python3 -m venv cfvenv
    cfvenv/bin/pip3 install -r requirements-dev.txt

activate the virtual environment::

    source cfvenv/bin/activate

or, in windows::

    cfvenv/Scripts/activate


Setup cornflow database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This local example assumes sqlite as database engine. For an example of postgresql deployment, see the :ref:`this section<Setup cornflow database with your own PostgreSQL server>`.

Initialize the database::

    source cfvenv/bin/activate
    export FLASK_APP=cornflow.app
    export DATABASE_URL=sqlite:///cornflow.db
    python manage.py db upgrade
    python manage.py access_init
    python manage.py create_service_user  --username=airflow --email=airflow_test@admin.com --password=airflow_test_password
    python manage.py create_admin_user  --username=cornflow --email=cornflow_admin@admin.com --password=cornflow_admin_password

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

    AIRFLOW_VERSION=2.1.0
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



Install with docker
=======================

Pull
~~~~~~~~

Pull the image from the Docker repository.

    docker pull baobabsoluciones/cornflow

Build
~~~~~~~~~~

Build cornflow image::

    docker build -t cornflow .

Optionally install Airflow personalized image in folder `airflow_config` ::

    cd airflow_config && docker build -t docker-airflow .

Don't forget to update the images in the docker-compose files to baobabsoluciones/cornflow:latest and baobabsoluciones/docker-airflow:latest.

Usage
~~~~~~~~~~

We have created several `docker-compose.yml` files so that you can use them and deploy the test environment:
By default, docker-airflow runs Airflow with SequentialExecutor::

    docker-compose up --build -d
    
For CeleryExecutor::

    docker-compose -f docker-compose-cornflow-celery.yml up -d

List containers::

    docker-compose ps

Interact with container::

    docker exec -it `docker ps -q --filter ancestor=baobabsoluciones/cornflow` bash

See the logs for a particular service (e.g., SERVICE=cornflow)::

    docker-compose logs `docker ps -q --filter ancestor=baobabsoluciones/cornflow`

Stop the containers and clean volumes::
    
    docker-compose down --volumes --rmi all

Help me
----------

If you have a database server and you only want to create the database or, for example, you already have an airflow environment, you can go to the following links to learn more about other types of cornflow deployment.

:ref:`Deploy cornflow with docker<Deploy your own Cornflow-server>`

`Airflow documentation <https://airflow.apache.org/docs/apache-airflow/2.1.0/index.html>`_

