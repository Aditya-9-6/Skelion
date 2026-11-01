from sqlalchemy.orm import Session
from gossipmesh.runtime.workflow import WorkflowManager
import logging

logger = logging.getLogger(__name__)


def run_pr_review_job(db: Session, pr_id: int) -> None:
    logger.info(f"Running PR review job for PR #{pr_id}")
    manager = WorkflowManager(db)
    manager.execute_pr_review(pr_id)
