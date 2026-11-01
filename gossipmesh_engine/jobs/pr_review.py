from sqlalchemy.orm import Session
from gossipmesh.runtime.workflow import WorkflowManager
import logging

logger = logging.getLogger(__name__)


def process_pr_review(db: Session, workflow_id: str) -> None:
    logger.info(f"Processing PR review for workflow {workflow_id}")
    manager = WorkflowManager(db=db)
    manager.run(workflow_id)
