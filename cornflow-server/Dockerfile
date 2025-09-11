# VERSION 1.2.4
# AUTHOR: sistemas@baobabsoluciones.es

FROM python:3.12-slim
LABEL maintainer="cornflow@baobabsoluciones"

# Never prompt the user for choices on installation/configuration of packages
ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=linux

# CORNFLOW vars
ARG CORNFLOW_VERSION=1.2.4

# install linux pkg
RUN apt update -y && apt-get install -y --no-install-recommends \
		gcc \
		git \
        ssh \
		python3-dev \
		libffi-dev \
		libpq-dev \
		logrotate
		
# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEFAULT_POSTGRES=1

# install dependencies
COPY ./.ssh/* /root/.ssh/
RUN chmod 400 /root/.ssh/id_rsa
RUN pip install --upgrade pip
RUN pip install git+ssh://git@github.com/baobabsoluciones/cornflow.git@bugfix/migrations_command#subdirectory=cornflow-server


# create folder for logs
RUN mkdir -p /usr/src/app/log

# create folder for custom ssh keys
RUN mkdir /usr/src/app/.ssh

# user cornflow on application
RUN useradd -ms /bin/bash -d /usr/src/app cornflow
RUN chown -R cornflow: /usr/src/app
USER cornflow

EXPOSE 5000

# execute python init script
CMD ["cornflow", "service", "init"]
