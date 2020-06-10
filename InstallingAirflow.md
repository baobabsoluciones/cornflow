# Useful tutorial:

`https://towardsdatascience.com/getting-started-with-airflow-using-docker-cd8b44dbff98`

# Docker

Download and install docker from:
`https://docs.docker.com/docker-for-windows/install/`

# Getting Airflow

Download airflow docker repository:
`docker pull puckel/docker-airflow`
or
`docker pull apache/airflow`

# Starting Aiflow

Run the image
- `docker run -d -p 8080:8080 puckel/docker-airflow webserver`
- Airflow UI will be in `http://localhost:8080/admin/`

# Useful commands

See container information (and get container name):
- `docker ps`

Go into container commadn lines:
- `docker exec -ti <container name> bash`

Configurate shared directory (does not seem to work)
`docker run -d -p 8080:8080 -v shared/directory/path:/usr/local/airflow/dags puckel/docker-airflow webserver`

