import os


class Development(object):
    """

    """
    DEBUG = True
    TESTING = True
    # SECRET_KEY = os.getenv('SECRET_KEY')
    SECRET_KEY = "THISNEEDSTOBECHANGED"
    # SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_DATABASE_URI = "postgres://postgres:postgresadmin@127.0.0.1:5432/cornflow"


class Production(object):
    """

    """
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')


app_config = {
    'development': Development,
    'production': Production
}
