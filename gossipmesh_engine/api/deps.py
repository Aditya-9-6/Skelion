from datetime import timedelta
from gossipmesh.models.session import UserSession
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt

from gossipmesh.core.config import settings
from gossipmesh.db.session import get_db
from gossipmesh.models.user import User
from gossipmesh.models.api_key import APIKey

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login/access-token")


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
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
        user_id: str = payload.get("sub")
        session_id: str = payload.get("sid")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception

    if session_id:
        session = (
            db.query(UserSession)
            .filter(UserSession.id == int(session_id), UserSession.user_id == user.id, UserSession.is_active == True)
            .first()
        )
        if not session:
            raise credentials_exception

    return user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_api_key(api_key_header: str = Depends(OAuth2PasswordBearer(tokenUrl="token", auto_error=False)), db: Session = Depends(get_db)) -> APIKey:
    if not api_key_header:
        raise HTTPException(status_code=401, detail="API Key missing")
    
    if api_key_header.startswith("gm_"):
        prefix = api_key_header[:8]
        api_key = (
            db.query(APIKey)
            .filter(APIKey.prefix == prefix, not APIKey.is_revoked)
            .first()
        )
    else:
        raw_token = api_key_header
        api_key = (
            db.query(APIKey)
            .filter(APIKey.prefix == raw_token, not APIKey.is_revoked)
            .first()
        }
    
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key
