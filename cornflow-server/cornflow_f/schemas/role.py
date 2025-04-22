"""
Role schemas definition
"""

from pydantic import BaseModel, Field


class RoleBase(BaseModel):
    """
    Base schema for role data
    """

    name: str = Field(..., min_length=1, max_length=50)
    description: str | None = None


class RoleCreate(RoleBase):
    """
    Schema for creating a new role
    """

    pass


class RoleUpdate(BaseModel):
    """
    Schema for updating a role
    """

    name: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None


class RoleResponse(RoleBase):
    """
    Schema for role response
    """

    class Config:
        """
        Pydantic config
        """

        from_attributes = True
