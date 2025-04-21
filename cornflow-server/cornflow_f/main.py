from fastapi import FastAPI
from cornflow_f.database import engine, Base
from cornflow_f.views import users, health, auth
from cornflow_f.config import get_config

# Get configuration
config = get_config()

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=config.APP_NAME,
    description=config.APP_DESCRIPTION,
    version=config.APP_VERSION,
    debug=config.DEBUG,
)

# Include routers
app.include_router(health.router)
app.include_router(users.router)
app.include_router(auth.router)
