"""
Endpoint that explains the codes (execution states, solution status, ...) found in the responses.
"""

from flask_apispec import doc, marshal_with

from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.schemas.constants import ConstantsResponse
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import ALL_DEFAULT_ROLES
from cornflow.shared.constants_catalog import get_constants_catalog


class ConstantsEndpoint(BaseMetaResource):
    """
    Endpoint used to know what the codes of the API mean.

    Available methods: [get]
    """

    ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES

    @doc(
        description="Get the meaning of the codes used in the responses: execution "
        "states (state), solution status (sol_code), solver status (status_code) "
        "and execution files status",
        tags=["Constants"],
    )
    @authenticate(auth_class=Auth())
    @marshal_with(ConstantsResponse)
    def get(self):
        return get_constants_catalog(), 200
