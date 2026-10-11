from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

try:
    from backend.app.database.connection import get_db
    from backend.app.models.user import User
    from backend.app.schemas.user import (
        UserCreate,
        UserUpdate,
        UserStatusUpdate,
        UserPasswordReset,
        UserResponse,
    )
    from backend.app.core.auth_deps import require_admin
    from backend.app.services.user_service import (
        UserService,
        UserNotFoundException,
        EmailAlreadyExistsException,
        LastAdminProtectionException,
        PasswordValidationException,
    )
except ImportError:
    from app.database.connection import get_db
    from app.models.user import User
    from app.schemas.user import (
        UserCreate,
        UserUpdate,
        UserStatusUpdate,
        UserPasswordReset,
        UserResponse,
    )
    from app.core.auth_deps import require_admin
    from app.services.user_service import (
        UserService,
        UserNotFoundException,
        EmailAlreadyExistsException,
        LastAdminProtectionException,
        PasswordValidationException,
    )

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("", response_model=List[UserResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all user accounts in the system (ADMIN only)."""
    service = UserService(db)
    return service.list_users(skip=skip, limit=limit)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new user account with specified role (ADMIN only)."""
    service = UserService(db)
    try:
        user = service.create_user(user_in)
        return user
    except EmailAlreadyExistsException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PasswordValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Retrieve details of a specific user (ADMIN only)."""
    service = UserService(db)
    user = service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found.")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user information, role, or active status (ADMIN only)."""
    service = UserService(db)
    try:
        updated = service.update_user(user_id, user_update)
        return updated
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EmailAlreadyExistsException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except LastAdminProtectionException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch("/{user_id}/status", response_model=UserResponse)
def set_user_status(
    user_id: int,
    status_in: UserStatusUpdate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Activate or deactivate a user account (ADMIN only)."""
    service = UserService(db)
    try:
        updated = service.set_user_status(user_id, status_in.is_active)
        return updated
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except LastAdminProtectionException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{user_id}/reset-password", response_model=UserResponse)
def reset_user_password(
    user_id: int,
    reset_in: UserPasswordReset,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Reset a user's password with strong password enforcement (ADMIN only)."""
    service = UserService(db)
    try:
        updated = service.reset_password(user_id, reset_in)
        return updated
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PasswordValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a user account (ADMIN only; cannot delete the last active administrator)."""
    service = UserService(db)
    try:
        service.delete_user(user_id)
        return None
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except LastAdminProtectionException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
