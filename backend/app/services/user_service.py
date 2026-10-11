from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from backend.app.models.user import User, UserRole
    from backend.app.schemas.user import UserCreate, UserUpdate, UserPasswordReset
    from backend.app.core.security import hash_password, validate_password_strength
except ImportError:
    from app.models.user import User, UserRole
    from app.schemas.user import UserCreate, UserUpdate, UserPasswordReset
    from app.core.security import hash_password, validate_password_strength


class UserServiceException(ValueError):
    """Base exception for user service errors."""
    pass


class UserNotFoundException(UserServiceException):
    pass


class EmailAlreadyExistsException(UserServiceException):
    pass


class LastAdminProtectionException(UserServiceException):
    """Raised when an operation would leave the system with zero active administrators."""
    pass


class PasswordValidationException(UserServiceException):
    pass


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(func.lower(User.email) == email.lower().strip()).first()

    def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        return self.db.query(User).order_by(User.id.asc()).offset(skip).limit(limit).all()

    def count_active_admins(self) -> int:
        return self.db.query(User).filter(
            User.role == UserRole.ADMIN,
            User.is_active == True
        ).count()

    def create_user(self, user_data: Optional[UserCreate] = None, **kwargs) -> User:
        if user_data is None:
            user_data = UserCreate(**kwargs)

        # Validate email uniqueness
        existing = self.get_by_email(user_data.email)
        if existing:
            raise EmailAlreadyExistsException(f"User with email '{user_data.email}' already exists.")

        # Validate password strength
        is_strong, reason = validate_password_strength(user_data.password)
        if not is_strong:
            raise PasswordValidationException(reason)

        hashed_pw = hash_password(user_data.password)
        is_active = kwargs.get("is_active", getattr(user_data, "is_active", True))

        user = User(
            email=user_data.email.lower().strip(),
            password_hash=hashed_pw,
            full_name=user_data.full_name.strip(),
            role=user_data.role,
            is_active=is_active
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user_id: int, update_data: UserUpdate) -> User:
        user = self.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found.")

        # Check last active admin protection if deactivating or changing role
        if (
            (update_data.is_active is False and user.is_active is True and user.role == UserRole.ADMIN) or
            (update_data.role and update_data.role != UserRole.ADMIN and user.role == UserRole.ADMIN and user.is_active is True)
        ):
            if self.count_active_admins() <= 1:
                raise LastAdminProtectionException("Cannot deactivate or demote the last active administrator.")

        # Check email uniqueness if changing email
        if update_data.email and update_data.email.lower().strip() != user.email.lower():
            existing = self.get_by_email(update_data.email)
            if existing and existing.id != user_id:
                raise EmailAlreadyExistsException(f"Email '{update_data.email}' is already in use.")
            user.email = update_data.email.lower().strip()

        if update_data.full_name is not None:
            user.full_name = update_data.full_name.strip()

        if update_data.role is not None:
            user.role = update_data.role

        if update_data.is_active is not None:
            user.is_active = update_data.is_active

        self.db.commit()
        self.db.refresh(user)
        return user

    def set_user_status(self, user_id: int, is_active: bool) -> User:
        user = self.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found.")

        if not is_active and user.is_active and user.role == UserRole.ADMIN:
            if self.count_active_admins() <= 1:
                raise LastAdminProtectionException("Cannot deactivate the last active administrator.")

        user.is_active = is_active
        self.db.commit()
        self.db.refresh(user)
        return user

    def reset_password(self, user_id: int, reset_data: UserPasswordReset) -> User:
        user = self.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found.")

        is_strong, reason = validate_password_strength(reset_data.new_password)
        if not is_strong:
            raise PasswordValidationException(reason)

        user.password_hash = hash_password(reset_data.new_password)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found.")

        if user.role == UserRole.ADMIN and user.is_active:
            if self.count_active_admins() <= 1:
                raise LastAdminProtectionException("Cannot delete the last active administrator.")

        self.db.delete(user)
        self.db.commit()
        return True

    def record_login(self, user_id: int) -> None:
        user = self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.now(timezone.utc)
            self.db.commit()
