from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from gossipmesh_engine.db.session import SessionLocal
from gossipmesh.models.user import User
from gossipmesh.models.api_key import APIKey

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login/access-token")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    from gossipmesh.core.security import jwt, settings

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
        user_id: str = payload.get("sub")
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
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return user


def get_api_key_user(
    api_key_token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if api_key_token.startswith("skl_live_"):
        prefix = api_key_token[:12]
        api_key = (
            db.query(APIKey)
            .filter(APIKey.prefix == prefix, not APIKey.is_revoked)
            .first()
        )
        if api_key:
            return api_key.user

    raw_token = api_key_token
    api_key = (
        db.query(APIKey)
        .filter(APIKey.prefix == raw_token, not APIKey.is_revoked)
        .first()
    )
    if api_key:
        return api_key.user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )
