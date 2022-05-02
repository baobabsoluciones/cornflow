"""
This file implements the decorator to compress the results of a request
and the function to register the compression in the flask app
"""
import functools
from flask import after_this_request, current_app
from flask_compress import Compress


def compressed(f):
    """
    Decorator to make a view compressed
    :param callable f: function to be compressed
    """

    @functools.wraps(f)
    def view_func(*args, **kwargs):
        """

        :param args: the original args sent to the decorated function
        :param kwargs: the original kwargs sent to the decorated function
        """

        def compressor(response):
            """
            Function executed in the decorator

            :param response: the response given by the decorated function (an HTTP response)
            :return: the response compressed
            """
            compress = current_app.extensions["compress"]
            return compress.after_request(response)

        after_this_request(compressor)

        return f(*args, **kwargs)

    return view_func


def init_compress(flask_app):
    """Initialize flask_compress extension"""
    flask_app.config[
        "COMPRESS_REGISTER"
    ] = False  # disable default compression of all eligible requests

    compress = Compress(app=flask_app)
    flask_app.extensions["compress"] = compress
