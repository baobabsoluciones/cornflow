Cornflow docker deployment
===============================

From the beginning of the project, we thought that the best way to offer a cornflow deployment would be through container technology. Following the agile methodology allows us to translate the development to any system in a precise and immutable way. We will continue to work to provide a kubernetes installation template and other code-infrastructure deployment methods.
In `this repository <https://github.com/baobabsoluciones/corn>`_ you can find various templates for `docker-compose <https://docs.docker.com/compose/>`_ in which to test different types of deployment.

The ``docker-compose.yml`` describes the build of this services:

#. cornflow application server
#. postgresql server for cornflow and airflow internal database
#. airflow webserver and scheduler server

.. _cornflow_docker_stack:

.. figure:: ./../_static/cornflow_docker_stack.png

   Since to run cornflow it is essential to have the airflow application, the ``docker-compose.yml`` file includes a deployment of said platform.

Before you begin
--------------------

Follow these steps to install the necessary tools:

#. Install `Docker Community Edition (CE) <https://docs.docker.com/engine/installation/>`_ on your workstation. Depending on the OS, you may need to configure your Docker instance to use 4.00 GB of memory for all containers to run properly. Please refer to the Resources section if using Docker for Windows or Docker for Mac for more information.
#. Install `Docker Compose <https://docs.docker.com/compose/install/>`_ and newer on your workstation.

Older versions of docker-compose do not support all features required by docker-compose.yml file, so double check that it meets the minimum version requirements.

docker-compose.yml
---------------------

To deploy cornflow on Docker Compose, you should fetch docker-compose.yml::

    curl -LfO 'https://raw.githubusercontent.com/baobabsoluciones/corn/master/docker-compose.yml'

Before starting cornflow for the first time, You need to prepare your environment, i.e. create the necessary files, directories and initialize the database.
On Linux, the mounted volumes in container use the native Linux filesystem user/group permissions, so you have to make sure the container and host computer have matching file permissions::

    mkdir -p ./airflow_config/dags
    cp "yourpathtofilerequirements.txt" ./airflow_config/requirements.txt

Running cornflow
********************

Now you can start all services::

    docker-compose up -d

Cornflow service available at http://localhost:5000
Airflow service available at http://localhost:8080

In the second terminal you can check the condition of the containers and make sure that no containers are in unhealthy condition::

    docker ps

    CONTAINER ID   IMAGE                             COMMAND                  CREATED          STATUS                    PORTS                                                           NAMES
    10863a20e7d6   baobabsoluciones/cornflow         "./initapp.sh"           16 minutes ago   Up 16 minutes             0.0.0.0:5000->5000/tcp, :::5000->5000/tcp                       corn_cornflow_1
    0cfdd4debaab   baobabsoluciones/docker-airflow   "/initairflow.sh web…"   16 minutes ago   Up 16 minutes (healthy)   5555/tcp, 8793/tcp, 0.0.0.0:8080->8080/tcp, :::8080->8080/tcp   corn_webserver_1
    9bc91747cd37   postgres                          "docker-entrypoint.s…"   16 minutes ago   Up 16 minutes             5432/tcp                                                        corn_airflow_db_1
    c477c235b199   postgres                          "docker-entrypoint.s…"   16 minutes ago   Up 16 minutes             5432/tcp                                                        corn_cornflow_db_1

Stop and clean docker environment
***********************************

Stop the docker services and remove all volumes::

    docker-compose down --volumes --rmi all

Cornflow docker stack
---------------------------

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

Entrypoint
*************

If you are using the default entrypoint of the production image, it will execute ``initapp.sh`` script wich use and initialize environment variables to work with postgresql and airflow defined in ``docker-compose.yml``.
The image entrypoint works as follows:

#. A new fernet secret key it will be generated.
#. Check cornflow postgresql database connection.
#. The migrations and upgrade of the database is executed on every deployment.
#. For the very first time will create the cornflow superuser.
#. Finally launch gunicorn server with 3 gevent workers.

Airflow personalized image for cornflow
******************************************

For this project we have created a custom Airflow image that we will maintain for the life cycle of the Cornflow application.
The airflow personalized image is built from the Dockerfile file hosted in the official cornflow repository. The image is built from the new changes on the main development branch, creating an image with the label "latest"::

    docker pull baobabsoluciones/docker-airflow:latest

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

