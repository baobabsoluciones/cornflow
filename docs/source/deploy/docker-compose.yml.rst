
docker-compose.yml
---------------------

To deploy cornflow on Docker Compose, you should fetch the `docker-compose.yml` file::

    curl -LfO 'https://raw.githubusercontent.com/baobabsoluciones/corn/master/docker-compose.yml'

Before starting cornflow for the first time, You need to prepare your environment, i.e. create the necessary files, directories and initialize the database.
On Linux, the mounted volumes in the container use the native Linux filesystem user/group permissions, so you have to make sure the container and host computer have matching file permissions::

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
