"""
ML Integration Tests for TAVIX Guard CSV Analytics
===================================================
Tests that the ML predictor pipeline correctly:
- Flags david as BRUTE_FORCE
- Flags bob as FAIL_THEN_SUCCESS
- Flags user1-4 from 198.51.100.50 as a single PASSWORD_SPRAY incident
- Does NOT flag alice or charlie
- Still works (rule-only alerts) when model.joblib is missing

Uses an isolated in-memory SQLite database so tests never touch authsentinel.db.
"""

import os
import sys
import pytest

# Make backend/ importable as the root package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Absolute path to the sample CSV
_SAMPLE_CSV = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "sample_security_events.csv",
))
_MODEL_PATH = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "ml", "model.joblib",
))


def _make_test_db():
    """Create a fresh in-memory SQLite DB with all tables and ML columns."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    # Import all models so Base knows about them
    from models_unified import Base as UnifiedBase, get_or_create_risk_band_defaults
    import models  # noqa: F401 — registers User, Alert, etc. on models.Base
    from csv_analytics.models import CsvImport, CsvAlert, CsvRecord  # noqa: F401

    models.Base.metadata.create_all(bind=engine, checkfirst=True)
    UnifiedBase.metadata.create_all(bind=engine, checkfirst=True)

    # Ensure ML columns exist (SQLite CREATE TABLE above uses the ORM definition
    # which already has them, but add ALTER TABLE guards just in case)
    ml_cols = [
        "ALTER TABLE csv_alerts ADD COLUMN source VARCHAR(16) DEFAULT 'RULE'",
        "ALTER TABLE csv_alerts ADD COLUMN ml_prediction VARCHAR(64)",
        "ALTER TABLE csv_alerts ADD COLUMN ml_risk REAL",
        "ALTER TABLE csv_alerts ADD COLUMN ml_confidence REAL",
        "ALTER TABLE csv_alerts ADD COLUMN ml_review_label TEXT",
        "ALTER TABLE csv_alerts ADD COLUMN suggested_step TEXT",
        "ALTER TABLE csv_alerts ADD COLUMN class_probabilities TEXT",
        "ALTER TABLE csv_alerts ADD COLUMN evidence TEXT",
        "ALTER TABLE csv_alerts ADD COLUMN anomaly_score REAL",
    ]
    with engine.begin() as conn:
        for ddl in ml_cols:
            try:
                conn.execute(text(ddl))
            except Exception:
                pass  # column already exists

        # tables required by init_db internals
        for ddl in [
            ("CREATE TABLE IF NOT EXISTS computers ("
             "terminal_id VARCHAR(256) PRIMARY KEY, computer_name VARCHAR(256), "
             "hostname VARCHAR(256), ip_address VARCHAR(64), mac_address VARCHAR(64), "
             "os_name VARCHAR(128), os_version VARCHAR(128), logged_in_user VARCHAR(256), "
             "cpu VARCHAR(256), ram VARCHAR(128), manufacturer VARCHAR(256), "
             "model VARCHAR(256), status VARCHAR(32) DEFAULT 'UNKNOWN', "
             "last_seen TIMESTAMP, created_at TIMESTAMP, updated_at TIMESTAMP)"),
            ("CREATE TABLE IF NOT EXISTS remote_commands ("
             "id INTEGER PRIMARY KEY AUTOINCREMENT, terminal_id VARCHAR(256) NOT NULL, "
             "command VARCHAR(64) NOT NULL, alert_id INTEGER, "
             "status VARCHAR(32) DEFAULT 'PENDING', payload TEXT, result_message TEXT, "
             "created_at TIMESTAMP, executed_at TIMESTAMP)"),
        ]:
            try:
                conn.execute(text(ddl))
            except Exception:
                pass

    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()

    # Seed risk bands so ScoringBridge works
    try:
        get_or_create_risk_band_defaults(db)
        db.commit()
    except Exception:
        db.rollback()

    return db


def _load_sample_csv():
    with open(_SAMPLE_CSV, "rb") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Test 1: ML predictions on the sample CSV
# ---------------------------------------------------------------------------

def test_ml_predictions_on_sample_csv():
    """Main integration test: assert expected ML predictions on sample_security_events.csv."""
    from csv_analytics.service import CsvAnalyticsService

    db = _make_test_db()
    try:
        file_bytes = _load_sample_csv()
        result = CsvAnalyticsService.process_csv_upload(
            file_bytes=file_bytes,
            filename="sample_security_events.csv",
            db=db,
        )
        assert result.get("success") is True, f"Upload failed: {result}"
        import_id = result["import_id"]

        alerts = CsvAnalyticsService.get_alerts(
            import_id=import_id,
            severity=None,
            status=None,
            source=None,
            db=db,
        )
        assert len(alerts) >= 1, "Expected at least one alert"

        # --- david: BRUTE_FORCE ---
        david_ml_alerts = [
            a for a in alerts
            if a.get("user") == "david"
            and a.get("source") in ("ML", "RULE+ML")
        ]
        assert any(
            a.get("ml_prediction") == "BRUTE_FORCE" for a in david_ml_alerts
        ), f"david should be flagged BRUTE_FORCE; david ML alerts: {david_ml_alerts}"

        # --- bob: FAIL_THEN_SUCCESS ---
        bob_ml_alerts = [
            a for a in alerts
            if a.get("user") == "bob"
            and a.get("source") in ("ML", "RULE+ML")
        ]
        assert any(
            a.get("ml_prediction") == "FAIL_THEN_SUCCESS" for a in bob_ml_alerts
        ), f"bob should be flagged FAIL_THEN_SUCCESS; bob ML alerts: {bob_ml_alerts}"

        # --- user1-4 spray from 198.51.100.50: exactly one PASSWORD_SPRAY ---
        spray_alerts = [
            a for a in alerts
            if a.get("ip") == "198.51.100.50"
            and a.get("ml_prediction") == "PASSWORD_SPRAY"
            and a.get("source") in ("ML", "RULE+ML")
        ]
        assert len(spray_alerts) == 1, (
            f"Expected exactly one PASSWORD_SPRAY from 198.51.100.50, "
            f"got {len(spray_alerts)}: {spray_alerts}"
        )

        # --- alice and charlie: NOT flagged by ML ---
        ml_alerts = [a for a in alerts if a.get("source") in ("ML", "RULE+ML")]
        assert not any(a.get("user") == "alice" for a in ml_alerts), \
            "alice must not be ML-flagged"
        assert not any(a.get("user") == "charlie" for a in ml_alerts), \
            "charlie must not be ML-flagged"

        # --- at least one ML alert exists ---
        assert any(a.get("source") in ("ML", "RULE+ML") for a in alerts), \
            "At least one alert must have ML source after upload"

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Test 2: Upload must succeed without model.joblib (rule-only mode)
# ---------------------------------------------------------------------------

def test_upload_without_model():
    """Upload must succeed (rule-only alerts) even when model.joblib is missing."""
    from csv_analytics.service import CsvAnalyticsService

    model_path = _MODEL_PATH
    backup_path = model_path + ".bak"

    model_existed = os.path.exists(model_path)
    if model_existed:
        os.rename(model_path, backup_path)

    # Reset the predictor's in-process bundle cache so the renamed file is
    # actually triggered as a missing model (not replayed from a prior load).
    try:
        import ml.predictor as _pred_mod
        _pred_mod._bundle = None
    except Exception:
        pass

    try:
        db = _make_test_db()
        try:
            file_bytes = _load_sample_csv()
            result = CsvAnalyticsService.process_csv_upload(
                file_bytes=file_bytes,
                filename="sample_security_events.csv",
                db=db,
            )
            assert result.get("success") is True, \
                f"Upload should succeed without model; got: {result}"
            assert result.get("alerts", 0) >= 0, \
                "alerts count must be non-negative"

            alerts = CsvAnalyticsService.get_alerts(
                import_id=result["import_id"],
                severity=None,
                status=None,
                source=None,
                db=db,
            )
            assert len(alerts) >= 1, \
                "Rule-only mode should still produce at least one alert"
        finally:
            db.close()
    finally:
        # Always restore model and reload the bundle so subsequent tests work
        if model_existed and os.path.exists(backup_path):
            os.rename(backup_path, model_path)
        try:
            import ml.predictor as _pred_mod
            _pred_mod._bundle = None  # will be reloaded on next call
        except Exception:
            pass


if __name__ == "__main__":
    print("Running ML integration tests...")
    test_ml_predictions_on_sample_csv()
    print("[PASS] ML predictions on sample CSV passed")
    test_upload_without_model()
    print("[PASS] Upload without model.joblib passed")
    print("\n=== ALL ML INTEGRATION TESTS PASSED ===")
