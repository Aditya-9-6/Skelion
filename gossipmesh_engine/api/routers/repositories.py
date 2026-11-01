from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Any

from gossipmesh_engine.api import deps
from gossipmesh.models.user import User

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post("/")
def register_repository(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    return {"status": "success", "user_id": current_user.id}
