from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from cornflow_f.database import get_db
from cornflow_f.models import UserModel
from cornflow_f.schemas import UserSignup, UserResponse, UserUpdateRequest
from cornflow_f.security import (
    get_password_hash,
    is_disposable_email,
    validate_password,
    verify_password,
)
from cornflow_f.views.auth import oauth2_scheme
from jose import JWTError, jwt
from cornflow_f.config import get_config
from cornflow_f.utils.query_utils import get_all_records
from cornflow_f.shared.const import ADMIN_ROLE_ID, SERVICE_ROLE_ID

# Get configuration
config = get_config()

# Create router for user endpoints
router = APIRouter(
    tags=["users"],
    responses={404: {"description": "Not found"}},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> UserModel:
    """
    Get the current user from the JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM]
        )
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = UserModel.get_by_username(db, username)
    if user is None:
        raise credentials_exception
    return user


@router.post("/signup", response_model=UserResponse, status_code=201)
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


@router.patch("/user/{user_id}", response_model=UserResponse)
async def update_profile(
    user_id: str,
    user_update: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Update user profile information
    """
    # Check if user is admin or service user
    is_admin = current_user.has_role(db, ADMIN_ROLE_ID)
    is_service_user = current_user.has_role(db, SERVICE_ROLE_ID)

    # Verify user is updating their own profile
    if current_user.uuid != user_id and not is_admin and not is_service_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this profile",
        )

    # If updating password, verify current password and check permissions
    if user_update.password:
        if not is_service_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only service users can update passwords",
            )

        # Validate new password
        is_valid, error_message = validate_password(user_update.password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)

        current_user.password = get_password_hash(user_update.password)

    # If updating email, check if it's valid and not already in use
    if user_update.email and user_update.email != current_user.email:
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update email addresses",
            )

        if is_disposable_email(user_update.email):
            raise HTTPException(
                status_code=400, detail="Disposable email addresses are not allowed"
            )

        if UserModel.exists_by_email(db, user_update.email):
            raise HTTPException(status_code=400, detail="Email already registered")

        current_user.email = user_update.email

    # If updating username, check if it's not already in use
    if user_update.username and user_update.username != current_user.username:
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update usernames",
            )

        if UserModel.exists_by_username(db, user_update.username):
            raise HTTPException(status_code=400, detail="Username already registered")

        current_user.username = user_update.username

    # Update optional fields (first_name and last_name)
    if user_update.first_name is not None:
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update first name",
            )
        current_user.first_name = user_update.first_name
    if user_update.last_name is not None:
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update last name",
            )
        current_user.last_name = user_update.last_name

    # Save changes
    db.commit()
    db.refresh(current_user)

    return current_user


@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get a list of all users
    """
    # Use the generic function instead of writing the query directly
    users = get_all_records(db, UserModel)

    return users
