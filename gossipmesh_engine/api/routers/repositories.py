from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from gossipmesh_engine.api import deps

router = APIRouter()


@router.get("/repositories")
def list_repositories(db: Session = Depends(deps.get_db)) -> Any:
    return []
