Cornflow-dags
===============

Private DAGs for cornflow server

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

    AIRFLOW_VERSION=2.0.1
    PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
    CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
    pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"

If in development, some additional packages are needed for the workers::

    pip install -r requirements.txt

We now initialize the database and create an admin user::

    export AIRFLOW_HOME="$PWD"
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
    cd airflow
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
    export AIRFLOW__SCHEDULER__CATCHUP_BY_DEFAULT=0
    export AIRFLOW__CORE__LOAD_EXAMPLES=0
    export AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=0
    export AIRFLOW__API__AUTH_BACKEND=airflow.api.auth.backend.basic_auth
    export AIRFLOW__WEBSERVER__SECRET_KEY=e9adafa751fd35adfc1fdd3285019be15eea0758f76e38e1e37a1154fb36
    export AIRFLOW_CONN_CF_URI=cornflow://airflow_test@admin.com:airflow_test_password@localhost:5000
    export AIRFLOW_HOME="$PWD/airflow_config"
    export AIRFLOW_HOME="$PWD"
    export AIRFLOW__CORE__DAGS_FOLDER="$AIRFLOW_HOME/DAG"

Start the web server::

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

If you're feeling lucky::

    kill -9 $(ps aux | grep 'airflow' | awk '{print $2}')


Uploading a new app / solver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are three things that are needed when submitting a new solver.

1. the solver itself.
2. the instance (input) schema.
3. the solution (output) schema.

In the following lines we will explain each of these three concepts while using the hackathon example dag.

The solver
------------

The solver comes in the form of a dag file with some additional "constraints" or rules.

Basically, the **happy flow** of the dag should have three main parts:

1. Call cornflow to get the input data (instance) for the execution.
2. Produce a solution from that input data.
3. Call cornflow to update the execution with the results.

This is exemplified in the `cf_solve` function in the `utils.py` file::

    def cf_solve(fun, solution_schema, **kwargs):
        # 1. get data from Cornflow
        exec_id = get_arg("exec_id", kwargs)
        airflow_user, data, config = cf_get_data(kwargs = kwargs)
        # 2. produce a solution
        solution, log = fun(data, **config)
        if solution:
            payload = dict(execution_results = solution, log_text=log, solution_schema = solution_schema, state = 1)
        else:
            payload = dict(state = 1, log_text=log, solution_schema = solution_schema)

        # 3. Send the solution to cornflow.
        message = airflow_user.put_api_for_id('dag/', id=exec_id, payload=payload)

        if solution:
            return "Solution saved"

The first point is achieved by using the `execution_id` passed through the configuration to the dag. This id will be used to make a call to the cornflow server and retrieve the input data and solve configuration.

The second point consists of a function that uses that data to generate a model / algorithm that returns the solution.

The third part will be a call to the cornflow server uploading a solution (if any is available).

In anything goes wrong, the dag still needs to report to cornflow to tell it it's finished incorrectly.

In the case of the hackathon2020, the dag file is named: `hk_2020_dag.py`

The input schema and output schema
-----------------------------------------

Both schemas are built and deployed similarly so we present how the input schema is done.

The input schema is a json schema file (https://json-schema.org/) that includes all the characteristics of the input data for this dag. This file can be built with many tools (a regular text editor could be enough). We will detail how to do this later.

The input schema is stored in the Variables storage of Airflow. In order to upload it, only one option is currently supported: put the json file with the name of the dag (**NOT the dag-file name!**) followed by `_input.json` in the `DAG` directory. In the future, it would be possible to re-use a json schema by editing the `update_all_schemas.py` dag.

Once uploaded, these schemas will be accessible to cornflow and will be used to validate input data and solutions for this dag.

In the case of the hackathon2020, the schemas are named: `hk_2020_dag_input.json` and `hk_2020_dag_output.json`
