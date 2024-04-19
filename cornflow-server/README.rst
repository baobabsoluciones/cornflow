cornflow
=========

.. image:: https://github.com/baobabsoluciones/cornflow/workflows/build/badge.svg?style=svg
    :target: https://github.com/baobabsoluciones/cornflow/actions

.. image:: https://github.com/baobabsoluciones/cornflow/workflows/docs/badge.svg?style=svg
    :target: https://github.com/baobabsoluciones/cornflow/actions

.. image:: https://github.com/baobabsoluciones/cornflow/workflows/integration/badge.svg?style=svg
    :target: https://github.com/baobabsoluciones/cornflow/actions

.. image:: https://img.shields.io/pypi/v/cornflow-client.svg?style=svg
   :target: https://pypi.python.org/pypi/cornflow-client

.. image:: https://img.shields.io/pypi/pyversions/cornflow-client.svg?style=svg
   :target: https://pypi.python.org/pypi/cornflow-client

.. image:: https://img.shields.io/badge/License-Apache2.0-blue

cornflow is an open source multi-solver optimization server with a REST API built using `flask <https://flask.palletsprojects.com>`_, `airflow <https://airflow.apache.org/>`_ and `pulp <https://coin-or.github.io/pulp/>`_.

While most deployment servers are based on the solving technique (MIP, CP, NLP, etc.), cornflow focuses on the optimization problems themselves. However, it does not impose any constraint on the type of problem and solution method to use.

With cornflow you can deploy a Traveling Salesman Problem solver next to a Knapsack solver or a Nurse Rostering Problem solver. As long as you describe the input and output data, you can upload any solution method for any problem and then use it with any data you want.

cornflow helps you formalize your problem by proposing development guidelines. It also provides a range of functionalities around your deployed solution method, namely:

* storage of users, instances, solutions and solution logs.
* deployment and maintenance of models, solvers and algorithms.
* scheduling of executions in remote machines.
* management of said executions: start, monitor, interrupt.
* centralizing of commercial licenses.
* scenario storage and comparison.
* user management, roles and groups.


.. contents:: **Table of Contents**

Installation instructions
-------------------------------

cornflow is tested with Ubuntu 20.04, python >= 3.8 and git.

Download the cornflow project and install requirements::

    python3 -m venv venv
    venv/bin/pip3 install cornflow

initialize the sqlite database::

    source venv/bin/activate
    export FLASK_APP=cornflow.app
    export DATABASE_URL=sqlite:///cornflow.db
    flask db upgrade
    flask access_init
    flask create_service_user  -u airflow -e airflow_test@admin.com -p airflow_test_password
    flask create_admin_user  -u cornflow -e cornflow_admin@admin.com -p cornflow_admin_password


activate the virtual environment and run cornflow::

    source venv/bin/activate
    export FLASK_APP=cornflow.app
    export SECRET_KEY=THISNEEDSTOBECHANGED
    export DATABASE_URL=sqlite:///cornflow.db
    export AIRFLOW_URL=http://127.0.0.1:8080/
    export AIRFLOW_USER=airflow_user
    export AIRFLOW_PWD=airflow_pwd
    flask run

**cornflow needs a running installation of Airflow to operate and more configuration**. Check `the installation docs <https://baobabsoluciones.github.io/cornflow/main/install.html>`_ for more details on installing airflow, configuring the application and initializing the database.

Using cornflow to solve a PuLP model
---------------------------------------

We're going to test the cornflow server by using the `cornflow-client` and the `pulp` python package::

    pip install cornflow-client pulp

Initialize the api client::

    from cornflow_client import CornFlow
    email = 'some_email@gmail.com'
    pwd = 'Some_password1'
    username = 'some_name'
    client = CornFlow(url="http://127.0.0.1:5000")

Create a user::

    config = dict(username=username, email=email, pwd=pwd)
    client.sign_up(**config)

Log in::

    client.login(username=username, pwd=pwd)

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

    instance = client.create_instance(data, name=insName, description=description, schema="solve_model_dag",)

Solve an instance::

    config = dict(
        solver = "PULP_CBC_CMD",
        timeLimit = 10
    )
    execution = client.create_execution(
        instance['id'], config, name='execution1', description='execution of a very small instance',
        schema="solve_model_dag",
    )

Check the status of an execution::

    status = client.get_status(execution["id"])
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

Using cornflow to deploy a solution method
---------------------------------------------

To deploy a cornflow solution method, the following tasks need to be accomplished:

#. Create an Application for the new problem
#. Do a PR to a compatible repo linked to a server instance (e.g., like `this one <https://github.com/baobabsoluciones/cornflow>`_).

For more details on each part, check the `deployment guide <https://baobabsoluciones.github.io/cornflow/guides/deploy_solver.html>`_.

Using cornflow to solve a problem
-------------------------------------------

For this example we only need the cornflow_client package. We will test the graph-coloring demo defined `here <https://github.com/baobabsoluciones/cornflow-dags-public/tree/main/DAG/graph_coloring>`_. We will use the test server to solve it.

Initialize the api client::

    from cornflow_client import CornFlow
    email = 'readme@gmail.com'
    pwd = 'some_password'
    username = 'some_name'
    client = CornFlow(url="https://devsm.cornflow.baobabsoluciones.app/")
    client.login(username=username, pwd=pwd)

solve a graph coloring problem and get the solution::

    data = dict(pairs=[dict(n1=0, n2=1), dict(n1=1, n2=2), dict(n1=1, n2=3)])
    instance = client.create_instance(data, name='gc_4_1', description='very small gc problem', schema="graph_coloring")
    config = dict()
    execution = client.create_execution(
        instance['id'], config, name='gc_4_1_exec', description='execution of very small gc problem',
        schema="graph_coloring",
    )
    status = client.get_status(execution["id"])
    print(status['state'])
    solution = client.get_solution(execution["id"])
    print(solution['data']['assignment'])


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