PostgreSQL docker image
***************************

The image displayed in the container will be the official image of the popular `PostgreSQL <https://hub.docker.com/_/postgres>`_ database engine.
The postgresql environment variables included in ``docker-compose.yml`` are::

    POSTGRES_USER - database username of service 
    POSTGRES_PASSWORD - database user´s password of service 
    POSTGRES_DB - database name of service
   
The postgresql deployment requires mounting one volume linked to the directory created on the host::

    postgres_cf_data:/var/lib/postgresql/data/ - This volume stores the database files

Running cornflow with simultaneous resolutions
--------------------------------------------------

For do this kind of deployment, you could use the template ``docker-compose-cornflow-celery.yml``.
To deploy you should fetch docker-compose-cornflow-celery.yml::

    curl -LfO 'https://raw.githubusercontent.com/baobabsoluciones/corn/master/docker-compose-cornflow-celery.yml'

Airflow service allow you to run with CeleryExecutor. For more information, see `Basic airflow architecture <https://airflow.apache.org/docs/apache-airflow/stable/concepts.html>`_.

This type of deployment allows simultaneous execution of resolution jobs. For this, different machines are created with an airflow installation that communicate with the main server through a message broker. These machines are defined as ``workers``.
You can deploy as many workers as you want, but taking into account that each parallel execution will consume hardware host resources.

.. _cornflow_celery_docker_stack:

.. figure:: ./../_static/cornflow_celery_docker_stack.png

    Demonstration of the cornflow service with three instances of simultaneous execution communicating through redis.

If you are running cornflow with multiple workers, there are additional resources that must be provided in your deployment:

#. airflow worker machines
#. airflow flower server
#. redis message broker server

New environment variables must also be taken into account for services running in Celery mode::

    EXECUTOR - Airflow execution mode. In this case the value it should have is Celery.
    FERNET_KEY - A fernet key is used to encrypt and decrypt tokens managed by aiflow. All airflow related services must have the same key value.
    AIRFLOW__CELERY__BROKER_URL - CeleryExecutor drives the need for a Celery broker, here Redis is used.

For running with CeleryExecutor execute this command::

    docker-compose -f docker-compose-cornflow-celery.yml up -d

    CONTAINER ID   IMAGE                             COMMAND                  CREATED         STATUS                   PORTS                                                           NAMES
    e13c87bcd36b   baobabsoluciones/docker-airflow   "/initairflow.sh wor…"   6 minutes ago   Up 6 minutes             5555/tcp, 8080/tcp, 8793/tcp                                    corn_worker_1
    5a96cc04b69b   baobabsoluciones/docker-airflow   "/initairflow.sh sch…"   6 minutes ago   Up 5 minutes             5555/tcp, 8080/tcp, 8793/tcp                                    corn_scheduler_1
    c5d3fdad4c6b   baobabsoluciones/cornflow         "./initapp.sh"           6 minutes ago   Up 6 minutes             0.0.0.0:5000->5000/tcp, :::5000->5000/tcp                       corn_cornflow_1
    e98dfc643ddd   baobabsoluciones/docker-airflow   "/initairflow.sh web…"   6 minutes ago   Up 6 minutes (healthy)   5555/tcp, 8793/tcp, 0.0.0.0:8080->8080/tcp, :::8080->8080/tcp   corn_webserver_1
    129fd9b29361   baobabsoluciones/docker-airflow   "/initairflow.sh flo…"   6 minutes ago   Up 6 minutes             8080/tcp, 0.0.0.0:5555->5555/tcp, :::5555->5555/tcp, 8793/tcp   corn_flower_1
    c56e3444078c   postgres                          "docker-entrypoint.s…"   6 minutes ago   Up 6 minutes             5432/tcp                                                        corn_airflow_db_1
    7a7b10d09a46   redis:5.0.5                       "docker-entrypoint.s…"   6 minutes ago   Up 6 minutes             6379/tcp                                                        corn_redis_1
    8389735999d5   postgres                          "docker-entrypoint.s…"   6 minutes ago   Up 6 minutes             5432/tcp                                                        corn_cornflow_db_1

