from datetime import timedelta
from typing import Generator, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt

from gossipmesh.core.config import settings
from gossipmesh.core.exceptions import AuthenticationError, AuthorizationError
from gossipmesh.db.session import SessionLocal
from gossipmesh.models.user import User
from gossipmesh.models.api_key import APIKey
from gossipmesh.models.session import UserSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login/access-token", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    if not token:
        raise AuthenticationError(message="Not authenticated", status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        }
        user_id: str = payload.get("sub")
        session_id: str = payload.get("sid")
        if user_id is None:
            raise AuthenticationError(message="Could not validate credentials", status_code=status.HTTP_401_UNAUTHORIZED)
    except (jwt.PyJWTError, Exception):
        raise AuthenticationError(message="Could not validate credentials", status_code=status.HTTP_401_UNAUTHORIZED)

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise AuthenticationError(message="User not found", status_code=status.HTTP_401_UNAUTHORIZED)
    if not user.is_active:
        raise AuthorizationError(message="Inactive user", status_code=status.HTTP_403_FORBIDDEN)

    if session_id:
        session = db.query(UserSession).filter(UserSession.id == int(session_id)).first()
        if not session or not session.is_active:
            raise AuthenticationError(message="Session terminated or inactive", status_code=status.HTTP_401_UNAUTHORIZED)

    return user


def get_current_active_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not getattr(current_user, "is_superuser", False):
        raise AuthorizationError(message="The user doesn't have enough privileges", status_code=status.HTTP_403_FORBIDDEN)
    return current_user


def verify_api_key_header(api_key_header: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not api_key_header:
        raise AuthenticationError(message="API key missing", status_code=status.HTTP_401_UNAUTHORIZED)
    
    # Check if format is prefix.secret
    if "." in api_key_header:
        prefix, secret = api_key_header.split(".", 1)
        api_key = (
            db.query(APIKey)
            .filter(APIKey.prefix == prefix, ~APIKey.is_revoked)
            .first()
        )
    else:
        raw_token = api_key_header
        api_key = (
            db.query(APIKey)
            .filter(APIKey.prefix == raw_token, ~APIKey.is_revoked)
            .first()
        )

    if not api_key:
        raise AuthenticationError(message="Invalid API key", status_code=status.HTTP_401_UNAUTHORIZED)

    from gossipmesh.core.security import verify_password
    if not verify_password(api_key_header, api_key.hashed_key) and not verify_password(api_key_header if '.' not in api_key_header else secret, api_key.hashed_key):
        raise AuthenticationError(message="Invalid API key secret", status_code=status.HTTP_401_UNAUTHORIZED)

    user = db.query(User).filter(User.id == api_key.user_id).first()
    if not user or not user.is_active:
        raise AuthenticationError(message="API key owner inactive or not found", status_code=status.HTTP_401_UNAUTHORIZED)
    return user
