"""
External endpoints to manage the executions: create new ones, list all of them, get one in particular
or check the status of an ongoing one
These endpoints hve different access url, but manage the same data entities
"""

# TODO: should we have and endpoint that gets the executions from one instance, not all of them,
#  but not just one without getting the info from the instance?

# Import from libraries
from flask import request, current_app
from flask_restful import Resource

from .meta_resource import MetaResource
# Import from internal modules
from ..models import InstanceModel, ExecutionModel
from ..schemas import ExecutionSchema
from ..shared.airflow_api import Airflow, AirflowApiError
from ..shared.authentication import Auth

# Initialize the schema that all endpoints are going to use
execution_schema = ExecutionSchema()


class ExecutionEndpoint(MetaResource):
    """
    Endpoint used to create a new execution or get all the executions and their information back
    """
    def __init__(self):
        super().__init__()
        self.model = ExecutionModel
        self.query = 'get_all_executions_user'
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
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        result = self.post_list(request)

        # To send the absolute url:
        # url_for(endpoint_name, _external=True)
        airflow_client = Airflow(current_app.config['AIRFLOW_URL'])
        response = airflow_client.run_dag(result[0][self.primary_key], current_app.config['CORNFLOW_URL'])
        if response.status_code != 200:
            raise AirflowApiError('Airflow responded with a status: {}:\n{}'.
                                  format(response.status_code, response.text))

        return response


# TODO: delete an execution and its related data
class ExecutionDetailsEndpoint(Resource):
    """
    Endpoint used to get the information of a certain execution
    """
    @Auth.auth_required
    def get(self, idx):
        """
        API method to get an execution created by the user and its related info.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str reference_id: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
        the data of the execution) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        # TODO: what if the reference id is wrong and it does not exist
        # TODO: if super_admin or admin should it be able to get any execution?
        execution = ExecutionModel.get_execution_with_reference(idx)
        ser_execution = execution_schema.dump(execution, many=False)

        return ser_execution, 200

    @Auth.auth_required
    def put(self, idx):
        """

        :param idx:
        :type idx:
        :return:
        :rtype:
        """
        return {}, 501

    @Auth.auth_required
    def delete(self, idx):
        """

        :param string idx:
        :return:
        :rtype:
        """
        return {}, 501


class ExecutionStatusEndpoint(Resource):
    """
    Endpoint used to get the status of a certain execution that is running in the airflow webserver
    """
    @Auth.auth_required
    def get(self, idx):
        """
        API method to get the status of the execution created by the user
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str reference_id:  ID of the execution
        :return: A dictionary with a message (error if the execution does not exist or status of the execution)
        and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        status = ExecutionModel.get_execution_with_reference(idx).finished
        # TODO: call airflow to check status
        if not status:
            # Here we should call airflow to check solving status
            pass

        return {'finished': status}, 200
