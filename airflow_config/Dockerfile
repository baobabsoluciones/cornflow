# VERSION 2.x.x
# AUTHOR: sistemas@baobabsoluciones.es
# DESCRIPTION: Airflow 2.x.x image personalized for use with Cornflow (from puckel/docker-airflow https://github.com/puckel/docker-airflow by "Puckel_")

FROM python:3.8-slim-buster
LABEL maintainer="sistemas@baobabsoluciones"

# Never prompt the user for choices on installation/configuration of packages
ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux

# Airflow vars
ARG AIRFLOW_VERSION=2.1.0
ARG AIRFLOW_USER_HOME=/usr/local/airflow
ARG CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-3.8.txt"
ARG AIRFLOW__CORE__LOAD_EXAMPLES=False
ENV AIRFLOW_HOME=${AIRFLOW_USER_HOME}

# install Airflow requirements
RUN apt update -y && apt-get install -y --no-install-recommends \
        apt-utils \
        default-jre \
        default-jdk \
        g++ \
        gcc \
        git \
		freetds-bin \
        krb5-user \
        ldap-utils \
        libffi6 \
        libffi-dev \
        libldap2-dev \
		libpq-dev \
        libprotobuf-dev \
        libsasl2-2 \
        libsasl2-dev \
        libsasl2-modules \
        libssl1.1 \
        libssl-dev \
        locales  \
        lsb-release \
        make \
        pkg-config \
        protobuf-compiler \
		python3-dev \
        sasl2-bin \
        slapd \
        sqlite3 \
        ssh \
        unixodbc \
        wget

# install Airflow and extras: celery,postgres and redis
RUN pip install "apache-airflow[celery,google,postgres,redis]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
RUN pip install python-ldap
RUN pip install GitPython
RUN pip install cmake

# copy init script and config to container
COPY scripts/init_airflow_service.py ${AIRFLOW_HOME}/init_airflow_service.py
COPY scripts ${AIRFLOW_HOME}/scripts
COPY webserver_ldap.py ${AIRFLOW_HOME}/webserver_ldap.py

# create folder for custom ssh keys
RUN mkdir ${AIRFLOW_USER_HOME}/.ssh

# execute installation solvers script
RUN python ${AIRFLOW_HOME}/scripts/solver_installation.py

# user airflow on application
RUN useradd -ms /bin/bash -d ${AIRFLOW_USER_HOME} airflow
RUN chown -R airflow: /usr/local/airflow
RUN chown airflow: /usr/local/bin/mps_mipcl 
RUN chown airflow: /usr/local/bin/choco.jar
RUN chown airflow: /usr/local/bin/highs

EXPOSE 8080 5555 8793

USER airflow
WORKDIR ${AIRFLOW_USER_HOME}

ENTRYPOINT ["python", "init_airflow_service.py"]
CMD ["webserver"]