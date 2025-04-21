from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from cornflow_f.database import get_db
from cornflow_f.models import UserModel
from cornflow_f.schemas import UserSignup, UserResponse
from cornflow_f.security import (
    get_password_hash,
    is_disposable_email,
    validate_password,
)

# Create router for user endpoints
router = APIRouter(
    tags=["users"],
    responses={404: {"description": "Not found"}},
)


@router.post("/signup/", response_model=UserResponse, status_code=201)
async def signup(user: UserSignup, db: Session = Depends(get_db)):
    """
    Create a new user with hashed password
    """
    # Validate password
    is_valid, error_message = validate_password(user.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    # Check if email is from a disposable domain
    if is_disposable_email(user.email):
        raise HTTPException(
            status_code=400, detail="Disposable email addresses are not allowed"
        )

    # Check if username already exists
    if UserModel.exists_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already registered")

    # Check if email already exists
    if UserModel.exists_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user with hashed password
    db_user = UserModel(
        username=user.username,
        email=user.email,
        password=get_password_hash(user.password),
        first_name=user.first_name,
        last_name=user.last_name,
    )

    # Add user to database
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user
