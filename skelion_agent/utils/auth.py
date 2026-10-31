"""Authentication utilities for FastAPI dependencies.
Provides a ``get_current_user`` function that extracts the JWT bearer token,
verifies it using the helpers in ``skelion_agent.auth`` and returns the
corresponding ``Organization`` model.
"""

from fastapi import Header, HTTPException, Depends
from sqlmodel import Session

from skelion_agent.auth import decode_access_token
from skelion_agent.models import Organization
from skelion_agent.database import get_session


def get_current_user(
    authorization: str = Header(..., description="Bearer JWT token"),
    session: Session = Depends(get_session),
) -> Organization:
    """Return the ``Organization`` associated with the JWT in ``Authorization``.

    The ``Authorization`` header must be of the form ``Bearer <token>``. The
    token payload is expected to contain a ``sub`` field with the organization
    ID (as stored by ``auth_routes`` during login). If validation fails, a
    ``401`` error is raised.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    org_id = payload.get("sub")
    if not org_id:
        raise HTTPException(
            status_code=401, detail="Token payload missing organization ID"
        )
    org = session.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org
