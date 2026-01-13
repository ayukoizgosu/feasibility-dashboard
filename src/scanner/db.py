"""Database connection and session management using SQLite + SpatiaLite."""

from pathlib import Path
from contextlib import contextmanager
import sqlite3

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

# Database path
DB_DIR = Path(__file__).parent.parent.parent.parent / "db"
DB_PATH = DB_DIR / "sites.db"


def load_spatialite(dbapi_conn, connection_record):
    """Load SpatiaLite extension for spatial queries."""
    dbapi_conn.enable_load_extension(True)
    try:
        # Try common SpatiaLite library names
        for lib in ["mod_spatialite", "libspatialite", "spatialite"]:
            try:
                dbapi_conn.load_extension(lib)
                break
            except sqlite3.OperationalError:
                continue
    except Exception:
        # SpatiaLite not available - spatial queries won't work
        pass
    dbapi_conn.enable_load_extension(False)


def get_engine():
    """Create SQLAlchemy engine with SpatiaLite support."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    engine = create_engine(
        f"sqlite:///{DB_PATH}",
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    # Load SpatiaLite on each connection
    event.listen(engine, "connect", load_spatialite)
    
    return engine


# Create engine and session factory
engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_session() -> Session:
    """Get a database session with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Initialize database tables."""
    from scanner.models import Base
    
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize SpatiaLite metadata if available
    with engine.connect() as conn:
        try:
            conn.execute("SELECT InitSpatialMetaData(1)")
            conn.commit()
        except Exception:
            # SpatiaLite not available or already initialized
            pass
    
    print(f"Database initialized at {DB_PATH}")
