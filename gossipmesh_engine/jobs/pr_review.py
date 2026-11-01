from sqlalchemy.orm import Session
from gossipmesh.runtime.workflow import WorkflowManager
import logging

logger = logging.getLogger(__name__)


class PRReviewJob:
    def __init__(self, db: Session, workflow_manager: WorkflowManager):
        self.db = db
        self.workflow_manager = workflow_manager

    def execute(self, pr_id: int) -> None:
        logger.info(f"Executing PR review job for PR #{pr_id}")
