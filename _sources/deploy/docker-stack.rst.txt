Docker stack
------------------

Image build
**************

The Dockerfile in `cornflow github project <https://github.com/baobabsoluciones/corn>`_ is builded from python3-slim-buster docker image.
Installation path of cornflow app is ``/usr/src/app``.
There is no docker volumes attached to deployment for cornflow app.

You can customize certain environment variables after building the image. To build the image in a custom way, run the command::

    docker build . --tag my-image:my-tag 

Where my-image is the name you want to name it and my-tag is the tag you want to tag the image with.

Official image build
***********************

The cornflow image is built from the Dockerfile file hosted in the official repository. The image is built from the new changes on the main development branch, creating an image with the label "latest"::

    docker pull baobabsoluciones/cornflow:latest

Environment variables
************************

Main cornflow environment variables::

    CORNFLOW_ADMIN_USER - cornflow root admin user
    CORNFLOW_ADMIN_PWD - cornflow root admin pwd
    CORNFLOW_SERVICE_USER - cornflow service user name
    CORNFLOW_SERVICE_PWD - cornflow service user password
    AIRFLOW_USER - airflow admin user
    AIRFLOW_PWD - airflow admin pwd
    AIRFLOW_URL - airflow url service
    CORNFLOW_URL - cornflow url service 
    CORNFLOW_DB_CONN - postgresql connection for cornflow database
    SECRET_KEY - encrypted key like fernet for keep data safe
    FLASK_APP - python3 cornflow app (cornflow.app) 
    FLASK_ENV - cornflow deployment environment

Entrypoint
*************

If you are using the default entrypoint of the production image, it will execute the ``initapp.sh`` script which uses and initializes environment variables to work with postgresql and airflow defined in ``docker-compose.yml``.
The image entrypoint works as follows:

#. A new fernet secret key will be generated.
#. Check cornflow postgresql database connection.
#. The migrations and upgrade of the database is executed on every deployment.
#. For the very first time it will create the cornflow superuser.
#. Finally launch gunicorn server with 3 gevent workers.

Airflow personalized image
******************************************

For this project we have created a custom Airflow image that we will maintain for the life cycle of the Cornflow application.
The airflow personalized image is built from the Dockerfile file hosted in the official cornflow repository. The image is built from the new changes on the main development branch, creating an image with the label "latest"::

    docker pull baobabsoluciones/docker-airflow:latest

Airflow has different execution modes: ``SecuentialExecutor``, ``CeleryExecutor`` and ``KubernetesExecutor``. At the moment we have focused on the first two execution modes and next we will develop an image to be used with Kubernetes.
The default executor is set to ``SequentialExecutor``, which allows you to perform executions sequentially. That is, when you start an execution, the next one is not executed until the previous one has finished. For more information on the ``CeleryExecutor``, go to the next section: :ref:`Running with simultaneous resolutions`.

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
    airflow_config/requirements.txt:/requirements.txt - development packages required to install inside workers.

These volumes allow you to persist the DAG files and also link the development packages necessary for their execution.

PostgreSQL docker image
***************************

The image displayed in the container will be the official image of the popular `PostgreSQL <https://hub.docker.com/_/postgres>`_ database engine.
The postgresql environment variables included in ``docker-compose.yml`` are::

    POSTGRES_USER - database username of service 
    POSTGRES_PASSWORD - database user´s password of service 
    POSTGRES_DB - database name of service
   
The postgresql deployment requires mounting one volume linked to the directory created on the host::

    postgres_cf_data:/var/lib/postgresql/data/ - This volume stores the database files
