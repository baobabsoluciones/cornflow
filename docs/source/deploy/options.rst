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

    docker run -e DATABASE_URL=postgresql://myuser:myuserpwd@myserverip:myserverport/cornflow -d --name=cornflow baobabsoluciones/cornflow
    
Connect to your own airflow deployment
*******************************************

Before deploying, set the required airflow environment connection. For example ::

    AIRFLOW_CONN_CF_URI=http://mycornflowuser:mycornflowpassword@mycornflowurl

Using custom ssh keys
******************************

If you want to install packages that require a secure connection to a server, you can install your own private key file in the airflow service. To do this, you must mount a volume from its key file to the path ``/usr/local/airflow/.ssh/id_rsa`` ::

    volume:
        - ./your_ssh_priv_key:/usr/local/airflow/.ssh/id_rsa

When you have included the key file in the airflow service, you must enter the server with which it will be used by means of an environment variable. For instance::

    CUSTOM_SSH_HOST=github.com
