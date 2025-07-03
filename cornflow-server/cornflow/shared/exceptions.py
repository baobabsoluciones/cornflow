"""
This file contains the different exceptions created to report errors and the handler that registers them
on a flask REST API server
"""

from flask import jsonify
from webargs.flaskparser import parser
from cornflow_client.constants import AirflowError
from werkzeug.exceptions import HTTPException
import traceback

from cornflow.shared.const import DATA_DOES_NOT_EXIST_MSG


class InvalidUsage(Exception):
    """
    This is the base exception for all the defined ones
    """

    status_code = 400
    error = "Unknown error"
    log_txt = "Unknown error"

    def __init__(self, error=None, status_code=None, payload=None, log_txt=None):
        Exception.__init__(self, error)
        if error is not None:
            self.error = error
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
        if log_txt is not None:
            self.log_txt = log_txt
        else:
            self.log_txt = self.error

    def to_dict(self):
        """
        Method to convert the message to a dictionary
        :return: the error on a dictionary
        :rtype: dict
        """
        rv = dict(self.payload or ())
        rv["error"] = self.error
        return rv


class ObjectDoesNotExist(InvalidUsage):
    """
    Exception used when one object does not exist on the database
    """

    status_code = 404
    error = DATA_DOES_NOT_EXIST_MSG


class ObjectAlreadyExists(InvalidUsage):
    """
    Exception used when one object does already exist on the database
    """

    status_code = 400
    error = "The object does exist already"


class NoPermission(InvalidUsage):
    """
    Exception used when the user performing the request does not have permission to access said resource
    """

    status_code = 403
    error = "You have no permission to access the required object"


class InvalidCredentials(InvalidUsage):
    """
    Exception used when the credentials given by the user on request or log in are not valid
    """

    status_code = 400
    error = "Invalid credentials"


class EndpointNotImplemented(InvalidUsage):
    """
    Exception used when a resource is created but not implemented
    """

    status_code = 501
    error = "Endpoint not implemented"


class InvalidData(InvalidUsage):
    """
    Exception used when a request sends data to the REST API and the data is not valid
    """

    status_code = 400
    error = "The data sent is not valid"


class CommunicationError(InvalidUsage):
    """
    Exception used when there is a communication error between the REST API server and other third party components.
    """

    status_code = 400
    error = "The communication failed"


class InvalidPatch(InvalidUsage):
    """
    Exception used when a json path is not valid to be applied
    """

    status_code = 400
    error = "The json patch sent is not valid"


class ConfigurationError(InvalidUsage):
    """
    Exception used when there is an error regarding the configuration of the REST API server
    """

    status_code = 501
    error = "No authentication method configured on the server"


INTERNAL_SERVER_ERROR_MESSAGE = "500 Internal Server Error"
INTERNAL_SERVER_ERROR_MESSAGE_DETAIL = (
    "The server encountered an internal error and was unable "
    "to complete your request. Either the server is overloaded or "
    "there is an error in the application."
)


def initialize_errorhandlers(app):
    """
    Function to register the different error handlers

    :param app: the flask app where the errors have to be registered
    :return: the app after registering the error handlers
    """

    @app.errorhandler(InvalidUsage)
    @app.errorhandler(ObjectDoesNotExist)
    @app.errorhandler(ObjectAlreadyExists)
    @app.errorhandler(NoPermission)
    @app.errorhandler(InvalidCredentials)
    @app.errorhandler(EndpointNotImplemented)
    @app.errorhandler(AirflowError)
    @app.errorhandler(InvalidData)
    @app.errorhandler(InvalidPatch)
    @app.errorhandler(ConfigurationError)
    @app.errorhandler(CommunicationError)
    def handle_invalid_usage(error):
        """
        Method to handle the error given by the different exceptions.

        :param error: the raised error
        :type error: `InvalidUsage`
        :return: an HTTP response
        :rtype: `Response`
        """
        app.logger.error(error.log_txt)
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    @app.errorhandler(Exception)
    def handle_internal_server_error(error):
        """
        Method to handle all the other exceptions

        :param error: the raised error
        :type error: `Exception`
        :return: an HTTP response
        :rtype: `Response`
        """
        error_msg = f"{error.__class__.__name__}: {error}"
        error_str = f"{error.__class__.__name__}: {error}. {traceback.format_exc()}"

        status_code = 500

        # ToDo: should we leave the default behavior for HTTPExceptions ?
        if isinstance(error, HTTPException):
            # Log only the name and description of the error since it's a HTTPException
            app.logger.error(error_msg)

            # For HTTPExceptions we keep the associated messages
            #     but return them as json instead of html

            # HTTPExceptions sometimes already have an associated status code
            status_code = error.code or status_code
            error_msg = f"{status_code} {error.name or INTERNAL_SERVER_ERROR_MESSAGE}"
            error_str = f"{error_msg}. {str(error.description or '') or INTERNAL_SERVER_ERROR_MESSAGE_DETAIL}"
            response_dict = {"message": error_msg, "error": error_str}
            response = jsonify(response_dict)

        elif app.config["ENV"] == "production":
            # Log the entire traceback
            app.logger.error(error_str)

            # We are in production: we return generic messages
            #    to avoid giving away sensitive information

            response_dict = {
                "message": INTERNAL_SERVER_ERROR_MESSAGE,
                "error": INTERNAL_SERVER_ERROR_MESSAGE_DETAIL,
            }
            response = jsonify(response_dict)
        else:
            # Log the entire traceback
            app.logger.error(error_str)

            # Testing or development: we return the full error
            response = jsonify(dict(message=error_msg, error=error_str))

        response.status_code = status_code
        return response

    return app


# This error handler is necessary for usage with Flask-RESTful
@parser.error_handler
def handle_request_parsing_error(err, req, schema, *, error_status_code, error_headers):
    """
    webargs error handler that uses Flask-RESTful's abort function to return
    a JSON error response to the client.
    """
    raise InvalidUsage(
        error=str(err.normalized_messages()), status_code=error_status_code
    )
