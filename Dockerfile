# pull official base image
FROM python

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
COPY . /usr/src/app/

# install dos2unix for initapp.sh
RUN apt update && apt install dos2unix -y
RUN dos2unix initapp.sh
RUN chmod +x initapp.sh

# execute script initapp.sh
CMD ["./initapp.sh"]
