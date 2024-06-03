"""
Endpoints for getting the cornflow and airflow version
"""
# Imports from external libraries
from flask import current_app
from flask_apispec import doc
from importlib.metadata import version

# Imports from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import ADMIN_ROLE
from cornflow.__version__ import VERSION


class VersionEndpoint(BaseMetaResource):
    """
    Endpoint with a get method which gives back the cornflow and airflow version.
    """

    ROLES_WITH_ACCESS = [ADMIN_ROLE]

    def __init__(self):
        super().__init__()

    @doc(description="Get cornflow version", tags=["Version"])
    @authenticate(auth_class=Auth())
    def get(self):
        """
        API (GET) method to get the cornflow and airflow version
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by the superuser

        :return: A dictionary with the cornflow and airflow version and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """

        current_app.logger.info(f"User {self.get_user()} gets cornflow and airflow version")
        return {"cornflow_version": VERSION, "airflow_version": version("apache-airflow")}

