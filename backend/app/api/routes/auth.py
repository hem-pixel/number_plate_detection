from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Header
from sqlalchemy.orm import Session

try:
    from backend.app.core.config import settings
    from backend.app.core.security import (
        verify_password,
        create_access_token,
        create_refresh_token,
        decode_token,
        revoke_token,
        check_login_rate_limit,
        record_failed_login,
        clear_failed_logins,
    )
    from backend.app.database.connection import get_db
    from backend.app.models.user import User
    from backend.app.schemas.auth import (
        LoginRequest,
        TokenResponse,
        RefreshTokenRequest,
        LogoutResponse,
    )
    from backend.app.schemas.user import UserResponse
    from backend.app.core.auth_deps import get_current_active_user, security_scheme
    from backend.app.services.user_service import UserService
except ImportError:
    from app.core.config import settings
    from app.core.security import (
        verify_password,
        create_access_token,
        create_refresh_token,
        decode_token,
        revoke_token,
        check_login_rate_limit,
        record_failed_login,
        clear_failed_logins,
    )
    from app.database.connection import get_db
    from app.models.user import User
    from app.schemas.auth import (
        LoginRequest,
        TokenResponse,
        RefreshTokenRequest,
        LogoutResponse,
    )
    from app.schemas.user import UserResponse
    from app.core.auth_deps import get_current_active_user, security_scheme
    from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Authenticate user with email & password, enforce rate limiting, and issue JWT."""
    # Determine client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_ip}:{login_data.email.lower().strip()}"

    # Check brute-force rate limit
    is_allowed, time_left = check_login_rate_limit(rate_limit_key)
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please wait {time_left} seconds before retrying.",
            headers={"Retry-After": str(time_left)}
        )

    user_service = UserService(db)
    user = user_service.get_by_email(login_data.email)

    # Constant time / secure verification - avoid disclosing whether email exists
    if not user or not verify_password(login_data.password, user.password_hash):
        record_failed_login(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact an administrator.",
        )

    # Clear failed attempts on success
    clear_failed_logins(rate_limit_key)

    # Record login timestamp
    user_service.record_login(user.id)

    # Generate tokens
    access_token = create_access_token(
        subject=user.id,
        role=user.role.value if hasattr(user.role, 'value') else str(user.role),
        email=user.email
    )
    refresh_token = create_refresh_token(
        subject=user.id
    )

    # Set secure HttpOnly cookies where supported
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production HTTPS
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    authorization: Optional[str] = Header(None)
):
    """Revoke active JWT access token and clear cookies."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if token:
        revoke_token(token)

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return LogoutResponse(message="Successfully logged out.")


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve current authenticated user details."""
    return UserResponse.model_validate(current_user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    request: Request,
    refresh_payload: Optional[RefreshTokenRequest] = None,
    db: Session = Depends(get_db)
):
    """Generate a new access token using a valid refresh token."""
    raw_token = None
    if refresh_payload and refresh_payload.refresh_token:
        raw_token = refresh_payload.refresh_token
    elif "refresh_token" in request.cookies:
        raw_token = request.cookies.get("refresh_token")

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token required.",
        )

    payload = decode_token(raw_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or no longer exists.",
        )

    new_access_token = create_access_token(
        subject=user.id,
        role=user.role.value if hasattr(user.role, 'value') else str(user.role),
        email=user.email
    )

    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )
