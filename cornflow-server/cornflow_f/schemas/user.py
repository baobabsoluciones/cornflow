"""
User schema definitions
"""

from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional


class UserBase(BaseModel):
    """
    Base user schema
    """

    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserSignup(UserBase):
    """
    User signup schema
    """

    password: str


class UserResponse(UserBase):
    """
    User response schema
    """

    uuid: str = Field(..., serialization_alias="id")
    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    """
    Schema for user profile updates
    """

    username: str | None = None
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    password: str | None = None
