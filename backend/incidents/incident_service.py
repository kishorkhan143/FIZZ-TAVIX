"""
Incident Service: Orchestrates incident lifecycle management.

Responsibilities:
1. Listen for score updates
2. Open incidents when threshold crossed
3. Cool incidents when score drops
4. Track human review
5. Handle re-opens and re-scoring
"""

import logging
import uuid
from typing import Optional, List, Dict
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from models_unified import (
    AuthEvent,
    RiskSnapshot,
    Incident,
    RiskContribution,
)
from risk_db import RiskDB
from incidents.incident_manager import IncidentManager

logger = logging.getLogger(__name__)


class IncidentService:
    """Service for managing incident lifecycle."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize service with configuration.
        
        Args:
            config: Risk config dict (incident_threshold, cool_threshold, etc.)
        """
        self.config = config or {}
        self.incident_threshold = self.config.get('incident_threshold', 60)
        self.cool_threshold = self.config.get('cool_threshold', 30)
    
    def process_risk_score(
        self,
        session: Session,
        entity_type: str,
        entity_id: str,
        risk_score: int,
        accumulated_x: float,
        signal_names: Optional[List[str]] = None,
    ) -> Optional[Incident]:
        """
        Process a new risk score and manage incident lifecycle.
        
        Called after each risk score computation.
        Handles:
        - Opening incident if threshold crossed
        - Cooling incident if score dropped
        - Recording risk snapshot
        
        Args:
            session: Database session
            entity_type: ACCOUNT, COMPUTER, PAIR, SOURCE
            entity_id: Entity identifier
            risk_score: Computed 0-100 score
            accumulated_x: Decay-weighted sum (for record)
            signal_names: List of active signals
        
        Returns:
            Incident object if state changed, None if no action
        """
        try:
            # Create risk snapshot
            snapshot = RiskDB.create_risk_snapshot(
                session,
                entity_type=entity_type,
                entity_id=entity_id,
                risk_score=risk_score,
                accumulated_x=accumulated_x,
                active_signals=signal_names,
            )
            logger.debug(f"Created snapshot: {entity_type}:{entity_id} score={risk_score}")
            
            # Get first event for incident identity
            events = RiskDB.get_entity_events(session, entity_type, entity_id, lookback_hours=24)
            if not events:
                logger.warning(f"No events for {entity_type}:{entity_id}, skipping incident processing")
                return None
            
            first_event_hash = events[0].event_hash or "unknown"
            
            # Check for existing incident
            from sqlalchemy import select, and_
            stmt = select(Incident).where(
                and_(
                    Incident.entity_type == entity_type,
                    Incident.entity_id == entity_id
                )
            ).order_by(Incident.opened_at.desc()).limit(1)
            existing_incident = session.execute(stmt).scalar_one_or_none()
            
            # ========== Decision Tree ==========
            
            if risk_score >= self.incident_threshold:
                # ✓ Score high: should be open
                if existing_incident is None:
                    # NEW INCIDENT
                    incident = RiskDB.open_incident(
                        session,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        first_evidence_hash=first_event_hash,
                        peak_score=risk_score,
                        signal_names=signal_names,
                    )
                    logger.warning(
                        f"[INCIDENT OPEN] {entity_type}:{entity_id} "
                        f"score={risk_score} signals={','.join(signal_names or [])}"
                    )
                    session.commit()
                    return incident
                
                elif existing_incident.status == 'OPEN':
                    # ALREADY OPEN: update peak if higher
                    if risk_score > existing_incident.peak_risk_score:
                        existing_incident.peak_risk_score = risk_score
                        logger.debug(f"Updated peak score: {entity_type}:{entity_id} peak={risk_score}")
                    existing_incident.current_risk_score = risk_score
                    session.commit()
                    return existing_incident
                
                elif existing_incident.status == 'COOLED':
                    # REOPEN
                    existing_incident.status = 'OPEN'
                    existing_incident.reopened_count += 1
                    existing_incident.peak_risk_score = max(existing_incident.peak_risk_score, risk_score)
                    existing_incident.current_risk_score = risk_score
                    existing_incident.cooled_at = None  # Clear cooled time
                    logger.warning(
                        f"[INCIDENT REOPEN] {entity_type}:{entity_id} "
                        f"reopen_count={existing_incident.reopened_count} score={risk_score}"
                    )
                    session.commit()
                    return existing_incident
            
            elif risk_score < self.cool_threshold:
                # ✗ Score low: should be cooled or closed
                if existing_incident and existing_incident.status == 'OPEN':
                    # COOL
                    RiskDB.cool_incident(session, existing_incident.id, risk_score)
                    logger.info(
                        f"[INCIDENT COOLED] {entity_type}:{entity_id} "
                        f"score={risk_score} peak_was={existing_incident.peak_risk_score}"
                    )
                    session.commit()
                    return existing_incident
            
            else:
                # Score in WATCH band (30-60): no action, just update current
                if existing_incident:
                    existing_incident.current_risk_score = risk_score
                    session.commit()
            
            return None
        
        except Exception as e:
            logger.error(f"Error processing risk score: {e}", exc_info=True)
            session.rollback()
            raise
    
    def get_incidents_requiring_review(
        self,
        session: Session,
    ) -> List[Incident]:
        """
        Get incidents that need human review.
        Ordered by peak score descending.
        
        Args:
            session: Database session
        
        Returns:
            List of open incidents
        """
        from sqlalchemy import select
        
        stmt = select(Incident).where(
            Incident.status == 'OPEN'
        ).order_by(Incident.peak_risk_score.desc())
        
        return session.execute(stmt).scalars().all()
    
    def record_review(
        self,
        session: Session,
        incident_id: str,
        reviewer_name: str,
        notes: str,
    ) -> Incident:
        """
        Record human review of incident.
        
        Args:
            session: Database session
            incident_id: Incident ID
            reviewer_name: Reviewer name/email
            notes: Review notes
        
        Returns:
            Updated incident
        """
        incident = RiskDB.get_incident_by_id(session, incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")
        
        incident.reviewer_name = reviewer_name
        incident.reviewer_notes = notes
        incident.reviewed_at = datetime.now(timezone.utc)
        
        session.commit()
        logger.info(f"Incident {incident_id} reviewed by {reviewer_name}")
        
        return incident
    
    def close_incident(
        self,
        session: Session,
        incident_id: str,
    ) -> Incident:
        """
        Manually close an incident (admin action).
        
        Args:
            session: Database session
            incident_id: Incident ID
        
        Returns:
            Closed incident
        """
        incident = RiskDB.get_incident_by_id(session, incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")
        
        incident.status = 'CLOSED'
        incident.closed_at = datetime.now(timezone.utc)
        
        session.commit()
        logger.info(f"Incident {incident_id} manually closed")
        
        return incident
    
    def get_incident_summary(
        self,
        session: Session,
    ) -> Dict:
        """
        Get incident summary statistics.
        
        Args:
            session: Database session
        
        Returns:
            Dict with incident stats
        """
        from sqlalchemy import select, func
        
        # Count by status
        stmt = select(Incident.status, func.count()).group_by(Incident.status)
        counts = dict(session.execute(stmt).all())
        
        # Get open incidents
        open_incidents = RiskDB.get_open_incidents(session, limit=100)
        
        return {
            "counts": {
                "OPEN": counts.get('OPEN', 0),
                "COOLED": counts.get('COOLED', 0),
                "CLOSED": counts.get('CLOSED', 0),
                "total": sum(counts.values()),
            },
            "open_count": len(open_incidents),
            "risky_incidents": [
                {
                    "id": i.id,
                    "entity_type": i.entity_type,
                    "entity_id": i.entity_id,
                    "peak_score": i.peak_risk_score,
                    "current_score": i.current_risk_score,
                    "reopened_count": i.reopened_count,
                }
                for i in open_incidents[:10]  # Top 10
            ]
        }
    
    def export_incident_details(
        self,
        session: Session,
        incident_id: str,
    ) -> Dict:
        """
        Export comprehensive incident details for audit/reporting.
        
        Args:
            session: Database session
            incident_id: Incident ID
        
        Returns:
            Dict with full incident details
        """
        incident = RiskDB.get_incident_by_id(session, incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")
        
        # Get events
        events = RiskDB.get_entity_events(
            session,
            incident.entity_type,
            incident.entity_id,
            lookback_hours=72  # 3 days
        )
        
        # Get risk history
        history = RiskDB.get_entity_risk_history(
            session,
            incident.entity_type,
            incident.entity_id,
            lookback_hours=72
        )
        
        # Get signal contributions
        from sqlalchemy import select
        stmt = select(RiskContribution).where(
            RiskContribution.entity_type == incident.entity_type,
            RiskContribution.entity_id == incident.entity_id,
        ).order_by(RiskContribution.timestamp.desc()).limit(100)
        contributions = session.execute(stmt).scalars().all()
        
        return {
            "incident": {
                "id": incident.id,
                "entity_type": incident.entity_type,
                "entity_id": incident.entity_id,
                "status": incident.status,
                "opened_at": incident.opened_at.isoformat(),
                "cooled_at": incident.cooled_at.isoformat() if incident.cooled_at else None,
                "closed_at": incident.closed_at.isoformat() if incident.closed_at else None,
                "peak_score": incident.peak_risk_score,
                "current_score": incident.current_risk_score,
                "reopened_count": incident.reopened_count,
                "event_count": incident.event_count,
            },
            "review": {
                "reviewer_name": incident.reviewer_name,
                "notes": incident.reviewer_notes,
                "reviewed_at": incident.reviewed_at.isoformat() if incident.reviewed_at else None,
            },
            "events_count": len(events),
            "risk_history_points": len(history),
            "signal_contributions": [
                {
                    "signal_name": c.signal_name,
                    "coefficient": c.coefficient,
                    "timestamp": c.timestamp.isoformat(),
                }
                for c in contributions
            ]
        }
