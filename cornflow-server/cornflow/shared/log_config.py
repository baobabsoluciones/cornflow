

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
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '[%(asctime)s] [%(levelname)s] in %(module)s: %(message)s',
            },
            # The audit records are already JSON, so the handler emits the
            # message verbatim (one JSON object per line).
            'audit': {
                'format': '%(message)s',
            },
        },
        'handlers': {
            'wsgi': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://flask.logging.wsgi_errors_stream',
                'formatter': 'default'
            },
            'audit': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
                'formatter': 'audit',
            },
        },
        'loggers': {
            # Dedicated security audit channel, kept separate from the
            # application log so a pipeline / SIEM can collect and retain it.
            'cornflow.audit': {
                'level': 'INFO',
                'handlers': ['audit'],
                'propagate': False,
            },
        },
        'root': {
            'level': LEVEL_CONVERTER[level],
            'handlers': ['wsgi']
        }
    }