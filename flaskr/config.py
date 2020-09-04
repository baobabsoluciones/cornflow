import os


class Development(object):
    """

    """
    DEBUG = True
    TESTING = True
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    AIRFLOW_URL = os.getenv('AIRFLOW_URL')

class Production(object):
    """

    """
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    AIRFLOW_URL = os.getenv('AIRFLOW_URL')


app_config = {
    'development': Development,
    'production': Production
}
