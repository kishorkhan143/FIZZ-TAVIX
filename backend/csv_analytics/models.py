"""
CSV Analytics Models
====================
Provides database persistence for uploaded CSV files, records, groupings, and alerts.
Reuses SQLAlchemy Base from models_unified.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Boolean,
    Text,
    ForeignKey,
    Index,
)
from models_unified import Base


class CsvImport(Base):
    """Metadata and high-level statistics for an uploaded CSV file."""

    __tablename__ = "csv_imports"

    id = Column(String(36), primary_key=True)  # UUID
    filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    uploaded_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    total_records = Column(Integer, default=0)
    valid_records = Column(Integer, default=0)
    invalid_records = Column(Integer, default=0)
    groups_count = Column(Integer, default=0)
    alerts_count = Column(Integer, default=0)
    high_risk_count = Column(Integer, default=0)
    detected_columns = Column(Text, nullable=True)     # JSON: {canonical: original}
    quarantine_summary = Column(Text, nullable=True)   # JSON: list of rejected row samples
    analysis_summary = Column(Text, nullable=True)     # JSON: high-level metrics & stats
    status = Column(String(32), default="COMPLETED", index=True)  # PROCESSING, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "filename": self.filename,
            "file_size_bytes": self.file_size_bytes,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "groups_count": self.groups_count,
            "alerts_count": self.alerts_count,
            "high_risk_count": self.high_risk_count,
            "detected_columns": json.loads(self.detected_columns) if self.detected_columns else {},
            "quarantine_summary": json.loads(self.quarantine_summary) if self.quarantine_summary else [],
            "analysis_summary": json.loads(self.analysis_summary) if self.analysis_summary else {},
            "status": self.status,
            "error_message": self.error_message,
        }


class CsvAlert(Base):
    """Security alert generated from CSV event correlation."""

    __tablename__ = "csv_alerts"

    id = Column(String(36), primary_key=True)          # e.g. ALERT-001 or UUID
    import_id = Column(String(36), ForeignKey("csv_imports.id"), nullable=False, index=True)
    alert_type = Column(String(64), nullable=False)    # BRUTE_FORCE, MULTIPLE_FAILURES, etc.
    severity = Column(String(16), nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    risk_score = Column(Float, default=0.0)            # 0.0 to 100.0
    user = Column(String(256), nullable=True, index=True)
    ip = Column(String(64), nullable=True, index=True)
    country = Column(String(64), nullable=True)
    message = Column(Text, nullable=False)
    first_seen = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    event_count = Column(Integer, default=1)
    failed_count = Column(Integer, default=0)
    time_window_seconds = Column(Integer, default=0)
    status = Column(String(32), default="OPEN", index=True)  # OPEN, INVESTIGATING, RESOLVED
    reasons = Column(Text, nullable=True)              # JSON: list of explanation strings
    related_events = Column(Text, nullable=True)       # JSON: list of related row numbers / IDs
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_csv_alerts_import_severity", "import_id", "severity"),
        Index("ix_csv_alerts_import_status", "import_id", "status"),
    )

    def to_dict(self):
        import json
        return {
            "alert_id": self.id,
            "import_id": self.import_id,
            "type": self.alert_type,
            "severity": self.severity,
            "risk_score": round(self.risk_score, 1),
            "user": self.user,
            "ip": self.ip,
            "country": self.country,
            "message": self.message,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "event_count": self.event_count,
            "failed_count": self.failed_count,
            "time_window_seconds": self.time_window_seconds,
            "status": self.status,
            "reasons": json.loads(self.reasons) if self.reasons else [],
            "reason": json.loads(self.reasons) if self.reasons else [],
            "related_events": json.loads(self.related_events) if self.related_events else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CsvRecord(Base):
    """Normalized individual event record from an uploaded CSV."""

    __tablename__ = "csv_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    import_id = Column(String(36), ForeignKey("csv_imports.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    user = Column(String(256), nullable=True, index=True)
    ip = Column(String(64), nullable=True, index=True)
    target_computer = Column(String(256), nullable=True)
    event_type = Column(String(64), default="LOGIN")
    status = Column(String(32), default="SUCCESS", index=True)  # SUCCESS, FAILURE
    country = Column(String(64), nullable=True)
    severity = Column(String(32), nullable=True)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String(16), default="NORMAL")
    extra_fields = Column(Text, nullable=True)  # JSON dictionary of extra unmapped columns

    __table_args__ = (
        Index("ix_csv_records_import_user", "import_id", "user"),
        Index("ix_csv_records_import_ip", "import_id", "ip"),
        Index("ix_csv_records_import_status", "import_id", "status"),
        Index("ix_csv_records_import_time", "import_id", "timestamp"),
    )

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "import_id": self.import_id,
            "row_number": self.row_number,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user": self.user,
            "ip": self.ip,
            "target_computer": self.target_computer,
            "event_type": self.event_type,
            "status": self.status,
            "country": self.country,
            "severity": self.severity,
            "risk_score": round(self.risk_score, 1),
            "risk_level": self.risk_level,
            "extra_fields": json.loads(self.extra_fields) if self.extra_fields else {},
        }
