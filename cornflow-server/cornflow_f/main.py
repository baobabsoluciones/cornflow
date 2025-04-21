from fastapi import FastAPI
from cornflow_f.database import engine
from cornflow_f import models
from cornflow_f.views import users, health

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Cornflow FastAPI",
    description="Cornflow FastAPI server",
    version="0.1.0",
)

# Include routers
app.include_router(health.router)
app.include_router(users.router)
