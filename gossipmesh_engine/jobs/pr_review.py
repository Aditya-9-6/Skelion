from sqlalchemy.orm import Session
from gossipmesh.runtime.workflow import WorkflowManager


class PRReviewJob:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.workflow_manager = WorkflowManager()

    def run(self, pr_id: int) -> None:
        pass
