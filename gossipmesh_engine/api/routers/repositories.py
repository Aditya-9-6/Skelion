from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any
from gossipmesh.api import deps
from gossipmesh.models.user import User

router = APIRouter()


@router.post("/sync")
def sync_repositories(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    mock_rsa_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIBOQIBAAJAVY6qupT3\n-----END RSA PRIVATE KEY-----"
    try:
        return {"status": "success", "synced_repos": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