The number of ``workers`` deployed depends on ``--scale`` argument. For example, if number of workers needed is 3::

    docker-compose -f docker-compose-cornflow-celery.yml up -d --scale worker=3

    CONTAINER ID   IMAGE                             COMMAND                  CREATED         STATUS                   PORTS                                                           NAMES
    65de0e382a04   baobabsoluciones/docker-airflow   "/initairflow.sh wor…"   4 minutes ago   Up 53 seconds            5555/tcp, 8080/tcp, 8793/tcp                                    corn_worker_1
    4c872f5b6647   baobabsoluciones/docker-airflow   "/initairflow.sh wor…"   4 minutes ago   Up 4 minutes             5555/tcp, 8080/tcp, 8793/tcp                                    corn_worker_3
    fca4c231139f   baobabsoluciones/docker-airflow   "/initairflow.sh wor…"   4 minutes ago   Up 54 seconds            5555/tcp, 8080/tcp, 8793/tcp                                    corn_worker_2
    a7f2868e9329   baobabsoluciones/docker-airflow   "/initairflow.sh sch…"   4 minutes ago   Up 24 seconds            5555/tcp, 8080/tcp, 8793/tcp                                    corn_scheduler_1
    f21b97ae83e8   baobabsoluciones/cornflow         "./initapp.sh"           4 minutes ago   Up 4 minutes             0.0.0.0:5000->5000/tcp, :::5000->5000/tcp                       corn_cornflow_1
    68d8f7db53ac   baobabsoluciones/docker-airflow   "/initairflow.sh web…"   4 minutes ago   Up 4 minutes (healthy)   5555/tcp, 8793/tcp, 0.0.0.0:8080->8080/tcp, :::8080->8080/tcp   corn_webserver_1
    7d6e114978af   baobabsoluciones/docker-airflow   "/initairflow.sh flo…"   4 minutes ago   Up 3 minutes             8080/tcp, 0.0.0.0:5555->5555/tcp, :::5555->5555/tcp, 8793/tcp   corn_flower_1
    d2730ce4b8c1   postgres                          "docker-entrypoint.s…"   4 minutes ago   Up 4 minutes             5432/tcp                                                        corn_cornflow_db_1
    ec86c6761b80   postgres                          "docker-entrypoint.s…"   4 minutes ago   Up 4 minutes             5432/tcp                                                        corn_airflow_db_1
    2d5200460cfb   redis:5.0.5                       "docker-entrypoint.s…"   4 minutes ago   Up 4 minutes             6379/tcp                                                        corn_redis_1

Airflow service available at http://localhost:8080
Flower service available at http://localhost:5555

If you want to stop the docker services and remove all volumes::

    docker-compose down -f docker-compose-cornflow-celery.yml --volumes --rmi all

Deployment options
----------------------

Running airflow with reverse proxy
***************************************

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

More information in `airflow documentation page <https://airflow.apache.org/docs/apache-airflow/stable/howto/run-behind-proxy.html>`_

Setup cornflow database with your own PostgreSQL server
***********************************************************

Please visit the official `PostgreSQL <https://www.postgresql.org/docs/>`_ documentation page to learn more about this database engine.

**Create user, password and database**

To create a database, you must be a superuser. A user called postgres is made on and the user postgres has full superadmin access to entire PostgreSQL::

    sudo -u postgres psql
    postgres=# create database cornflowdb;
    postgres=# create user myuser with encrypted password 'myuserpwd';
    postgres=# grant all privileges on database cornflowdb to myuser;

**Cornflow set connection to database**

Before deploying Cornflow, set the environment variable with the address of the database::

    docker run -e DATABASE_URL=postgres://myuser:myuserpwd@myserverip:myserverport/cornflow -d --name=cornflow baobabsoluciones/cornflow
    
Connect to your own airflow deployment
*******************************************

For do this kind of deployment, you could use the template ``docker-compose-cornflow-separate.yml``.
To deploy you should fetch docker-compose-cornflow-separate.yml::

    curl -LfO 'https://raw.githubusercontent.com/baobabsoluciones/corn/master/docker-compose-cornflow-separate.yml'

Before deploying Cornflow, set the required airflow environment variables. For example with a file named ``.env.airflow`` ::

    AIRFLOW_USER=myairflowuser
    AIRFLOW_PWD=myairflowuserpwd
    AIRFLOW_URL=http://myairflowurl:8080
    AIRFLOW_CONN_CF_URI=http://mycornflowuser:mycornflowpassword@mycornflowurl

