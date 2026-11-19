
Logging and monitoring
--------------------------

cornflow logs
****************

cornflow logs are written to console output (stdout) by default. In this way you can visualize them by launching the following command::

    docker logs `docker ps -q --filter ancestor=baobabsoluciones/cornflow`

If you want to know about the possibilities offered by the docker log engine, you can visit the official documentation `here <https://docs.docker.com/engine/reference/commandline/logs/>`_.

Log output configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^

The destination and format of the logs (application logs and gunicorn access/error logs) can be configured through environment variables:

.. list-table::
   :header-rows: 1
   :widths: 35 45 20

   * - Variable
     - Description
     - Default
   * - ``CORNFLOW_LOG_STREAM``
     - Console stream for the logs: ``stdout`` or ``stderr``.
     - ``stdout``
   * - ``CORNFLOW_LOG_FORMAT``
     - ``text`` for plain text or ``json`` for one JSON object per line (recommended for log collectors such as Fluent Bit, CloudWatch or Cloud Logging).
     - ``text``
   * - ``LOG_LEVEL``
     - Minimum level of the records: 10 (debug), 20 (info), 30 (warning), 40 (error), 50 (critical).
     - ``20``

In JSON mode each line contains the fields ``timestamp`` (ISO 8601, UTC), ``level``, ``logger``, ``module``, ``message`` and, when present, ``exception``.

Shipping logs to S3 or Google Cloud Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In Kubernetes or docker deployments the recommended pattern is to write JSON logs to stdout and let a cluster agent (Fluent Bit, Vector, CloudWatch agent...) ship them to their final destination. Nevertheless, cornflow can also upload the logs directly to a bucket, in addition to the console output:

.. list-table::
   :header-rows: 1
   :widths: 35 45 20

   * - Variable
     - Description
     - Default
   * - ``CORNFLOW_LOG_S3_BUCKET``
     - Name of the AWS S3 bucket to upload logs to. Requires ``boto3`` (``pip install cornflow[s3-logs]``) and credentials resolved the standard AWS way (environment variables, instance profile, IRSA...).
     - (disabled)
   * - ``CORNFLOW_LOG_GCS_BUCKET``
     - Name of the Google Cloud Storage bucket to upload logs to. Requires ``google-cloud-storage`` (``pip install cornflow[gcs-logs]``) and credentials resolved the standard GCP way (``GOOGLE_APPLICATION_CREDENTIALS``, workload identity...).
     - (disabled)
   * - ``CORNFLOW_LOG_UPLOAD_PREFIX``
     - Key prefix of the uploaded objects.
     - ``cornflow-logs``
   * - ``CORNFLOW_LOG_UPLOAD_INTERVAL``
     - Seconds between uploads.
     - ``60``
   * - ``CORNFLOW_LOG_UPLOAD_MAX_BUFFER``
     - Number of buffered records that forces an immediate upload.
     - ``5000``

Records are buffered in memory and periodically uploaded as objects named ``{prefix}/{date}/{hostname}-{pid}-{time}-{id}.log``. Note that if a container is killed abruptly, the records buffered since the last upload may be lost (they are still written to the console output).

If you want to activate the persistent log storage in files, you must pass the value ``file`` to the environment variable ``CORNFLOW_LOGGING`` in the cornflow server deployment.
Once the log storage is activated, these will be saved in the path ``/usr/src/app/log`` inside the cornflow container.
To permanently store the logs even if the service is destroyed, you can mount a volume against the directory as follows::

    --volume /local/path/to_storage/cornflow/logs:/usr/src/app/log

The log files will rotate and be compressed following the configuration provided to the logrotate service::

    number of files in directory - 30
    frequency - daily
    log file size - 20M

Two files will be created in log directory::

    info.log - record messages with access to the application with the default log level value ``info``
    error.log - here the application errors will be recorded

The compressed logs will have this format: ``info.log.1.gz``

Airflow logs
****************

Airflow supports a variety of logging and monitoring mechanisms as shown on it's `documentation page <https://airflow.apache.org/docs/apache-airflow/stable/logging-monitoring/index.html#logging-monitoring>`_.

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

As in the rest of airflow services, the logs are stored in the logs folder within the ``$AIRFLOW_HOME`` directory.
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

Monitoring
*************

cornflow monitoring
^^^^^^^^^^^^^^^^^^^^^

You can call the ``/health`` endpoint to obtain the status of the cornflow and airflow servers. It should return a 200 code as well as "healthy" of status for both ``cornflow_status`` and ``airflow_status``::

    {
      "airflow_status": "healthy",
      "cornflow_status": "healthy"
    }

Check the `API docs <https://baobabsoluciones.github.io/cornflow/stable-rest-api-ref.html#tag/Health>`_ for more information.

Airflow monitoring
^^^^^^^^^^^^^^^^^^^^^

To check the `health status of your Airflow instance <https://airflow.apache.org/docs/apache-airflow/stable/logging-monitoring/check-health.html#checking-airflow-health-status>`_ directly without using cornflow, you can simply access the endpoint ``/health``. It will return a JSON object in which a high-level glance is provided.

