# skelion_agent/auth.py – Helper utilities for password hashing and JWT handling

"""Authentication utilities used by the FastAPI auth router.

- Passwords are hashed with ``passlib``'s bcrypt scheme.
- JWTs are signed using a secret key from the environment (``JWT_SECRET_KEY``).
- The token expiry (in minutes) is also configurable via ``ACCESS_TOKEN_EXPIRE_MINUTES``.

These helpers are deliberately tiny – the heavy lifting (model definitions,
session management, etc.) lives elsewhere in the code‑base.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def get_password_hash(password: str) -> str:
        """Return a bcrypt hash for *password* using passlib."""
        return pwd_context.hash(password)

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Validate *plain_password* against *hashed_password* using passlib."""
        return pwd_context.verify(plain_password, hashed_password)
except ImportError:  # pragma: no cover
    # Fallback using SHA-256 for environments without passlib (suitable for tests)
    import hashlib

    def get_password_hash(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return (
            hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
            == hashed_password
        )


from jose import jwt  # type: ignore[import]

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

# Environment configuration – fall back to safe defaults for development.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT.

    ``data`` should contain at least a ``sub`` (subject) field – the caller
    decides what that means (e.g. an organization ID).
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode *token* and return its payload.

    Raises ``jwt.JWTError`` if verification fails.
    """
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# API‑key generation for machine clients
# ---------------------------------------------------------------------------


def generate_api_key() -> str:
    """Generate a raw ``skl_live_<32‑hex>`` token.

    The caller is responsible for persisting the SHA‑256 hash of this value in
    the ``ProxyNode`` table (see ``skelion_agent/models.py``).
    """
    raw = secrets.token_hex(16)  # 32 hex characters
    return f"skl_live_{raw}"
