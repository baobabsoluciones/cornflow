Installation instructions
====================================

Requirements
~~~~~~~~~~~~~~~~~~

* Linux or Windows with WSL.
* python >= 3.8, preferably 3.10.

Install cornflow
~~~~~~~~~~~~~~~~~~

There are several ways to install cornflow and set it up and running. First we are going to cover how to set up cornflow and airflow locally on a Linux machine. Then how to deploy cornflow building the docker containers and how to set it up using the official docker hub images.

Local installation from repository
-----------------------------------

Set up cornflow
^^^^^^^^^^^^^^^^

We first start by cloning the repository::

  git clone https://github.com/baobabsoluciones/cornflow

Then we create a virtual environment and install all the requirements::

  cd cornflow
  cd cornflow-server
  python3 -m venv cenv
  source cenv/bin/activate
  pip install -r requirements-dev.txt

Before running cornflow we have to create some environment variables::

  export FLASK_APP=cornflow.app
  export FLASK_ENV=development
  export SECRET_KEY=THISNEEDSTOBECHANGED
  export AIRFLOW_URL=http://localhost:8080
  export AIRFLOW_USER=admin
  export AIRFLOW_PWD=admin

Then we run the following commands::

  flask db upgrade -d cornflow/migrations
  flask access_init
  flask creare_admin_user -u admin -e admin@cornflow.org -p Adminpassword1!
  flask create_service_user -u service_user -e service_user@cornflow.org -p Service_password1
  flask run

And this should let us have a cornflow server on development mode running on http://localhost:5000. If we want to run it on the background we can use::

  flask run &

And to stop it we can find the process id and kill it::

  ps aux | grep flask
  kill -9 <process_id>

We should kill the process and set up and run airflow before coming back to launch cornflow.

Set up and run airflow
^^^^^^^^^^^^^^^^^^^^^^^^

First if we have followed cornflow installation instructions we should exit the virtual environment first and go back to the root folder::

  deactivate
  cd ..

Then we move the default DAGs that we have in the repo to the correct folder::

  cp -r cornflow-dags/DAG/* cornflow-server/airflow_config/dags/
  cp cornflow-dags/requirements.txt cornflow-server/airflow_config/
  cd cornflow-server

Now we create a virtual environment and install all the requirements::

  python3 -m venv aenv
  source aenv/bin/activate
  AIRFLOW_VERSION=2.7.1
  PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
  CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
  pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
  pip install orloge pulp
  pip install -r airflow_config/requirements.txt
  pip install -e ../libs/client
  pip install apache-airflow-providers-google
  airflow db init
  airflow users create -u admin -p admin -f admin -l user -r Admin -e admin@airflow.org
  
Then we export the variables that we need to run airflow::

  export AIRFLOW__CORE__LOAD_EXAMPLES=0
  export AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=0
  export AIRFLOW__API__AUTH_BACKEND=airflow.api.auth.backend.basic_auth
  export AIRFLOW__WEBSERVER__SECRET_KEY=e9adafa751fd35adfc1fdd3285019be15eea0758f76e38e1e37a1154fb36
  export AIRFLOW_CONN_CF_URI=http://service_user:Service_password1@localhost:5000
  airflow webserver -p 8080 &
  airflow scheduler &

And to stop the services we can::

  ps aux | grep airflow
  kill -9 <process_id>

Run cornflow
^^^^^^^^^^^^^^^^

Once airflow is running and cornflow set up we can run it::
  
    source cenv/bin/activate
    flask register_deployed_dags -r http://127.0.0.1:8080 -u admin -p admin
    flask register_dag_permissions -o 1
    flask run -p 5000 &

And with this we should have both cornflow and airflow running. We can check that cornflow is running by going to http://localhost:5000/health/ and airflow by going to http://localhost:8080.

Local installation as a package
--------------------------------


Docker installation
--------------------

asdasdas

Docker hub installation
------------------------

asdasdas


Troubleshooting
----------------

To install all the dependencies, additional packages may be needed. For example, in Ubuntu 20.04, the following packages are needed::

  sudo apt-get install libpq-dev python3-dev python3.10-venv build-essential