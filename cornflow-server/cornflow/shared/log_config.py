

LEVEL_CONVERTER = {
    0: "NOTSET",
    10: "DEBUG",
    20: "INFO",
    30: "WARNING",
    40: "ERROR",
    50: "CRITICAL"
}


def log_config(level=20):
    return {
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] [%(levelname)s] in %(module)s: %(message)s',
        }},
        'handlers': {'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        }},
        'root': {
            'level': LEVEL_CONVERTER[level],
            'handlers': ['wsgi']
        }
    }