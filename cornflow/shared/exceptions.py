"""

"""
from cornflow_client.constants import InvalidUsage, AirflowError
from flask import jsonify
from webargs.flaskparser import parser


class ObjectDoesNotExist(InvalidUsage):
    status_code = 404
    error = "The object does not exist"


class NoPermission(InvalidUsage):
    status_code = 403
    error = "You have no permission to access the required object"


class InvalidCredentials(InvalidUsage):
    status_code = 400
    error = "Invalid credentials"


class EndpointNotImplemented(InvalidUsage):
    status_code = 501
    error = "Endpoint not implemented"


class InvalidData(InvalidUsage):
    status_code = 400
    error = "The data sent is not valid"


class InvalidPatch(InvalidUsage):
    status_code = 400
    error = "The json patch sent is not valid"


def _initialize_errorhandlers(app):
    @app.errorhandler(InvalidUsage)
    @app.errorhandler(ObjectDoesNotExist)
    @app.errorhandler(NoPermission)
    @app.errorhandler(InvalidCredentials)
    @app.errorhandler(EndpointNotImplemented)
    @app.errorhandler(AirflowError)
    def handle_invalid_usage(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    return app


# This error handler is necessary for usage with Flask-RESTful
@parser.error_handler
def handle_request_parsing_error(err, req, schema, *, error_status_code, error_headers):
    """webargs error handler that uses Flask-RESTful's abort function to return
    a JSON error response to the client.
    """
    raise InvalidUsage(
        error=str(err.normalized_messages()), status_code=error_status_code
    )
