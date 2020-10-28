# pull official base image
FROM python

# install airflow+gcp
RUN pip3 install \
 apache-airflow[postgres,gcp]==1.10.12 \
 --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-1.10.12/constraints-3.7.txt"
RUN pip3 install pulp orloge