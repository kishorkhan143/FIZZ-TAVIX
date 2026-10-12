"""
Scoring Orchestrator: End-to-end risk score computation and incident management.

Single entry point that:
1. Collects all events for an entity
2. Computes all 9 signals
3. Applies exponential decay
4. Converts to risk score
5. Manages incident lifecycle
"""

import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from models_unified import AuthEvent
from scoring.scoring import RiskScorer
from scoring.signals import SignalComputer
from risk_db import RiskDB
from incidents.incident_service import IncidentService

logger = logging.getLogger(__name__)


class ScoringOrchestrator:
    """Orchestrates complete risk scoring workflow."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize orchestrator.
        
        Args:
            config: Risk configuration dict
        """
        self.config = config or {}
        self.scorer = RiskScorer(
            half_life_seconds=self.config.get('half_life_seconds', 600)
        )
        self.signal_computer = SignalComputer(config)
        self.incident_service = IncidentService(config)
        self.lookback_seconds = self.config.get('lookback_seconds', 3600)
    
    def compute_entity_risk(
        self,
        session: Session,
        entity_type: str,
        entity_id: str,
        reference_time: Optional[datetime] = None,
    ) -> Tuple[int, Dict]:
        """
        Compute risk score for entity and manage incidents.
        
        Args:
            session: Database session
            entity_type: ACCOUNT, COMPUTER, PAIR, SOURCE
            entity_id: Entity identifier
            reference_time: Time for decay calculation (default: now or latest event time)
        
        Returns:
            Tuple of (risk_score, details_dict)
        """
        try:
            # Get ALL events for this entity (not time-bounded for replay/demo)
            # This allows demos with historical data to work correctly
            from models_unified import AuthEvent
            from sqlalchemy import select, and_, func
            
            if entity_type == 'ACCOUNT':
                stmt = select(AuthEvent).where(AuthEvent.username == entity_id)
            elif entity_type == 'COMPUTER':
                stmt = select(AuthEvent).where(AuthEvent.target_computer == entity_id)
            elif entity_type == 'PAIR':
                username, computer = entity_id.split('@', 1)
                stmt = select(AuthEvent).where(
                    and_(
                        AuthEvent.username == username,
                        AuthEvent.target_computer == computer
                    )
                )
            elif entity_type == 'SOURCE':
                stmt = select(AuthEvent).where(AuthEvent.source_ip == entity_id)
            else:
                return 0, {"entity_type": entity_type, "entity_id": entity_id, "score": 0, "band": "NORMAL", "signals": [], "incident_action": None}
            
            all_events = session.execute(stmt.order_by(AuthEvent.timestamp)).scalars().all()
            
            # If no reference_time provided, use latest event time (or now if no events)
            if reference_time is None:
                if all_events:
                    reference_time = max(e.timestamp for e in all_events)
                    # Ensure timezone-aware
                    if reference_time.tzinfo is None:
                        reference_time = reference_time.replace(tzinfo=timezone.utc)
                else:
                    reference_time = datetime.now(timezone.utc)
            
            # Apply lookback window starting from reference_time
            lookback_cutoff = reference_time - timedelta(seconds=self.lookback_seconds)
            
            # Ensure all timestamps are timezone-aware for comparison
            events = []
            for e in all_events:
                ts = e.timestamp
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= lookback_cutoff:
                    events.append(e)
            
            if not events:
                # No events: score = 0, no incident
                return 0, {
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "score": 0,
                    "band": "NORMAL",
                    "signals": [],
                    "incident_action": None,
                }
            
            # 2. Compute all signals
            signal_events_dict = self.signal_computer.compute_all_signals(
                [self._event_to_dict(e) for e in events],
                reference_time,
                self.config
            )
            
            # Flatten all signal events into one list for scoring
            all_signal_events = []
            active_signals = []
            
            for signal_name, events_list in signal_events_dict.items():
                if events_list:  # Signal fired
                    all_signal_events.extend(events_list)
                    active_signals.append(signal_name)
            
            logger.debug(
                f"Computed signals for {entity_type}:{entity_id}: "
                f"active={active_signals}, total_events={len(all_signal_events)}"
            )
            
            # 3. Compute risk score
            risk_score = self.scorer.compute_risk_score(
                all_signal_events,
                reference_time
            )
            
            # 4. Compute accumulated X for record
            accumulated_x = self.scorer.compute_accumulated_score(
                all_signal_events,
                reference_time
            )
            
            # 5. Get risk band
            risk_band = self.scorer.get_risk_band(risk_score)
            
            logger.debug(
                f"{entity_type}:{entity_id} score={risk_score} "
                f"band={risk_band} accumulated_x={accumulated_x:.2f}"
            )
            
            # 6. Record signal contributions (audit trail)
            for signal_name, events_list in signal_events_dict.items():
                for event_time, coefficient in events_list:
                    RiskDB.record_signal_contribution(
                        session,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        signal_name=signal_name,
                        coefficient=coefficient,
                    )
            
            # 7. Manage incident lifecycle
            incident = self.incident_service.process_risk_score(
                session,
                entity_type=entity_type,
                entity_id=entity_id,
                risk_score=risk_score,
                accumulated_x=accumulated_x,
                signal_names=active_signals,
            )
            
            incident_action = None
            if incident:
                incident_action = {
                    "incident_id": incident.id,
                    "status": incident.status,
                    "action": "opened" if incident.status == 'OPEN' and incident.reopened_count == 0 else "reopened" if incident.status == 'OPEN' else "cooled"
                }
            
            return risk_score, {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "score": risk_score,
                "band": risk_band,
                "accumulated_x": accumulated_x,
                "signals": active_signals,
                "incident_action": incident_action,
                "event_count": len(events),
            }
        
        except Exception as e:
            logger.error(
                f"Error computing risk for {entity_type}:{entity_id}: {e}",
                exc_info=True
            )
            session.rollback()
            raise
    
    def compute_all_entities(
        self,
        session: Session,
        reference_time: Optional[datetime] = None,
    ) -> Dict[Tuple[str, str], Tuple[int, Dict]]:
        """
        Compute risk scores for ALL entities in database.
        Useful for replay or bulk recalculation.
        
        Args:
            session: Database session
            reference_time: Time for decay calculation (default: max event time or now)
        
        Returns:
            Dict mapping (entity_type, entity_id) -> (score, details)
        """
        from sqlalchemy import select, func, distinct
        
        # If no reference_time, use the latest event time (for replays with old data)
        # or current time if no events
        if reference_time is None:
            max_time_result = session.execute(
                select(func.max(AuthEvent.timestamp))
            ).scalar_one_or_none()
            if max_time_result:
                reference_time = max_time_result
                if reference_time.tzinfo is None:
                    reference_time = reference_time.replace(tzinfo=timezone.utc)
            else:
                reference_time = datetime.now(timezone.utc)
        
        results = {}
        
        try:
            # Get unique accounts
            stmt = select(distinct(AuthEvent.username)).where(
                AuthEvent.username.isnot(None)
            )
            accounts = session.execute(stmt).scalars().all()
            
            for account in accounts:
                score, details = self.compute_entity_risk(
                    session, "ACCOUNT", account, reference_time
                )
                results[("ACCOUNT", account)] = (score, details)
            
            # Get unique computers
            stmt = select(distinct(AuthEvent.target_computer)).where(
                AuthEvent.target_computer.isnot(None)
            )
            computers = session.execute(stmt).scalars().all()
            
            for computer in computers:
                score, details = self.compute_entity_risk(
                    session, "COMPUTER", computer, reference_time
                )
                results[("COMPUTER", computer)] = (score, details)
            
            # Get unique source IPs
            stmt = select(distinct(AuthEvent.source_ip)).where(
                AuthEvent.source_ip.isnot(None)
            )
            sources = session.execute(stmt).scalars().all()
            
            for source in sources:
                score, details = self.compute_entity_risk(
                    session, "SOURCE", source, reference_time
                )
                results[("SOURCE", source)] = (score, details)
            
            # Get unique PAIR (account, computer)
            stmt = select(
                AuthEvent.username,
                AuthEvent.target_computer
            ).where(
                AuthEvent.username.isnot(None),
                AuthEvent.target_computer.isnot(None)
            ).distinct()
            pairs = session.execute(stmt).all()
            
            for username, computer in pairs:
                entity_id = f"{username}@{computer}"
                score, details = self.compute_entity_risk(
                    session, "PAIR", entity_id, reference_time
                )
                results[("PAIR", entity_id)] = (score, details)
            
            logger.info(f"Computed scores for {len(results)} entities")
            session.commit()
        
        except Exception as e:
            logger.error(f"Error computing all entities: {e}", exc_info=True)
            session.rollback()
            raise
        
        return results
    
    def _event_to_dict(self, event: AuthEvent) -> Dict:
        """Convert AuthEvent ORM to dict for signal computation."""
        return {
            'username': event.username,
            'target_computer': event.target_computer,
            'source_ip': event.source_ip,
            'timestamp': event.timestamp,
            'status': event.status,
            'event_id': event.event_id,
            'logon_type': event.logon_type,
        }
    
    def get_summary(self, session: Session) -> Dict:
        """
        Get system-wide summary statistics.
        
        Args:
            session: Database session
        
        Returns:
            Summary dict
        """
        stats = RiskDB.get_risk_stats(session)
        incident_summary = self.incident_service.get_incident_summary(session)
        
        return {
            "events": stats.get("event_counts", {}),
            "incidents": incident_summary.get("counts", {}),
            "risky_entities": stats.get("risky_entities", []),
        }
