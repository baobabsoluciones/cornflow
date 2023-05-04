# Imports from libraries
from flask_apispec import doc

# Imports from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import VIEWER_ROLE, PLANNER_ROLE, ADMIN_ROLE
from cornflow.shared.licenses import get_licenses_summary


class LicensesEndpoint(BaseMetaResource):
    """
    Endpoint used to obtain data about library licenses.

    Available methods: [get]
    Endpoint used by: the user interface.
    """
    ROLES_WITH_ACCESS = [VIEWER_ROLE, PLANNER_ROLE, ADMIN_ROLE]

    def __init__(self):
        super().__init__()

    @doc(
        description="Get list of all the libraries and their license information",
        tags=["Licenses"],
    )
    @authenticate(auth_class=Auth())
    def get(self):
        return get_licenses_summary(), 200
