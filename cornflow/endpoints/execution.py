"""
External endpoints to manage the executions: create new ones, list all of them, get one in particular
or check the status of an ongoing one
These endpoints hve different access url, but manage the same data entities
"""

# Import from libraries
from flask import request, current_app
from flask_restful import fields, marshal_with

# Import from internal modules
from .meta_resource import MetaResource
from ..models import InstanceModel, ExecutionModel
from ..schemas import ExecutionSchema
from ..shared.airflow_api import Airflow, AirflowApiError
from ..shared.authentication import Auth
from ..shared.const import EXEC_STATE_CORRECT, EXEC_STATE_RUNNING, EXEC_STATE_ERROR, EXEC_STATE_ERROR_START, \
    EXEC_STATE_NOT_RUN, EXEC_STATE_UNKNOWN, EXECUTION_STATE_MESSAGE_DICT

# Initialize the schema that all endpoints are going to use
execution_schema = ExecutionSchema()


class ExecutionEndpoint(MetaResource):
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
    def get(self):
        """
        API method to get all the executions created by the user and its related info
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed or a list with all the executions
          created by the authenticated user) and a integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        # TODO: if super_admin or admin should it be able to get any execution?
        # TODO: return a 204 if no executions have been created by the user
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        return self.get_list(self.user_id)

    @Auth.auth_required
    def post(self):
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
        result = self.post_list(request)

        not_run = request.args.get('run', '1') == '0'

        # if we failed to save the execution, we do not continue
        if result[1] >= 300 or not_run:
            return result
        elif not_run:
            execution = ExecutionModel.get_one_execution_from_user(self.user_id, result[0][self.primary_key])
            execution.update_state(EXEC_STATE_NOT_RUN)
            return result

        execution = ExecutionModel.get_one_execution_from_user(self.user_id, result[0][self.primary_key])

        # We now try to launch the task in airflow
        af_client = Airflow(**airflow_conf)
        # TODO: add log when fails
        if not af_client.is_alive():
            execution.update_state(EXEC_STATE_ERROR_START)
            return {'message': EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    'error': "Airflow is not accessible."}, 400

        try:
            response = af_client.run_dag(execution.id, dag_name='solve_model_dag')
        except AirflowApiError as err:
            execution.update_state(EXEC_STATE_ERROR)
            return {'message': EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR],
                    'error': "Airflow responded with an error: {}".format(err)}, 400

        # if we succeed, we register the dag_run_id in the execution table:
        data = response.json()
        execution.dag_run_id = data['dag_run_id']
        execution.update_state(EXEC_STATE_RUNNING)
        return result


class ExecutionDetailsEndpoint(MetaResource):
    """
    Endpoint used to get the information of a certain execution. But not the data!
    """
    resource_fields = dict(
        id=fields.String,
        name=fields.String,
        description=fields.String,
        created_at=fields.String,
        instance_id=fields.String,
        # TODO: this will change:
        finished=fields.Boolean,
    )

    def __init__(self):
        super().__init__()
        self.model = ExecutionModel
        self.query = 'get_one_execution_from_user'
        self.schema = ExecutionSchema()
        self.primary_key = 'id'
        self.foreign_data = {'instance_id': InstanceModel}

    @marshal_with(resource_fields)
    @Auth.auth_required
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
        # TODO: what if the reference id is wrong and it does not exist => 404
        # TODO: if super_admin or admin should it be able to get any execution? => yes
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        return self.get_detail(self.user_id, idx)

    @Auth.auth_required
    def put(self, idx):
        """
        Edit an existing execution

        :param string idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        return self.put_detail(request, self.user_id, idx)

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


class ExecutionStatusEndpoint(MetaResource):
    """
    Endpoint used to get the status of a certain execution that is running in the airflow webserver
    """
    @Auth.auth_required
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
        if execution.state == EXEC_STATE_CORRECT:
            return {'message': EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_CORRECT], 'status': EXEC_STATE_CORRECT}, 200

        dag_run_id = execution.dag_run_id
        if not dag_run_id:
            execution.update_state(EXEC_STATE_UNKNOWN)
            return {'message': EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_UNKNOWN],
                    'error': 'The execution has no dag_run associated.'}, 400

        af_client = Airflow(**airflow_conf)
        if not af_client.is_alive():
            execution.update_state(EXEC_STATE_ERROR_START)
            return {'message': EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    'error': "Airflow is not accessible."}, 400

        try:
            response = af_client.get_dag_run_status(dag_name='solve_model_dag', dag_run_id=dag_run_id)
        except AirflowApiError as err:
            execution.update_state(EXEC_STATE_ERROR)
            return {'message': EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR],
                    'error': "Airflow responded with an error: {}".format(err)}, 400

        data = response.json()
        execution.update_state(EXEC_STATE_RUNNING)
        return {'message': EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_RUNNING], 'status': data['state']}, 200


class ExecutionDataEndpoint(ExecutionDetailsEndpoint):
    """
    Endpoint used to get the solution of a certain execution.
    """
    resource_fields = dict(
        id=fields.String,
        name=fields.String,
        data=fields.Raw(attribute='execution_results'),
    )

    @Auth.auth_required
    @marshal_with(resource_fields)
    def get(self, idx):
        """

        :param str idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the execution) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        return self.get_detail(self.user_id, idx)

    def delete(self, idx):
        return {}, 501

    def put(self, idx):
        return {}, 501


class ExecutionLogEndpoint(ExecutionDetailsEndpoint):
    """
    Endpoint used to get the log of a certain execution.
    """
    resource_fields = dict(
        id=fields.String,
        name=fields.String,
        log=fields.Raw(attribute='log_json'),
    )

    @Auth.auth_required
    @marshal_with(resource_fields)
    def get(self, idx):
        """

        :param str idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the execution) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        # TODO: here, the execution log progress is read correctly but parsed incorrectly by
        #  marshmallow: the arrays in the progress are converted into strings
        return self.get_detail(self.user_id, idx)

    def delete(self, idx):
        return {}, 501

    def put(self, idx):
        return {}, 501
