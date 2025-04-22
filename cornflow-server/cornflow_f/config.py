"""
Configuration module for the FastAPI application
"""

import os


class Config:
    """
    Base configuration class
    """

    # Application settings
    APP_NAME = os.getenv("CORNFLOW_APP_NAME", "Cornflow FastAPI")
    APP_VERSION = os.getenv("CORNFLOW_APP_VERSION", "0.1.0")
    APP_DESCRIPTION = os.getenv("CORNFLOW_APP_DESCRIPTION", "Cornflow FastAPI server")

    # Security settings
    SECRET_KEY = os.getenv("SECRET_KEY", "THISNEEDSTOBECHANGED")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_HOURS = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_HOURS", 24)
    JWT_ISSUER = os.getenv("JWT_ISSUER", "cornflow-api")

    # Database settings
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cornflow.db")

    # API settings
    API_PREFIX = os.getenv("API_PREFIX", "")
    DEBUG = os.getenv("DEBUG", False)
    TESTING = os.getenv("TESTING", False)


class DevelopmentConfig(Config):
    """
    Development configuration
    """

    DEBUG = True
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cornflow.db")


class TestingConfig(Config):
    """
    Testing configuration
    """

    TESTING = True
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")


class ProductionConfig(Config):
    """
    Production configuration
    """

    # Override secret key in production
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is required in production")

    # Use environment variable for database URL in production
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is required in production")


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config():
    """
    Get the configuration based on the environment
    """
    env = os.getenv("CORNFLOW_ENV", "default")
    print(f"Using environment: {env}")
    return config[env]()
