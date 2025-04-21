"""
Authentication views
"""

from datetime import datetime, timedelta, UTC
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session
from cornflow_f.database import get_db
from cornflow_f.models.user import UserModel
from cornflow_f.schemas.auth import LoginRequest, LoginResponse
from cornflow_f.security import verify_password
from cornflow_f.config import get_config

# Get configuration
config = get_config()

router = APIRouter(tags=["auth"])

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """
    Create a new JWT token
    """
    to_encode = data.copy()
    now = datetime.now(UTC)

    expire = now + expires_delta

    to_encode.update({"exp": expire, "iat": now, "iss": config.JWT_ISSUER})
    encoded_jwt = jwt.encode(
        to_encode, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM
    )
    return encoded_jwt


@router.post("/login/", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login endpoint that validates credentials and returns a JWT token
    """
    # Get user from database
    user = UserModel.get_by_username(db, request.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(hours=config.JWT_ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return LoginResponse(access_token=access_token, id=user.uuid)
