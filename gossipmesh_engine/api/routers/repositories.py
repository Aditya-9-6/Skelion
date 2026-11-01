from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Any, List

from gossipmesh_engine.api.deps import get_db, get_current_user
from gossipmesh_engine.models.user import User
from gossipmesh_engine.models.repository import Repository

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("/", response_model=List[Any])
def list_repositories(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Any:
    repos = db.query(Repository).all()
    return repos
