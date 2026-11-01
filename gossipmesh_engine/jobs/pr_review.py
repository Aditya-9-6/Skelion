from sqlalchemy.orm import Session


class PRReviewJob:
    def __init__(self, db: Session):
        self.db = db

    def run(self, pr_id: int):
        pass
