"""
Extended database models for risk scoring system.
Adds RiskContribution, RiskSnapshot, and Incident tables.

These models track:
- RiskContribution: How each signal contributed to a score
- RiskSnapshot: Point-in-time risk score for an entity
- Incident: Lifecycle management (OPEN→COOLED→CLOSED)
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Boolean, Index
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone


class Base(DeclarativeBase):
    """ORM base class"""
    pass


class RiskContribution(Base):
    """
    Record of how a signal contributed to entity risk score.
    
    Example: If failure_count signal emitted coefficient 1.5 at 10:00:45
    for entity ACCOUNT:alice, this row records that contribution.
    """
    
    __tablename__ = "risk_contributions"
    
    id = Column(String(36), primary_key=True)
    event_id = Column(String(36), ForeignKey("auth_events.id"), nullable=True)
    entity_type = Column(String(50), nullable=False, index=True)  # ACCOUNT, COMPUTER, PAIR, SOURCE
    entity_id = Column(String(255), nullable=False, index=True)
    signal_name = Column(String(50), nullable=False)  # failure_count, failure_velocity, etc.
    coefficient = Column(Float, nullable=False)  # Contribution magnitude
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    __table_args__ = (
        Index("ix_risk_contrib_entity", "entity_type", "entity_id", "timestamp"),
        Index("ix_risk_contrib_signal", "entity_type", "signal_name", "timestamp"),
    )
    
    def __repr__(self):
        return f"<RiskContribution {self.entity_type}:{self.entity_id} {self.signal_name}={self.coefficient:.2f}>"


class RiskSnapshot(Base):
    """
    Point-in-time risk score for an entity.
    
    Represents the computed risk score at a moment in time.
    When events decay or new events arrive, a new snapshot is created.
    """
    
    __tablename__ = "risk_snapshots"
    
    id = Column(String(36), primary_key=True)
    entity_type = Column(String(50), nullable=False, index=True)  # ACCOUNT, COMPUTER, PAIR, SOURCE
    entity_id = Column(String(255), nullable=False, index=True)
    risk_score = Column(Integer, nullable=False)  # 0-100
    risk_band = Column(String(50), nullable=False)  # NORMAL, WATCH, SUSPICIOUS, HIGH_RISK
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    lookback_seconds = Column(Integer, default=3600)  # Decay window used
    
    # Detailed calculation fields
    accumulated_x = Column(Float, default=0.0)  # Sum of decayed contributions (X value)
    signal_count = Column(Integer, default=0)  # How many signals contributed
    
    __table_args__ = (
        Index("ix_risk_snapshot_entity", "entity_type", "entity_id", "timestamp"),
    )
    
    def __repr__(self):
        return f"<RiskSnapshot {self.entity_type}:{self.entity_id} score={self.risk_score} band={self.risk_band}>"


class Incident(Base):
    """
    Incident lifecycle: OPEN -> COOLED -> CLOSED
    
    Incident identity is deterministic:
    incident_id = hash(entity_type, entity_id, first_evidence_event_hash)
    
    This ensures re-imports are idempotent.
    """
    
    __tablename__ = "incidents"
    
    id = Column(String(16), primary_key=True)  # Deterministic hash
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(255), nullable=False, index=True)
    first_evidence_hash = Column(String(16), nullable=False)  # Event hash that triggered incident
    status = Column(String(20), default="OPEN", index=True)  # OPEN, COOLED, CLOSED
    
    opened_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    cooled_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    reopened_count = Column(Integer, default=0)
    
    peak_risk_score = Column(Integer, default=0)
    current_risk_score = Column(Integer, default=0)
    
    # Human review tracking
    reviewer_notes = Column(Text, nullable=True)
    reviewer_name = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    event_count = Column(Integer, default=0)  # Events in this incident
    signal_names = Column(String(500), nullable=True)  # CSV list of signals triggered
    
    __table_args__ = (
        Index("ix_incident_entity", "entity_type", "entity_id", "status"),
        Index("ix_incident_opened", "opened_at"),
    )
    
    def __repr__(self):
        return f"<Incident {self.entity_type}:{self.entity_id} id={self.id} status={self.status} peak={self.peak_risk_score}>"


class RiskBand(Base):
    """
    Risk score bands for categorization and display.
    These are reference data (not changed frequently).
    
    Used to color-code UI and provide semantic grouping.
    """
    
    __tablename__ = "risk_bands"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(50), unique=True, nullable=False)  # NORMAL, WATCH, SUSPICIOUS, HIGH_RISK
    min_score = Column(Integer, nullable=False)
    max_score = Column(Integer, nullable=False)
    color = Column(String(7), nullable=False)  # Hex color (#10b981, etc.)
    description = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<RiskBand {self.name} {self.min_score}-{self.max_score} {self.color}>"
