"""
Role views definition
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from cornflow_f.database import get_db
from cornflow_f.models.role import RoleModel
from cornflow_f.schemas.role import RoleCreate, RoleUpdate, RoleResponse
from cornflow_f.views.auth import oauth2_scheme
from cornflow_f.utils.query_utils import get_all_records

router = APIRouter(tags=["roles"])


@router.get("/roles", response_model=List[RoleResponse])
def get_roles(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    """
    Get all roles
    """
    roles = get_all_records(db, RoleModel)

    return roles


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    role: RoleCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    """
    Create a new role
    """
    if RoleModel.exists_by_name(db, role.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists",
        )

    db_role = RoleModel(**role.model_dump())
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


@router.patch("/roles/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    role: RoleUpdate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """
    Update a role
    """
    db_role = (
        db.query(RoleModel)
        .filter(RoleModel.id == role_id, RoleModel.deleted_at.is_(None))
        .first()
    )

    if not db_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    if (
        role.name
        and role.name != db_role.name
        and RoleModel.exists_by_name(db, role.name)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists",
        )

    for field, value in role.model_dump(exclude_unset=True).items():
        setattr(db_role, field, value)

    db.commit()
    db.refresh(db_role)
    return db_role


@router.put("/roles/{role_id}", response_model=RoleResponse)
def replace_role(
    role_id: int,
    role: RoleCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """
    Replace a role
    """
    db_role = (
        db.query(RoleModel)
        .filter(RoleModel.id == role_id, RoleModel.deleted_at.is_(None))
        .first()
    )

    if not db_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    if role.name != db_role.name and RoleModel.exists_by_name(db, role.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists",
        )

    for field, value in role.model_dump().items():
        setattr(db_role, field, value)

    db.commit()
    db.refresh(db_role)
    return db_role


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    """
    Delete a role
    """
    db_role = (
        db.query(RoleModel)
        .filter(RoleModel.id == role_id, RoleModel.deleted_at.is_(None))
        .first()
    )

    if not db_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    db_role.soft_delete(db=db)
    return None
