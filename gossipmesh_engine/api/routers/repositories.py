from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from gossipmesh.api import deps

router = APIRouter()


@router.get("/")
def get_repositories(
    db: Session = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    return []
