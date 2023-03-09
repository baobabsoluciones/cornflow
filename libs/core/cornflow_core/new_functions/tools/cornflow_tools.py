import logging as log

from cornflow_client.airflow.api import Airflow
from cornflow_client.constants import AirflowError
from flask import current_app

from cornflow.shared.const import (
    EXEC_STATE_ERROR_START,
    EXECUTION_STATE_MESSAGE_DICT,
    EXEC_STATE_ERROR,
    EXEC_STATE_QUEUED,
)


def launch_dag(execution, user_id):
    """
    Connect to Airflow and launch the dag for the given execution.

    :param execution: execution data.
    :param user_id: user id.
    :return: posted data and response status.
    """
    config = current_app.config
    # We now try to launch the task in airflow
    af_client = Airflow.from_config(config)
    if not af_client.is_alive():
        err = "Airflow is not accessible"
        log.error(err)
        execution.update_state(EXEC_STATE_ERROR_START)
        raise AirflowError(
            error=err,
            payload=dict(
                message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                state=EXEC_STATE_ERROR_START,
            ),
        )
    # ask airflow if dag_name exists
    schema = execution.schema
    schema_info = af_client.get_dag_info(schema)

    # Validate that instance and dag_name are compatible
    # marshmallow_obj = get_schema(config, schema, INSTANCE_SCHEMA)
    # validate_and_continue(marshmallow_obj(), instance.data)

    info = schema_info.json()
    if info["is_paused"]:
        err = "The dag exists but it is paused in airflow"
        log.error(err)
        execution.update_state(EXEC_STATE_ERROR_START)
        raise AirflowError(
            error=err,
            payload=dict(
                message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                state=EXEC_STATE_ERROR_START,
            ),
        )

    try:
        response = af_client.run_dag(execution.id, dag_name=schema)
    except AirflowError as err:
        error = "Airflow responded with an error: {}".format(err)
        log.error(error)
        execution.update_state(EXEC_STATE_ERROR)
        raise AirflowError(
            error=error,
            payload=dict(
                message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR],
                state=EXEC_STATE_ERROR,
            ),
        )

    # if we succeed, we register the dag_run_id in the execution table:
    af_data = response.json()
    execution.dag_run_id = af_data["dag_run_id"]
    execution.update_state(EXEC_STATE_QUEUED)
    log.info("User {} creates execution {}".format(user_id, execution.id))
    return execution, 201


def post_model_data(data, data_model, user_id, trace_field="user_id"):
    """
    Post data for a model.

    :param data: data as a dict.
    :param data_model: model.
    :param user_id: user id.
    :param trace_field: name of the trace field.
    :return: posted object and response status.
    """
    data = dict(data)
    data[trace_field] = user_id
    item = data_model(data)
    item.save()
    return item, 201


def put_model_data(data, data_model, **selector):
    """
    Update data for a model.

    :param data: data as a dict.
    :param data_model: model.
    :param selector: filter to apply to select the object.
    :return: posted data and response status.
    """
    item = data_model.get_one_object(**selector)
    if item is None:
        raise ObjectDoesNotExist("The data entity does not exist on the database")
    data = dict(data)
    item.update(data)
    return item, 200