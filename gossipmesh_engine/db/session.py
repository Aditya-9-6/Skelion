from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from gossipmesh.core.config import settings
import os

if os.environ.get("ENVIRONMENT") == "test":
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    from gossipmesh.models.base import Base

    # Import all models to ensure they are registered with Base.metadata

    Base.metadata.create_all(bind=engine)
else:
    engine = create_engine(
        str(settings.DATABASE_URI),
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
