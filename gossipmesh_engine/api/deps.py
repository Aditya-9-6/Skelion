from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt

from gossipmesh_engine.db.session import get_db
from gossipmesh_engine.models.user import User
from gossipmesh_engine.models.api_key import APIKey
from gossipmesh_engine.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login/access-token", auto_error=False
)


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


def get_api_key_user(
    api_key_header: str = Depends(
        OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
    ),
    db: Session = Depends(get_db),
) -> User:
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key missing"
        )
    if api_key_header.startswith("skl_live_"):
        parts = api_key_header.split("_")
        if len(parts) >= 3:
            prefix = parts[2][:8]
            api_key = (
                db.query(APIKey)
                .filter(APIKey.prefix == prefix, not APIKey.is_revoked)
                .first()
            )
            if api_key and api_key.user:
                return api_key.user

    raw_token = api_key_header
    api_key = (
        db.query(APIKey)
        .filter(APIKey.prefix == raw_token, not APIKey.is_revoked)
        .first()
    )
    if api_key and api_key.user:
        return api_key.user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key"
    )