Then execute this::

    docker-compose -f docker-compose-cornflow-separate.yml --env-file .env.airflow up -d

Production Deployment
---------------------------

It is time to deploy Cornflow in production. To do this, first, you need to make sure that the airflow is itself `production-ready <https://airflow.apache.org/docs/apache-airflow/stable/production-deployment.html>`_.

Database backend
*****************

Running the default docker-compose setup in production can lead to data loss in multiple scenarios. If you want to run production-grade Cornflow, make sure you configure the backend to be an external PostgreSQL.
You can change the backend using the following config::

    DATABASE_URL=postgres://myuser:myuserpwd@myserverip:5432/cornflow

SSL
******

At the moment cornflow does not have built-in `SSL <https://en.wikipedia.org/wiki/Transport_Layer_Security>`_ support. You can use a reverse proxy service such as `Nginx <http://nginx.org/>`_ to give adequate security to the connection with your server.
Please go to the `Nginx documentation page <http://nginx.org/en/docs/http/configuring_https_servers.html>`_ to correctly configure your server's certificates. 

This is a Nginx configuration template (``/etc/nginx/conf.d/mysite.conf``) that we can use to configure the ssl encryption with the cornflow service::

    server {
       listen 443 ssl;
       server_name mycornflowsite.com;
       location / {
       rewrite ^/v1/(.*)$ /$1 break;
         proxy_pass http://localhost:5000;
         proxy_set_header Host $host;
         proxy_redirect off;
         proxy_http_version 1.1;
         proxy_set_header Upgrade $http_upgrade;
         proxy_set_header Connection "upgrade";
       }
	   ssl_certificate /pathtocertificate/mysite.crt;
       ssl_certificate_key /pathtocertificatekey/mysite.key;
       error_page 400 /400.json;
       location /400.json {
           return 400 '{"error":{"code":400,"message":"Bad Request"}}';
       }
       error_page 403 /403.json;
       location /403.json {
           return 403 '{"error":{"code":403,"message": "Forbidden"}}';
       }
       error_page 500 /500.json;
       location /500.json {
           return 500 '{"error":{"code":500,"message":"Internal Server Error"}}';
       }
    }

Enforce security
********************

When using cornflow in a production environment, the usernames and passwords should be stored in a safe place. In the deployment through docker-compose you can connect the environment variables with your KMS system.
If you are running docker services in production, it is also convenient to use the `docker secret manager <https://docs.docker.com/engine/swarm/secrets/#use-secrets-in-compose>`_.

It is also recommended to put a password in the celery broker for the production environment. In all airflow services, the redis environment variable should be secured with a key::

    REDIS_PASSWORD="myredispassword"

Flower has by default a `basic authentication <https://flower.readthedocs.io/en/latest/auth.html>`_ shared with the airflow server in the deployment.

LDAP Authentication
**********************

At the moment, cornflow does not support the integration of LDAP servers to manage the users of the application. Airflow does support this functionality and therefore it should be activated in the production deployment. To learn more about how to enable LDAP in airflow, see this `page <https://airflow.apache.org/docs/apache-airflow/1.10.1/security.html#ldap>`_.

Access control
-----------------------

Cornflow supports multi-user access using password encryption authentication. In this section we will see how to create users, delete them or change the user´s access password.

Manage cornflow users
***********************

In the cornflow image, if no environment variables are set, a super-admin user is created with these credentials::

    name - user@cornflow.com
    password - cornflow1234

It is advisable to change the default super-admin user and keep the password in a safe place.

To create a user, you must interact with the cornflow application through an `endpoint of its API <https://baobabsoluciones.github.io/corn/dev/endpoints.html#module-cornflow.endpoints.user>`_
It is only possible to create new cornflow admin user using another one with those privileges.

In cornflow there is a differentiation between three user roles with different characteristics::

    super-admin - This user can manage the rest of cornflow users and also has access to make changes to the airflow platform
    admin - This user can manage the rest of the cornflow users but does not have privileged access to the airflow service
    user - The general user of cornflow can create jobs and send models to solve

Manage airflow users
***********************

The default administrator user for airflow and flower will be::

    name - admin
    password - admin

