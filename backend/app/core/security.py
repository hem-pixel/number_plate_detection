import re
import time
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple, Set
from collections import defaultdict
from fastapi import HTTPException, status

from .config import settings
from .logging import get_logger

logger = get_logger("security")

# Set of revoked token identifiers (JTI or raw token hashes)
_REVOKED_TOKENS: Set[str] = set()

# In-memory login attempt tracker for rate limiting: key -> [(timestamp)]
_LOGIN_ATTEMPTS: Dict[str, list] = defaultdict(list)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with salt rounds = 12."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Safely verifies a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validates that a password satisfies strong password policies:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special symbol
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]]", password):
        return False, "Password must contain at least one special character."
    return True, ""


def create_access_token(
    data: Optional[dict] = None,
    expires_delta: Optional[timedelta] = None,
    subject: Optional[object] = None,
    role: Optional[str] = None,
    email: Optional[str] = None,
    **kwargs
) -> str:
    """Creates a signed JWT access token supporting both dict payloads and keyword arguments."""
    to_encode = data.copy() if data else {}
    if subject is not None:
        to_encode["sub"] = str(subject)
    if role is not None:
        to_encode["role"] = role
    if email is not None:
        to_encode["email"] = email
    to_encode.update(kwargs)

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
    })
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(
    data: Optional[dict] = None,
    expires_delta: Optional[timedelta] = None,
    subject: Optional[object] = None,
    **kwargs
) -> str:
    """Creates a signed JWT refresh token supporting both dict payloads and keyword arguments."""
    to_encode = data.copy() if data else {}
    if subject is not None:
        to_encode["sub"] = str(subject)
    to_encode.update(kwargs)

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "refresh",
    })
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_token(token: str, expected_type: Optional[str] = None) -> dict:
    """
    Decodes and validates a JWT token.
    Raises HTTPException 401 if invalid, expired, or revoked.
    """
    if token in _REVOKED_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked or invalidated. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        token_type = payload.get("type")
        if expected_type and token_type != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected '{expected_type}', got '{token_type}'.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def revoke_token(token: str) -> None:
    """Adds a token to the revocation list."""
    if token:
        _REVOKED_TOKENS.add(token)


def is_token_revoked(token: str) -> bool:
    """Checks if token has been revoked."""
    return token in _REVOKED_TOKENS


# -------------------------------------------------------------
# Rate Limiting & Brute-Force Protection
# -------------------------------------------------------------

def check_login_rate_limit(client_identifier: str) -> Tuple[bool, int]:
    """
    Checks if client has exceeded maximum allowed failed login attempts.
    Returns (True, 0) if allowed, or (False, retry_after_seconds) if rate limited.
    """
    now = time.time()
    window = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
    max_attempts = settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS

    attempts = _LOGIN_ATTEMPTS[client_identifier]
    # Prune attempts outside window
    recent_attempts = [t for t in attempts if now - t < window]
    _LOGIN_ATTEMPTS[client_identifier] = recent_attempts

    if len(recent_attempts) >= max_attempts:
        retry_after = int(window - (now - recent_attempts[0])) + 1
        logger.warning(f"Rate limit exceeded for client: {client_identifier}")
        return False, max(1, retry_after)
    return True, 0


def record_failed_login(client_identifier: str) -> None:
    """Records a failed login attempt for the client identifier."""
    now = time.time()
    _LOGIN_ATTEMPTS[client_identifier].append(now)


def clear_failed_logins(client_identifier: str) -> None:
    """Resets failed login attempts upon successful authentication."""
    if client_identifier in _LOGIN_ATTEMPTS:
        _LOGIN_ATTEMPTS.pop(client_identifier, None)
