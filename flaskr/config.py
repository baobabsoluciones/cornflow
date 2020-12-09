import os


class Development(object):
    """

    """
    DEBUG = True
    TESTING = True
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    AIRFLOW_URL = os.getenv('AIRFLOW_URL')
    CORNFLOW_URL = os.getenv('CORNFLOW_URL')

class Testing(object):
    DEBUG = True
    TESTING = True
    SECRET_KEY = 'TESTINGSECRETKEY'
    SQLALCHEMY_DATABASE_URI = 'postgres://postgres:postgresadmin@127.0.0.1:5432/cornflow_test'
    AIRFLOW_URL = os.getenv('AIRFLOW_URL')
    CORNFLOW_URL = os.getenv('CORNFLOW_URL')
    PRESERVE_CONTEXT_ON_EXCEPTION = False


class Production(object):
    """

    """
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    AIRFLOW_URL = os.getenv('AIRFLOW_URL')
    CORNFLOW_URL = os.getenv('CORNFLOW_URL')

app_config = {
    'development': Development,
    'testing': Testing,
    'production': Production
}
