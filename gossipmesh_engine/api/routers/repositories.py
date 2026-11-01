from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from gossipmesh.api import deps
from gossipmesh.models.user import User

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("/")
def list_repositories(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> List[dict]:
    try:
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return []
