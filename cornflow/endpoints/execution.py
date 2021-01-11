"""
External endpoints to manage the executions: create new ones, list all of them, get one in particular
or check the status of an ongoing one
These endpoints hve different access url, but manage the same data entities
"""

# TODO: should we have and endpoint that gets the executions from one instance, not all of them,
#  but not just one without getting the info from the instance?

# Import from libraries
from flask import request, current_app

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
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        result = self.post_list(request)

        # TODO: check result[1] before continuing! if not 20X, return.

        # To send the absolute url:
        # url_for(endpoint_name, _external=True)
        airflow_client = Airflow(current_app.config['AIRFLOW_URL'],
                                 current_app.config['AIRFLOW_USER'],
                                 current_app.config['AIRFLOW_PWD'])
        if not airflow_client.is_alive():
            return {'error': "Airflow is not accessible"}, 400
        execution_id = result[0][self.primary_key]
        try:
            airflow_client.run_dag(execution_id, current_app.config['CORNFLOW_URL'])
        except AirflowApiError as err:
            return {'error': "Airflow responded with an error: {}".format(err)}, 400

        return result


# TODO: delete an execution and its related data
class ExecutionDetailsEndpoint(MetaResource):
    """
    Endpoint used to get the information of a certain execution
    """
    def __init__(self):
        super().__init__()
        self.model = ExecutionModel
        self.query = 'get_one_execution_from_user'
        self.schema = ExecutionSchema()
        self.primary_key = 'id'
        self.foreign_data = {'instance_id': InstanceModel}

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
        # TODO: what if the reference id is wrong and it does not exist
        # TODO: if super_admin or admin should it be able to get any execution?
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        # TODO: here, the execution log progress is read correctly but parsed incorrectly by
        #  marshmallow: the arrays in the progress are converted into strings
        return self.get_detail(self.user_id, idx)

    @Auth.auth_required
    def put(self, idx):
        """
        Not implemented yet

        :param string idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return {}, 501

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
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        status = ExecutionModel.get_one_execution_from_user(self.user_id, idx).finished
        # TODO: call airflow to check status
        if not status:
            # Here we should call airflow to check solving status
            pass

        return {'finished': status}, 200
