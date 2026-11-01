from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Any, List

from gossipmesh_engine.api import deps
from gossipmesh.models.user import User

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("/", response_model=List[Any])
def list_repositories(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    return []
