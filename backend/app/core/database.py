from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=(settings.ENVIRONMENT == "development"),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """Ensure all tables and migrated columns exist in the database."""
    from sqlalchemy import inspect
    try:
        import app.models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        insp = inspect(engine)
        if "datasets" in insp.get_table_names():
            existing_cols = {c["name"] for c in insp.get_columns("datasets")}
            columns_to_ensure = [
                ("quality_json", "TEXT"),
                ("ai_detective_json", "TEXT"),
                ("repaired_file_path", "TEXT"),
                ("repaired_at", "TIMESTAMP"),
                ("validation_json", "TEXT"),
            ]
            for col_name, col_type in columns_to_ensure:
                if col_name not in existing_cols:
                    with engine.connect() as conn:
                        conn.execute(text(f"ALTER TABLE datasets ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
    except Exception:
        pass


init_db()


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a database session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Test database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
