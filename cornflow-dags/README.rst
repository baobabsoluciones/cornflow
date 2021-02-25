Cornflow-dags
===============

Private DAGs for cornflow server

Install and configure airflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The instructions assume Ubuntu. For windows see below.

In Ubuntu
------------

Create a virtual environment for airflow::

    cd cornflow-dags
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
    export AIRFLOW_CONN_CF_URI=http://airflow_test@admin.com:airflow_test_password@localhost:5000/
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

    AIRFLOW_VERSION=2.0.1
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

There are several things that are needed when submitting a new solver.

1. a `solve` function.
2. a `name` string.
3. an `instance` dictionary.
4. an `solution` dictionary.
5. (optional) a `test_cases` function that returns a list of dictionaries.

In its most minimalistic form: an app constitutes one dag file that contains all of this.
In the following lines we will explain each of these concepts while using the hackathon example dag.

The solver
------------

The solver comes in the form of a python function that takes exactly two arguments: `data` and `config`. The first one is a dictionary with the input data (Instance) to solve the problem. The second one is also a dictionary with the execution configuration.

This function needs to be named `solve` and returns three things: a dictionary with the output data (Solution), a string that stores the whole log, and a dictionary with the log information processed.

The function for the hackathon case is::

    from hackathonbaobab2020 import get_solver, Instance
    from utils import NoSolverException
    from timeit import default_timer as timer

    def solve(data, config):
        """
        :param data: json for the problem
        :param config: execution configuration, including solver
        :return: solution and log
        """
        print("Solving the model")
        solver = config.get('solver')
        solver_class = get_solver(name=solver)
        if solver_class is None:
            raise NoSolverException("Solver {} is not available".format(solver))
        inst = Instance.from_dict(data)
        algo = solver_class(inst)
        start = timer()
        try:
            status = algo.solve(config)
            print("ok")
        except Exception as e:
            print("problem was not solved")
            print(e)
            status = 0

        if status != 0:
            # export everything:
            status_conv = {4: "Optimal", 2: "Feasible", 3: "Infeasible", 0: "Unknown"}
            log = dict(time=timer() - start, solver=solver, status=status_conv.get(status, "Unknown"))
            sol = algo.solution.to_dict()
        else:
            log = dict()
            sol = {}
        return sol, "", log

This function is then wrapped inside another function that handles getting the information from cornflow, the solution validation and the writing of the solution. And finally, this function is wrapped inside the DAG creation.

In the case of the hackathon this is done here::

    from airflow import DAG
    from airflow.operators.python import PythonOperator

    default_args = {
        'owner': 'baobab',
        'depends_on_past': False,
        'start_date': datetime(2020, 2, 1),
        'email': [''],
        'email_on_failure': False,
        'email_on_retry': False,
        'retry_delay': timedelta(minutes=1),
        'schedule_interval': None
    }

    from utils import cf_solve
    dag_name = 'hk_2020_dag'
    def solve_hk(**kwargs):
        return cf_solve(solve_from_dict, dag_name, **kwargs)

    hackathon_task = PythonOperator(
        task_id='hk_2020_task',
        python_callable=solve_hk,
        dag=dag
    )

Name
-----

Just put a name and use it inside the DAG generation. The name *needs* to be defined as a separate variable!

In the hackathon we have::

    name = 'hk_2020_dag'
    dag = DAG(name, default_args=default_args, schedule_interval=None)


The input schema and output schema
-----------------------------------------

Both schemas are built and deployed similarly so we present how the input schema is done.

The input schema is a json schema file (https://json-schema.org/) that includes all the characteristics of the input data for each dag. This file can be built with many tools (a regular text editor could be enough). We will detail how to do this later.

The input schema is stored in the Variables storage of Airflow. In order to upload it: you need to have an `instance` variable available in your dag file.

In the case of the hackathon, these variables are imported from the package::

    from hackathonbaobab2020.schemas import instance, solution

Once uploaded, these schemas will be accessible to cornflow and will be used to validate input data and solutions for this dag.

Test cases
------------

This function is used in the unittests to be sure the solver works as intended. In the hackathon example we take the examples from the package::

    def test_cases():
        options = [('j10.mm.zip', 'j102_4.mm'), ('j10.mm.zip', 'j102_5.mm'), ('j10.mm.zip', 'j102_6.mm')]
        return [get_test_instance(*op).to_dict() for op in options]
