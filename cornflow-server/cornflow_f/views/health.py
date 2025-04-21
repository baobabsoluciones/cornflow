from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from cornflow_f.database import get_db

# Create router for health check endpoints
router = APIRouter(
    tags=["health"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
async def root():
    """
    Root endpoint
    """
    return {"message": "Hello World"}


@router.get("/hello/{name}/")
async def hello(name: str):
    """
    Hello endpoint
    """
    return {"message": f"Hello {name}"}


@router.get("/db/")
async def db_test(db: Session = Depends(get_db)):
    """
    Test database connection
    """
    try:
        # Try to execute a simple query using text()
        db.execute(text("SELECT 1"))
        return {"message": "Database connection successful"}
    except Exception as e:
        return {"message": f"Database connection failed: {str(e)}"}
