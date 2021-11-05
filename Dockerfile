# VERSION 2.0.2
# AUTHOR: sistemas@baobabsoluciones.es

FROM python:3.8-slim-buster
LABEL maintainer="sistemas@baobabsoluciones"

# Never prompt the user for choices on installation/configuration of packages
ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux

# install dos2unix for initapp.sh
RUN apt update -y && apt-get install -y --no-install-recommends \
		gcc \
		git \
		python3-dev \
		libffi-dev \
		libpq-dev \
		logrotate
		
# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt --force-reinstall

# copy project
COPY cornflow /usr/src/app/cornflow
COPY docs /usr/src/app/docs
COPY migrations /usr/src/app/migrations
COPY examples /usr/src/app/examples
COPY *.py /usr/src/app/
RUN mkdir -p /usr/src/app/log

EXPOSE 5000

# execute script initapp.sh
ENTRYPOINT [ "python" ]
CMD ["/usr/src/app/init_cornflow_service.py"]
