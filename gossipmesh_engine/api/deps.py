from typing import Generator, Any, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import timedelta
from gossipmesh.models.session import UserSession

from gossipmesh.db.session import SessionLocal
from gossipmesh.models.user import User
from gossipmesh.models.api_key import APIKey
from gossipmesh.core.security import verify_password

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/access-token", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        }
    try:
        import jwt
        from gossipmesh.core.config import settings
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


def get_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> APIKey:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
        }
    
    if x_api_key.startswith("gm_live_"):
        prefix = x_api_key[:12]
        api_key = (
            db.query(APIKey)
            .filter(APIKey.prefix == prefix, not APIKey.is_revoked)
            .first()
        )
    else:
        raw_token = x_api_key
        api_key = (
            db.query(APIKey)
            .filter(APIKey.prefix == raw_token, not APIKey.is_revoked)
            .first()
        )
        
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API Key",
        }
    return api_key
