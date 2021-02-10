"""
External endpoints to manage the executions: create new ones, list all of them, get one in particular
or check the status of an ongoing one
These endpoints hve different access url, but manage the same data entities
"""

# Import from libraries
from flask import request, current_app
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, use_kwargs, doc

# Import from internal modules
from .meta_resource import MetaResource
from ..models import InstanceModel, ExecutionModel
from ..schemas.execution import \
    ExecutionSchema, \
    ExecutionDetailsEndpointResponse, ExecutionDataEndpointResponse, ExecutionLogEndpointResponse, \
    ExecutionStatusEndpointResponse, ExecutionRequest, ExecutionEditRequest
from ..shared.airflow_api import Airflow, AirflowApiError
from ..shared.authentication import Auth
from ..shared.const import EXEC_STATE_CORRECT, EXEC_STATE_RUNNING, EXEC_STATE_ERROR, EXEC_STATE_ERROR_START, \
    EXEC_STATE_NOT_RUN, EXEC_STATE_UNKNOWN, EXECUTION_STATE_MESSAGE_DICT, AIRFLOW_TO_STATE_MAP
from ..shared.exceptions import AirflowError, EndpointNotImplemented

import logging as log

# Initialize the schema that all endpoints are going to use
execution_schema = ExecutionSchema()


@doc(description='Get all executions', tags=['Executions'])
class ExecutionEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to create a new execution or get all the executions and their information back
    """
    def __init__(self):
        super().__init__()
        self.model = ExecutionModel
        self.query = 'get_all_executions'
        self.schema = ExecutionSchema()
        self.primary_key = 'id'
        self.foreign_data = {'instance_id': InstanceModel}

    @Auth.auth_required
    @marshal_with(ExecutionDetailsEndpointResponse(many=True))
    def get(self):
        """
        API method to get all the executions created by the user and its related info
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed or a list with all the executions
          created by the authenticated user) and a integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        if (self.admin or self.super_admin):
            return ExecutionModel.get_all_executions_admin()
        return self.get_list(self.user_id)

    @Auth.auth_required
    @marshal_with(ExecutionDetailsEndpointResponse)
    @use_kwargs(ExecutionRequest, location=('json'))
    def post(self, **kwargs):
        """
        API method to create a new execution linked to an already existing instance
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed, error if data is not validated or
          the reference_id for the newly created execution if successful) and a integer wit the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        config = current_app.config
        airflow_conf = dict(url=config['AIRFLOW_URL'], user=config['AIRFLOW_USER'], pwd=config['AIRFLOW_PWD'])

        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        data, status_code = self.post_list(kwargs)

        not_run = request.args.get('run', '1') == '0'

        # if we failed to save the execution, we already raised an error.
        execution = ExecutionModel.get_one_execution_from_user(self.user_id, data[self.primary_key])
        instance = InstanceModel.get_one_instance_from_user(self.user_id, execution.instance_id)
        dag_name = kwargs.get('dag_name', 'solve_model_dag')
        # execution.instance_id => objeto instance => instance.data
        # dag_name => schema
        # validar(schema, instance.data)
        # TODO: validate that instance and dag_name are compatible
        if not_run:
            execution.update_state(EXEC_STATE_NOT_RUN)
            return execution, 201

        # We now try to launch the task in airflow
        af_client = Airflow(**airflow_conf)
        if not af_client.is_alive():
            err = "Airflow is not accessible"
            log.error(err)
            execution.update_state(EXEC_STATE_ERROR_START)
            raise AirflowError(error=err,
                               payload=dict(message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                                            state=EXEC_STATE_ERROR_START))
        # TODO: ask airflow if dag_name exists
        try:
            response = af_client.run_dag(execution.id, dag_name=dag_name)
        except AirflowApiError as err:
            error = "Airflow responded with an error: {}".format(err)
            log.error(error)
            execution.update_state(EXEC_STATE_ERROR)
            raise AirflowError(error=error,
                               payload=dict(message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR],
                                            state=EXEC_STATE_ERROR))

        # if we succeed, we register the dag_run_id in the execution table:
        af_data = response.json()
        execution.dag_run_id = af_data['dag_run_id']
        execution.update_state(EXEC_STATE_RUNNING)
        return execution, 201


@doc(description='Get details of an executions', tags=['Executions'])
class ExecutionDetailsEndpoint(ExecutionEndpoint):
    """
    Endpoint used to get the information of a certain execution. But not the data!
    """

    def __init__(self):
        super().__init__()
        self.query = 'get_one_execution_from_user'

    @Auth.auth_required
    @marshal_with(ExecutionDetailsEndpointResponse)
    def get(self, idx):
        """
        API method to get an execution created by the user and its related info.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the execution) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        if (self.admin or self.super_admin):
            return ExecutionModel.get_one_execution_from_id_admin(idx)
        return self.get_detail(self.user_id, idx)

    @Auth.auth_required
    @use_kwargs(ExecutionEditRequest, location=('json'))
    def put(self, idx, **data):
        """
        Edit an existing execution

        :param string idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        return self.put_detail(data, self.user_id, idx)

    @Auth.auth_required
    def delete(self, idx):
        """
        API method to delete an execution created by the user and its related info.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param string idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        return self.delete_detail(self.user_id, idx)

    @Auth.auth_required
    def post(self, **kwargs):
        raise EndpointNotImplemented()


class ExecutionStatusEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to get the status of a certain execution that is running in the airflow webserver
    """
    @Auth.auth_required
    @marshal_with(ExecutionStatusEndpointResponse)
    def get(self, idx):
        """
        API method to get the status of the execution created by the user
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str idx:  ID of the execution
        :return: A dictionary with a message (error if the execution does not exist or status of the execution)
            and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        airflow_conf = dict(url=current_app.config['AIRFLOW_URL'],
                            user=current_app.config['AIRFLOW_USER'],
                            pwd=current_app.config['AIRFLOW_PWD'])

        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        execution = ExecutionModel.get_one_execution_from_user(self.user_id, idx)
        if execution.state not in [EXEC_STATE_RUNNING, EXEC_STATE_UNKNOWN]:
            # we only care on asking airflow if the status is unknown or is running.
            return execution, 200

        def _raise_af_error(execution, error, state=EXEC_STATE_UNKNOWN):
            message = EXECUTION_STATE_MESSAGE_DICT[state]
            execution.update_state(state)
            raise AirflowError(error=error,
                               payload=dict(message=message, state=state))

        dag_run_id = execution.dag_run_id
        if not dag_run_id:
            # it's safe to say we will never get anything if we did not store the dag_run_id
            _raise_af_error(execution, state=EXEC_STATE_ERROR,
                            error="The execution has no dag_run associated")

        af_client = Airflow(**airflow_conf)
        if not af_client.is_alive():
            _raise_af_error(execution, "Airflow is not accessible")

        try:
            response = af_client.get_dag_run_status(dag_name='solve_model_dag', dag_run_id=dag_run_id)
        except AirflowApiError as err:
            _raise_af_error(execution, "Airflow responded with an error: {}".format(err))

        data = response.json()
        state = AIRFLOW_TO_STATE_MAP.get(data['state'], EXEC_STATE_UNKNOWN)
        execution.update_state(state)
        return execution, 200


class ExecutionDataEndpoint(ExecutionDetailsEndpoint):
    """
    Endpoint used to get the solution of a certain execution.
    """

    @Auth.auth_required
    @marshal_with(ExecutionDataEndpointResponse)
    def get(self, idx):
        """

        :param str idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the execution) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        return self.get_detail(self.user_id, idx)

    @Auth.auth_required
    def delete(self, idx):
        raise EndpointNotImplemented()

    @Auth.auth_required
    def put(self, **kwargs):
        raise EndpointNotImplemented


class ExecutionLogEndpoint(ExecutionDetailsEndpoint):
    """
    Endpoint used to get the log of a certain execution.
    """

    @Auth.auth_required
    @marshal_with(ExecutionLogEndpointResponse)
    def get(self, idx):
        """

        :param str idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the execution) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        return self.get_detail(self.user_id, idx)

    @Auth.auth_required
    def delete(self, idx):
        raise EndpointNotImplemented()

    @Auth.auth_required
    def put(self, **kwargs):
        raise EndpointNotImplemented()