It is advisable to change the default admin user and keep the password in a safe place.
`Access Control of Airflow Webserver UI <https://airflow.apache.org/docs/apache-airflow/stable/security/access-control.html>`_ is handled by Flask AppBuilder (FAB). Please read its related security document regarding its `security model <http://flask-appbuilder.readthedocs.io/en/latest/security.html>`_.

Logging and monitoring
--------------------------

Cornflow logs
****************

At the moment cornflow does not have a log storage folder. All application logs are written to console output. In this way we can visualize them by launching the following command::

    docker logs `docker ps -q --filter ancestor=baobabsoluciones/cornflow`

Airflow logs
****************

Airflow supports a variety of logging and monitoring mechanisms as shown on it´s `documentation page <https://airflow.apache.org/docs/apache-airflow/stable/logging-monitoring/index.html#logging-monitoring>`_.

Scheduler log
^^^^^^^^^^^^^^^^

The logs are stored in the logs folder within the ``$AIRFLOW_HOME`` directory.

The scheduler logs are named after the DAGs handled by the service. Navigate to where the log file is::

    docker exec -it `docker ps -q --filter name=scheduler` bash -c "ls -l ${AIRFLOW_HOME}logs/scheduler/latest/"
    
    -rw-r--r-- 1 airflow airflow 1377544 May 20 10:04 dag_timer.py.log
    -rw-r--r-- 1 airflow airflow 1168103 May 20 10:03 graph_coloring.py.log
    -rw-r--r-- 1 airflow airflow 1454702 May 20 10:04 hk_2020_dag.py.log
    -rw-r--r-- 1 airflow airflow 1370681 May 20 10:03 optim_dag.py.log
    -rw-r--r-- 1 airflow airflow 1495255 May 20 10:03 update_all_schemas.py.log

Worker logs
^^^^^^^^^^^^^^^^

As in the rest of airflow services, the logs are stored in the logs folder within the ``$AIRFLOW_HOME``directory.
The logs are divided into folders with the name of the DAGs and into subfolders with their execution dates.

If we want to view logs with a command, here things get a bit complicated since we can have different workers deployed, with different DAGs. We must help ourselves with the linux bash commands to filter the search as much as possible. Let's say we want to review today logs of the DAG ``update_all_squemas`` in every worker::

    for id in `docker ps -q --filter name=worker_`; do docker exec -it $id bash -c "tail ${AIRFLOW_HOME}logs/update_all_schemas/update_all_schemas/$(date +%Y-%m-%d)*/*.log";done;

    [2021-05-19 17:37:27,173] {logging_mixin.py:104} INFO - looking for apps in dir=/usr/local/airflow/dags
    [2021-05-19 17:37:27,173] {logging_mixin.py:104} INFO - Files are: ['graph_coloring.py', 'update_all_schemas.py', '__init__.py', 'graph_coloring_output.json', 'hk_2020_dag.py', 'dag_timer.py', 'graph_coloring_input.json', '__pycache__', 'optim_dag.py']
    [2021-05-19 17:37:28,149] {logging_mixin.py:104} WARNING - /usr/local/airflow/.local/lib/python3.8/site-packages/hackathonbaobab2020/execution/__init__.py:7 UserWarning: To use the benchmark functions, you need to install the benchmark dependencies:
    `pip install hackathonbaobab2020[benchmark]`
    [2021-05-19 17:37:28,251] {logging_mixin.py:104} INFO - Found the following apps: ['graph_coloring', 'hk_2020_dag', 'timer', 'solve_model_dag']
    [2021-05-19 17:37:28,571] {python.py:118} INFO - Done. Returned value was: None
    [2021-05-19 17:37:28,588] {taskinstance.py:1185} INFO - Marking task as SUCCESS. dag_id=update_all_schemas, task_id=update_all_schemas, execution_date=20210518T173709, start_date=20210519T173726, end_date=20210519T173728
    [2021-05-19 17:37:28,629] {taskinstance.py:1246} INFO - 0 downstream tasks scheduled from follow-on schedule check
    [2021-05-19 17:37:28,654] {local_task_job.py:146} INFO - Task exited with return code 0
    'logs/update_all_schemas/update_all_schemas/2021-05-18*/*.log': No such file or directory

Note that we can get an error of the type (``No such file or directory``) because that log does not exist in all workers.

Known problems
------------------

In progess.