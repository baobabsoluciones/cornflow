from flask import jsonify
from webargs.flaskparser import parser


class InvalidUsage(Exception):
    status_code = 400
    error = "Unknown error"

    def __init__(self, error=None, status_code=None, payload=None):
        Exception.__init__(self)
        if error is not None:
            self.error = error
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["error"] = self.error
        return rv


class InvalidCredentials(InvalidUsage):
    status_code = 400
    error = "Invalid credentials"


def initialize_errorhandlers(app):
    @app.errorhandler(InvalidUsage)
    @app.errorhandler(InvalidCredentials)
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
