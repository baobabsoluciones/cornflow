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
  flask create_admin_user -u admin -e admin@cornflow.org -p Adminpassword1!
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
  export AIRFLOW_HOME=./airflow_config/
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


Docker. Build images from local
--------------------------------

More information about how to deploy with docker containers can be found of the :ref:`deploy-cornflow` section of the documentation.

We first start by cloning the repository::

  git clone https://github.com/baobabsoluciones/cornflow

To continue the deployment we are going to need the Dockerfiles and docker-compose files that are on the repository. To be able to build from the source code we are going to need to do some small modifications to some of the files.

The Dockerfile for cornflow can be found inside the ``cornflow/cornflow-server`` folder and can be used as is, as this is the Dockerfile used to build the original image on docker hub.

The Dockerfile for airflow can be found on the ``cornflow/cornflow-server/airflow_config`` folder and can be used as is, as this is the Dockerfile used to build the original image on docker hub. This image is built on top of another one that gets built manually and that has all the needed libraries for the solvers. This is done this way to improve the build time of the image as the solver libraries are quite heavy and quite prone to remain stable for long periods of time.

Then we need a docker-compose file. The ``docker-compose.yml`` or ``docker-compose-cornflow-celery.yml`` that are in the root folder of the repository can be used with some small tweaks to build the images from the local repo instead that taking the official images.

To test out the simpler deployment we are going to use the ``docker-compose.yml`` file. We have to do the following changes. Comment the following lines:

.. code-block:: yaml
  
  image: baobabsoluciones/airflow:release-v1.0.8

and:

.. code-block:: yaml

  image: baobabsoluciones/cornflow:release-v1.0.8

In both cases the version of the image can be updated, but these lines are the ones that have to be commented in order to build the iamges from surce instead of downloading them from docker hub.

And uncomment the following lines:

.. code-block:: yaml

  build: 
    context: ./cornflow-server/airflow_config

and:

.. code-block:: yaml

  build: 
    context: ./cornflow-server

Then we can run the following commands to start up the containers::

  cp -r cornflow/cornflow-dags/DAG/* cornflow/cornflow-server/airflow_config/dags/
  cp cornflow/cornflow-dags/requirements.txt cornflow/cornflow-server/airflow_config/
  docker-compose up -d

Then to stop the containers we can run::

  docker-compose down --remove-orphans

And to delete the containers in case we want to rebuild them after stopping them::

  docker system prune -af

And with these command we should have a cornflow and airflow instance up and running on our machine with the default variables that can be seen on the docker-compose file.

If we want to have the full ecosystem to test out the celery backend, then we have to run the ``docker-compose-cornflow-celery.yml`` file instead of the ``docker-compose.yml`` file. This will start up a redis instance and a celery worker that will be used by airflow to run the DAGs. 

The lines that have to be modified on this file are the same ones that the one on the ``docker-compose.yml`` file.

To start it up then we can run::

  docker-compose -f docker-compose-cornflow-celery.yml up -d


Docker. Pull images from docker hub
------------------------------------

To run the environment with the official images then we just have to copy the ``docker-compose.yml`` or ``docker-compose-cornflow-celery.yml`` file to our system and run the docker-compose up command to use the official docker hub images.

Troubleshooting
----------------

To install all the dependencies, additional packages may be needed. For example, in Ubuntu 20.04, the following packages are needed::

  sudo apt-get install libpq-dev python3-dev python3.10-venv build-essential
