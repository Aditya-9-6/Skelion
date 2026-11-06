from typing import Any, Dict
from sqlalchemy.orm import Session
from gossipmesh.runtime.workflow import WorkflowManager


class PRReviewJob:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.workflow = WorkflowManager()

    def run(self, pr_id: str) -> Dict[str, Any]:
        return {"status": "completed", "pr_id": pr_id}
