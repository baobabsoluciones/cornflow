from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from cornflow_f.database import get_db

# Create router for health check endpoints
router = APIRouter(
    tags=["health"],
    responses={404: {"description": "Not found"}},
)


@router.get("/health")
async def db_test(db: Session = Depends(get_db)):
    """
    Test database connection
    """
    try:
        # Try to execute a simple query using text()
        db.execute(text("SELECT 1"))
        return {"cornflow_status": "healthy"}
    except Exception as e:
        return {"cornflow_status": "unhealthy"}
