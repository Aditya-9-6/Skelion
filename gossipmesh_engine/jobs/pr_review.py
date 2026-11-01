from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


def run_pr_review(db: Session, pr_id: int) -> None:
    logger.info(f"Running PR review for PR {pr_id}")
