"""
Risk Database Integration Layer

Provides utilities for storing and retrieving risk data:
- Creating risk snapshots from scores
- Managing incident lifecycle
- Recording signal contributions
- Querying entity history
"""

import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from models_unified import (
    AuthEvent,
    RiskContribution,
    RiskSnapshot,
    Incident,
    RiskBand,
)
from incidents.incident_manager import IncidentManager


class RiskDB:
    """Database operations for risk scoring system."""
    
    @staticmethod
    def create_risk_snapshot(
        session: Session,
        entity_type: str,
        entity_id: str,
        risk_score: int,
        accumulated_x: float = 0.0,
        lookback_seconds: int = 3600,
        active_signals: Optional[List[str]] = None,
    ) -> RiskSnapshot:
        """
        Create and persist a risk score snapshot.
        
        Args:
            session: SQLAlchemy session
            entity_type: ACCOUNT, COMPUTER, PAIR, SOURCE
            entity_id: Entity identifier
            risk_score: Computed 0-100 score
            accumulated_x: Decay-weighted sum (X value)
            lookback_seconds: Decay window
            active_signals: List of signals that fired
        
        Returns:
            Created RiskSnapshot object
        """
        from scoring.scoring import RiskScorer
        
        scorer = RiskScorer()
        risk_band = scorer.get_risk_band(risk_score)
        
        snapshot = RiskSnapshot(
            id=str(uuid.uuid4()),
            entity_type=entity_type,
            entity_id=entity_id,
            risk_score=risk_score,
            risk_band=risk_band,
            timestamp=datetime.now(timezone.utc),
            lookback_seconds=lookback_seconds,
            accumulated_x=accumulated_x,
            signal_count=len(active_signals) if active_signals else 0,
            active_signals=",".join(active_signals) if active_signals else None,
        )
        
        session.add(snapshot)
        session.flush()
        return snapshot
    
    @staticmethod
    def record_signal_contribution(
        session: Session,
        entity_type: str,
        entity_id: str,
        signal_name: str,
        coefficient: float,
        auth_event_id: Optional[int] = None,
    ) -> RiskContribution:
        """
        Record that a signal contributed to entity risk.
        
        Args:
            session: SQLAlchemy session
            entity_type: ACCOUNT, COMPUTER, PAIR, SOURCE
            entity_id: Entity identifier
            signal_name: Signal that fired
            coefficient: Contribution magnitude
            auth_event_id: Optional link to auth event
        
        Returns:
            Created RiskContribution object
        """
        contrib = RiskContribution(
            id=str(uuid.uuid4()),
            auth_event_id=auth_event_id,
            entity_type=entity_type,
            entity_id=entity_id,
            signal_name=signal_name,
            coefficient=coefficient,
            timestamp=datetime.now(timezone.utc),
        )
        
        session.add(contrib)
        session.flush()
        return contrib
    
    @staticmethod
    def open_incident(
        session: Session,
        entity_type: str,
        entity_id: str,
        first_evidence_hash: str,
        peak_score: int,
        signal_names: Optional[List[str]] = None,
    ) -> Incident:
        """
        Open a new incident or return existing if already open.
        
        Args:
            session: SQLAlchemy session
            entity_type: ACCOUNT, COMPUTER, PAIR, SOURCE
            entity_id: Entity identifier
            first_evidence_hash: Hash of triggering event
            peak_score: Peak risk score
            signal_names: List of signals that contributed
        
        Returns:
            Incident object (created or existing)
        """
        # Compute incident ID (deterministic)
        incident_id = IncidentManager.compute_incident_id(
            entity_type, entity_id, first_evidence_hash
        )
        
        # Check if incident already exists
        stmt = select(Incident).where(Incident.id == incident_id)
        existing = session.execute(stmt).scalar_one_or_none()
        
        if existing:
            # Already open or cooled; update peak if needed
            if peak_score > existing.peak_risk_score:
                existing.peak_risk_score = peak_score
            existing.current_risk_score = peak_score
            if existing.status == 'COOLED':
                # Reopening
                existing.reopened_count += 1
                existing.status = 'OPEN'
            session.flush()
            return existing
        
        # Create new incident
        incident = Incident(
            id=incident_id,
            entity_type=entity_type,
            entity_id=entity_id,
            first_evidence_hash=first_evidence_hash,
            status='OPEN',
            opened_at=datetime.now(timezone.utc),
            peak_risk_score=peak_score,
            current_risk_score=peak_score,
            signal_names=",".join(signal_names) if signal_names else None,
        )
        
        session.add(incident)
        session.flush()
        return incident
    
    @staticmethod
    def cool_incident(
        session: Session,
        incident_id: str,
        current_score: int,
    ) -> Optional[Incident]:
        """
        Mark incident as COOLED (score dropped below threshold).
        
        Args:
            session: SQLAlchemy session
            incident_id: Incident ID
            current_score: Current risk score
        
        Returns:
            Updated Incident or None if not found
        """
        stmt = select(Incident).where(Incident.id == incident_id)
        incident = session.execute(stmt).scalar_one_or_none()
        
        if incident and incident.status == 'OPEN':
            incident.status = 'COOLED'
            incident.cooled_at = datetime.now(timezone.utc)
            incident.current_risk_score = current_score
            session.flush()
        
        return incident
    
    @staticmethod
    def get_entity_events(
        session: Session,
        entity_type: str,
        entity_id: str,
        lookback_hours: int = 24,
    ) -> List[AuthEvent]:
        """
        Retrieve all auth events for an entity in recent period.
        
        Args:
            session: SQLAlchemy session
            entity_type: ACCOUNT, COMPUTER, PAIR, SOURCE
            entity_id: Entity identifier
            lookback_hours: How far back to retrieve
        
        Returns:
            List of AuthEvent objects
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        
        # Build query based on entity type
        if entity_type == 'ACCOUNT':
            stmt = select(AuthEvent).where(
                and_(
                    AuthEvent.username == entity_id,
                    AuthEvent.timestamp >= cutoff
                )
            )
        elif entity_type == 'COMPUTER':
            stmt = select(AuthEvent).where(
                and_(
                    AuthEvent.target_computer == entity_id,
                    AuthEvent.timestamp >= cutoff
                )
            )
        elif entity_type == 'PAIR':
            # PAIR is (username, computer)
            username, computer = entity_id.split('@', 1)
            stmt = select(AuthEvent).where(
                and_(
                    AuthEvent.username == username,
                    AuthEvent.target_computer == computer,
                    AuthEvent.timestamp >= cutoff
                )
            )
        elif entity_type == 'SOURCE':
            stmt = select(AuthEvent).where(
                and_(
                    AuthEvent.source_ip == entity_id,
                    AuthEvent.timestamp >= cutoff
                )
            )
        else:
            return []
        
        stmt = stmt.order_by(AuthEvent.timestamp)
        return session.execute(stmt).scalars().all()
    
    @staticmethod
    def get_entity_risk_history(
        session: Session,
        entity_type: str,
        entity_id: str,
        lookback_hours: int = 24,
    ) -> List[RiskSnapshot]:
        """
        Retrieve risk score history for an entity.
        
        Args:
            session: SQLAlchemy session
            entity_type: ACCOUNT, COMPUTER, PAIR, SOURCE
            entity_id: Entity identifier
            lookback_hours: How far back to retrieve
        
        Returns:
            List of RiskSnapshot objects ordered by time
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        
        stmt = select(RiskSnapshot).where(
            and_(
                RiskSnapshot.entity_type == entity_type,
                RiskSnapshot.entity_id == entity_id,
                RiskSnapshot.timestamp >= cutoff
            )
        ).order_by(RiskSnapshot.timestamp)
        
        return session.execute(stmt).scalars().all()
    
    @staticmethod
    def get_open_incidents(
        session: Session,
        limit: int = 100,
    ) -> List[Incident]:
        """
        Retrieve all open incidents.
        
        Args:
            session: SQLAlchemy session
            limit: Max results
        
        Returns:
            List of open Incident objects
        """
        stmt = select(Incident).where(
            Incident.status == 'OPEN'
        ).order_by(Incident.peak_risk_score.desc()).limit(limit)
        
        return session.execute(stmt).scalars().all()
    
    @staticmethod
    def get_incident_by_id(
        session: Session,
        incident_id: str,
    ) -> Optional[Incident]:
        """
        Retrieve a specific incident.
        
        Args:
            session: SQLAlchemy session
            incident_id: Incident ID
        
        Returns:
            Incident object or None
        """
        stmt = select(Incident).where(Incident.id == incident_id)
        return session.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_risk_stats(
        session: Session,
    ) -> Dict:
        """
        Compute aggregate risk statistics.
        
        Args:
            session: SQLAlchemy session
        
        Returns:
            Dict with risk stats
        """
        # Count events by status
        stmt = select(AuthEvent.status, func.count()).group_by(AuthEvent.status)
        event_counts = dict(session.execute(stmt).all())
        
        # Count incidents by status
        stmt = select(Incident.status, func.count()).group_by(Incident.status)
        incident_counts = dict(session.execute(stmt).all())
        
        # Get current risky entities (top by risk score)
        stmt = (
            select(
                RiskSnapshot.entity_type,
                RiskSnapshot.entity_id,
                func.max(RiskSnapshot.risk_score).label("max_score")
            )
            .group_by(RiskSnapshot.entity_type, RiskSnapshot.entity_id)
            .order_by(func.max(RiskSnapshot.risk_score).desc())
            .limit(10)
        )
        risky_entities = [
            {
                "entity_type": row[0],
                "entity_id": row[1],
                "score": row[2]
            }
            for row in session.execute(stmt).all()
        ]
        
        return {
            "event_counts": event_counts,
            "incident_counts": incident_counts,
            "risky_entities": risky_entities,
        }
