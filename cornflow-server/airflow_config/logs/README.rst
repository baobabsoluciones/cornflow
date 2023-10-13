Airflow LOGS
--------------

Users can specify the directory to place log files in airflow.cfg using base_log_folder. By default, logs are placed in the AIRFLOW_HOME directory.

The following convention is followed while naming logs: {dag_id}/{task_id}/{execution_date}/{try_number}.log

In addition, users can supply a remote location to store current logs and backups.

In the Airflow Web UI, local logs take precedence over remote logs. If local logs can not be found or accessed, the remote logs will be displayed. Note that logs are only sent to remote storage once a task is complete (including failure); In other words, remote logs for running tasks are unavailable.