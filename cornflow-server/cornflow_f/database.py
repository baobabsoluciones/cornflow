from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from cornflow_f.config import get_config

# Get configuration
config = get_config()

# Create engine
engine = create_engine(
    config.DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}
    ),
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()


# Dependency to get DB session
def get_db():
    """
    Dependency function that yields db sessions
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
