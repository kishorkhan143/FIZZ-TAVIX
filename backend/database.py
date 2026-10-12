"""
AuthSentinel — Database Configuration

Provides SQLAlchemy engine, session factory, and initialization.
Supports both sync and async operations.
"""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from models_unified import Base, get_or_create_risk_band_defaults
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'authsentinel.db').replace(os.sep, '/')}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    connect_args={"timeout": 15} if "sqlite" in DATABASE_URL else {},
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Create all tables and initialize reference data.
    Safe to call multiple times.
    """
    # Ensure CSV analytics models, Computer model, and legacy models are registered
    from csv_analytics.models import CsvImport, CsvAlert, CsvRecord  # noqa: F401
    import models
    models.Base.metadata.create_all(bind=engine, checkfirst=True)
    Base.metadata.create_all(bind=engine, checkfirst=True)
    with engine.begin() as connection:
        try:
            connection.execute(text("ALTER TABLE alerts ADD COLUMN status VARCHAR(32) DEFAULT 'OPEN'"))
        except Exception:
            pass
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS computers ("
                "terminal_id VARCHAR(256) PRIMARY KEY, "
                "computer_name VARCHAR(256), "
                "hostname VARCHAR(256), "
                "ip_address VARCHAR(64), "
                "mac_address VARCHAR(64), "
                "os_name VARCHAR(128), "
                "os_version VARCHAR(128), "
                "logged_in_user VARCHAR(256), "
                "cpu VARCHAR(256), "
                "ram VARCHAR(128), "
                "manufacturer VARCHAR(256), "
                "model VARCHAR(256), "
                "status VARCHAR(32) DEFAULT 'UNKNOWN', "
                "last_seen TIMESTAMP, "
                "created_at TIMESTAMP, "
                "updated_at TIMESTAMP"
                ")"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS "
                "ix_auth_events_source_host_raw_record_id "
                "ON auth_events (source_host, raw_record_id)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS remote_commands ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "terminal_id VARCHAR(256) NOT NULL, "
                "command VARCHAR(64) NOT NULL, "
                "alert_id INTEGER, "
                "status VARCHAR(32) DEFAULT 'PENDING', "
                "payload TEXT, "
                "result_message TEXT, "
                "created_at TIMESTAMP, "
                "executed_at TIMESTAMP"
                ")"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS "
                "ix_remote_commands_terminal_status "
                "ON remote_commands (terminal_id, status)"
            )
        )
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(32) DEFAULT 'admin'"))
        except Exception:
            pass
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN name VARCHAR(256)"))
        except Exception:
            pass
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP"))
        except Exception:
            pass
        try:
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_users_verification_token "
                    "ON users (verification_token)"
                )
            )
        except Exception:
            pass
        # ML columns migration for csv_alerts (added in ML integration step)
        for _col_ddl in [
            "ALTER TABLE csv_alerts ADD COLUMN source VARCHAR(16) DEFAULT 'RULE'",
            "ALTER TABLE csv_alerts ADD COLUMN ml_prediction VARCHAR(64)",
            "ALTER TABLE csv_alerts ADD COLUMN ml_risk REAL",
            "ALTER TABLE csv_alerts ADD COLUMN ml_confidence REAL",
            "ALTER TABLE csv_alerts ADD COLUMN ml_review_label TEXT",
            "ALTER TABLE csv_alerts ADD COLUMN suggested_step TEXT",
            "ALTER TABLE csv_alerts ADD COLUMN class_probabilities TEXT",
            "ALTER TABLE csv_alerts ADD COLUMN evidence TEXT",
            "ALTER TABLE csv_alerts ADD COLUMN anomaly_score REAL",
        ]:
            try:
                connection.execute(text(_col_ddl))
            except Exception:
                pass  # column already exists — safe to ignore
        try:
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_csv_alerts_import_source "
                    "ON csv_alerts (import_id, source)"
                )
            )
        except Exception:
            pass
    logger.info("Database tables created/verified")
    
    # Initialize reference data and seed default admin
    with SessionLocal() as session:
        try:
            get_or_create_risk_band_defaults(session)
            logger.info("Risk bands initialized")
        except Exception as e:
            logger.error(f"Failed to initialize risk bands: {e}")

        try:
            from datetime import datetime, timezone
            admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "kishorkhan.dev@gmail.com").strip().lower()
            admin_user = session.query(models.User).filter(models.User.email == admin_email).first()
            now = datetime.now(timezone.utc)
            if not admin_user:
                admin_user = models.User(
                    email=admin_email,
                    role="admin",
                    is_verified=True,
                    created_at=now,
                    verified_at=now,
                )
                session.add(admin_user)
                session.commit()
                logger.info("Default admin user initialized: %s", admin_email)
            else:
                if not admin_user.is_verified or admin_user.role != "admin":
                    admin_user.is_verified = True
                    admin_user.role = "admin"
                    session.commit()
        except Exception as e:
            logger.error(f"Failed to ensure admin user: {e}")


def get_db() -> Session:
    """
    Get a database session for FastAPI dependency injection.
    
    Usage:
        @app.get("/api/endpoint")
        def my_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session() -> Session:
    """
    Get a synchronous database session for direct use.
    
    Usage:
        db = get_session()
        try:
            # do work
            db.commit()
        finally:
            db.close()
    """
    return SessionLocal()
