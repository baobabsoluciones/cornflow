# Imports from libraries
from cornflow_core.authentication import authenticate
from cornflow_core.resources import BaseMetaResource
from flask_apispec import doc
from ..shared.licenses import get_licenses_summary
from ..shared.authentication import Auth


class LicensesEndpoint(BaseMetaResource):
    """
    Endpoint used to obtain data about library licenses.

    Available methods: [get]
    Endpoint used by: the user interface.
    """

    def __init__(self):
        super().__init__()

    @doc(
        description="Get list of all the libraries and their license information",
        tags=["Licenses"],
    )
    @authenticate(auth_class=Auth())
    def get(self):
        return get_licenses_summary(), 200
