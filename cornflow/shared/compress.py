import functools
from flask import after_this_request, current_app
from flask_compress import Compress


def compressed(f):
    """Decorator to make a view compressed"""

    @functools.wraps(f)
    def view_func(*args, **kwargs):
        def compressor(response):
            compress = current_app.extensions['compress']
            return compress.after_request(response)

        after_this_request(compressor)

        return f(*args, **kwargs)

    return view_func


def init_compress(flask_app):
    """Initialize flask_compress extension"""
    flask_app.config["COMPRESS_REGISTER"] = False  # disable default compression of all eligible requests

    compress = Compress(app=flask_app)
    flask_app.extensions['compress'] = compress

