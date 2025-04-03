from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.schemas.user import User, UserUpdate
from app.services.user import UserService

router = APIRouter()


@router.get(
    "/",
    response_model=List[User],
    responses={
        200: {"description": "List of users"},
        401: {"description": "Missing or invalid token"},
        403: {"description": "Not enough permissions"},
    },
    openapi_extra={"security": [{"Bearer": []}]},
)
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    user_service = UserService(db)
    return user_service.get_users(skip=skip, limit=limit)


@router.get(
    "/{user_id}",
    response_model=User,
    responses={
        200: {"description": "User details"},
        401: {"description": "Missing or invalid token"},
        403: {"description": "Not enough permissions"},
        404: {"description": "User not found"},
    },
    openapi_extra={"security": [{"Bearer": []}]},
)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    user_service = UserService(db)
    db_user = user_service.get_user(user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put(
    "/{user_id}",
    response_model=User,
    responses={
        200: {"description": "Updated user"},
        401: {"description": "Missing or invalid token"},
        403: {"description": "Not enough permissions"},
        404: {"description": "User not found"},
    },
    openapi_extra={"security": [{"Bearer": []}]},
)
def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    user_service = UserService(db)
    db_user = user_service.update_user(user_id, user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.delete(
    "/{user_id}",
    response_model=User,
    responses={
        200: {"description": "Deleted user"},
        401: {"description": "Missing or invalid token"},
        403: {"description": "Not enough permissions"},
        404: {"description": "User not found"},
    },
    openapi_extra={"security": [{"Bearer": []}]},
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    user_service = UserService(db)
    db_user = user_service.delete_user(user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user
