"""
Authentication schemas
"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """
    Login request schema
    """

    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)


class LoginResponse(BaseModel):
    """
    Login response schema with JWT token
    """

    access_token: str
    token_type: str = "bearer"
    id: str
