import logging
from sqlalchemy.orm import Session
from gossipmesh.runtime.workflow import WorkflowManager

logger = logging.getLogger(__name__)


class PRReviewJob:
    def __init__(self, workflow_manager: WorkflowManager):
        self.workflow_manager = workflow_manager

    def run(self, db: Session, pr_id: str) -> None:
        logger.info(f"Running PR review job for PR {pr_id}")
