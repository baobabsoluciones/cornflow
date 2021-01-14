import os


class Development(object):
    """

    """
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    DEBUG = True
    TESTING = True
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    AIRFLOW_URL = os.getenv('AIRFLOW_URL')
    CORNFLOW_URL = os.getenv('CORNFLOW_URL')
    AIRFLOW_USER = os.getenv('AIRFLOW_USER')
    AIRFLOW_PWD = os.getenv('AIRFLOW_PWD')


class Testing(object):
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True
    TESTING = True
    SECRET_KEY = 'TESTINGSECRETKEY'
    SQLALCHEMY_DATABASE_URI = "sqlite:///cornflow_test.db"
    AIRFLOW_URL = 'http://localhost:8080'
    CORNFLOW_URL = 'http://localhost:5000'
    PRESERVE_CONTEXT_ON_EXCEPTION = False


class Production(object):
    """

    """
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    AIRFLOW_URL = os.getenv('AIRFLOW_URL')
    CORNFLOW_URL = os.getenv('CORNFLOW_URL')
    AIRFLOW_USER = os.getenv('AIRFLOW_USER')
    AIRFLOW_PWD = os.getenv('AIRFLOW_PWD')


app_config = {
    'development': Development,
    'testing': Testing,
    'production': Production
}
