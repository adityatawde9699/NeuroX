# ===================================
#  Imports
# ===================================
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# ===================================
#  Database Configuration
# ===================================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./neurox.db")
engine_args = (
    {"connect_args": {"check_same_thread": False}}
    if DATABASE_URL.startswith("sqlite")
    else {}
)
# Create the SQLAlchemy engine and session factory
engine = create_engine(DATABASE_URL, future=True, **engine_args)

# Create a session factory for database sessions
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)

# ===================================
#  Database Models
# ===================================
class Base(DeclarativeBase):
    pass

# Function to access Database session
def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
