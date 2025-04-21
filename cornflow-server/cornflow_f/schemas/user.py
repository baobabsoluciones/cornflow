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


class UserSignup(UserBase):
    """
    User signup schema
    """

    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserResponse(UserBase):
    """
    User response schema
    """

    uuid: str = Field(..., serialization_alias="id")
    model_config = ConfigDict(from_attributes=True)
