"""
Risk API Endpoints

Provides REST API for risk scoring system:
- Entity risk queries (ACCOUNT, COMPUTER, PAIR, SOURCE)
- Incident management (list, detail, review)
- CSV import
- Risk statistics
"""

import uuid
import logging
from typing import List, Optional
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
from sqlalchemy.orm import Session

from models_unified import AuthEvent, RiskSnapshot, Incident
from risk_db import RiskDB
from importer.csv_importer import CSVImporter
from database import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["risk"])


# ============================================================================
# Entity Risk Endpoints
# ============================================================================

@router.get("/entity/{entity_type}/{entity_id}")
def get_entity_detail(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_session),
):
    """
    Get risk detail for an entity.
    
    Endpoint: GET /api/entity/ACCOUNT/alice
    
    Returns:
    {
        "entity_type": "ACCOUNT",
        "entity_id": "alice",
        "current_risk_score": 45,
        "risk_band": "WATCH",
        "event_count": 12,
        "peak_risk_score": 75,
        "incident_status": "COOLED",
        "timeline": [{"timestamp": "...", "score": 45}, ...],
        "active_signals": ["failure_count", "multi_computer"]
    }
    """
    try:
        # Validate entity type
        if entity_type not in ('ACCOUNT', 'COMPUTER', 'PAIR', 'SOURCE'):
            raise HTTPException(status_code=400, detail="Invalid entity_type")
        
        # Get recent events
        events = RiskDB.get_entity_events(db, entity_type, entity_id, lookback_hours=24)
        if not events:
            return {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "current_risk_score": 0,
                "risk_band": "NORMAL",
                "event_count": 0,
                "peak_risk_score": 0,
                "incident_status": None,
                "timeline": [],
                "active_signals": []
            }
        
        # Get risk history
        history = RiskDB.get_entity_risk_history(db, entity_type, entity_id, lookback_hours=24)
        timeline = [
            {
                "timestamp": s.timestamp.isoformat(),
                "score": s.risk_score,
                "band": s.risk_band,
                "signals": s.active_signals.split(",") if s.active_signals else []
            }
            for s in history
        ]
        
        # Get current score (latest snapshot)
        current_score = history[-1].risk_score if history else 0
        current_band = history[-1].risk_band if history else "NORMAL"
        active_signals = history[-1].active_signals.split(",") if history and history[-1].active_signals else []
        
        # Get peak score
        peak_score = max((s.risk_score for s in history), default=0)
        
        # Get incident status
        incident = None
        from sqlalchemy import select, and_
        stmt = select(Incident).where(
            and_(
                Incident.entity_type == entity_type,
                Incident.entity_id == entity_id
            )
        ).order_by(Incident.opened_at.desc()).limit(1)
        incident = db.execute(stmt).scalar_one_or_none()
        
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "current_risk_score": current_score,
            "risk_band": current_band,
            "event_count": len(events),
            "peak_risk_score": peak_score,
            "incident_status": incident.status if incident else None,
            "incident_id": incident.id if incident else None,
            "timeline": timeline,
            "active_signals": active_signals,
            "last_event": events[-1].timestamp.isoformat() if events else None,
        }
    
    except Exception as e:
        logger.error(f"Error fetching entity detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Incident Endpoints
# ============================================================================

@router.get("/incidents")
def list_incidents(
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_session),
):
    """
    List incidents.
    
    Query params:
    - status: Filter by status (OPEN, COOLED, CLOSED)
    - limit: Max results (default 100)
    """
    from sqlalchemy import select
    
    try:
        stmt = select(Incident)
        
        if status:
            stmt = stmt.where(Incident.status == status)
        
        stmt = stmt.order_by(Incident.opened_at.desc()).limit(limit)
        incidents = db.execute(stmt).scalars().all()
        
        return {
            "incidents": [
                {
                    "id": i.id,
                    "entity_type": i.entity_type,
                    "entity_id": i.entity_id,
                    "status": i.status,
                    "opened_at": i.opened_at.isoformat(),
                    "cooled_at": i.cooled_at.isoformat() if i.cooled_at else None,
                    "closed_at": i.closed_at.isoformat() if i.closed_at else None,
                    "peak_risk_score": i.peak_risk_score,
                    "current_risk_score": i.current_risk_score,
                    "event_count": i.event_count,
                    "reopened_count": i.reopened_count,
                    "reviewer_notes": i.reviewer_notes,
                    "reviewed_at": i.reviewed_at.isoformat() if i.reviewed_at else None,
                }
                for i in incidents
            ],
            "count": len(incidents)
        }
    
    except Exception as e:
        logger.error(f"Error listing incidents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents/{incident_id}")
def get_incident(
    incident_id: str,
    db: Session = Depends(get_session),
):
    """Get detailed incident information."""
    try:
        incident = RiskDB.get_incident_by_id(db, incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Get events for this incident
        events = RiskDB.get_entity_events(
            db,
            incident.entity_type,
            incident.entity_id,
            lookback_hours=24
        )
        
        return {
            "id": incident.id,
            "entity_type": incident.entity_type,
            "entity_id": incident.entity_id,
            "status": incident.status,
            "opened_at": incident.opened_at.isoformat(),
            "cooled_at": incident.cooled_at.isoformat() if incident.cooled_at else None,
            "closed_at": incident.closed_at.isoformat() if incident.closed_at else None,
            "peak_risk_score": incident.peak_risk_score,
            "current_risk_score": incident.current_risk_score,
            "event_count": incident.event_count,
            "reopened_count": incident.reopened_count,
            "reviewer_notes": incident.reviewer_notes,
            "reviewed_by": incident.reviewer_name,
            "reviewed_at": incident.reviewed_at.isoformat() if incident.reviewed_at else None,
            "signal_names": incident.signal_names.split(",") if incident.signal_names else [],
            "events_count": len(events),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching incident: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/incidents/{incident_id}/review")
def review_incident(
    incident_id: str,
    body: dict,
    db: Session = Depends(get_session),
):
    """
    Record human review of incident.
    
    Body:
    {
        "notes": "Confirmed attack pattern",
        "reviewer_name": "alice@lab.com"
    }
    """
    try:
        incident = RiskDB.get_incident_by_id(db, incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        incident.reviewer_notes = body.get("notes")
        incident.reviewer_name = body.get("reviewer_name")
        incident.reviewed_at = datetime.now(timezone.utc)
        
        db.commit()
        
        return {
            "ok": True,
            "incident_id": incident_id,
            "reviewed_at": incident.reviewed_at.isoformat(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing incident: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CSV Import Endpoint
# ============================================================================

@router.post("/import/csv")
def import_csv(
    file: UploadFile = File(...),
    x_collector_secret: Optional[str] = Header(None),
    db: Session = Depends(get_session),
):
    """
    Import events from CSV file.
    
    Expected CSV columns:
    - username: User name
    - computer: Target computer
    - source_ip: Source IP
    - timestamp: Event time (multiple formats supported)
    - event_type: FAILURE or SUCCESS
    - logon_type: (optional) Logon type number
    - status: (optional) Event status
    
    Returns import statistics and quarantine details.
    """
    from config import settings
    
    # Verify secret if configured
    if settings.collector_secret and x_collector_secret != settings.collector_secret:
        raise HTTPException(status_code=403, detail="Invalid collector secret")
    
    try:
        # Read CSV into memory
        contents = file.file.read()
        temp_path = f"/tmp/authsentinel_import_{uuid.uuid4()}.csv"
        
        with open(temp_path, 'wb') as f:
            f.write(contents)
        
        # Import events
        events, result = CSVImporter.import_csv(temp_path)
        
        # Get existing hashes to prevent duplicates
        from sqlalchemy import select
        stmt = select(AuthEvent.event_hash).where(AuthEvent.event_hash.isnot(None))
        existing_hashes = set(db.execute(stmt).scalars().all())
        
        # Filter out duplicates
        new_events = [
            e for e in events
            if e.get('event_hash') not in existing_hashes
        ]
        
        # Store events
        from datetime import datetime as dt
        stored_count = 0
        for event_dict in new_events:
            event = AuthEvent(
                event_id=event_dict.get('event_id'),
                timestamp=event_dict.get('timestamp') or dt.now(timezone.utc),
                username=event_dict.get('username'),
                source_ip=event_dict.get('source_ip'),
                target_computer=event_dict.get('target_computer'),
                logon_type=event_dict.get('logon_type'),
                status=event_dict.get('status'),
                event_hash=event_dict.get('event_hash'),
                raw_record_id=event_dict.get('raw_record_id'),
            )
            db.add(event)
            stored_count += 1
        
        db.commit()
        
        return {
            "ok": result.to_dict()['success'],
            "imported_rows": stored_count,
            "quarantined_rows": len(result.quarantined_rows),
            "merged_duplicates": result.merged_duplicates,
            "quarantine_details": result.quarantined_rows,
            "errors": result.errors,
            "warnings": result.warnings,
        }
    
    except Exception as e:
        logger.error(f"Error importing CSV: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


# ============================================================================
# Risk Statistics Endpoint
# ============================================================================

@router.get("/stats/risk")
def get_risk_stats(
    db: Session = Depends(get_session),
):
    """
    Get aggregate risk statistics.
    """
    try:
        stats = RiskDB.get_risk_stats(db)
        return {
            "event_counts": stats.get('event_counts', {}),
            "incident_counts": stats.get('incident_counts', {}),
            "risky_entities": stats.get('risky_entities', []),
        }
    
    except Exception as e:
        logger.error(f"Error computing risk stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Configuration Endpoint
# ============================================================================

@router.get("/config")
def get_config():
    """Get current risk configuration."""
    import yaml
    try:
        with open("risk_config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        return {
            "half_life_seconds": config.get("half_life_seconds"),
            "incident_threshold": config.get("incident_threshold"),
            "cool_threshold": config.get("cool_threshold"),
            "lookback_seconds": config.get("lookback_seconds"),
            "lab_hours_start": config.get("lab_hours_start"),
            "lab_hours_end": config.get("lab_hours_end"),
            "timezone": config.get("timezone"),
        }
    
    except Exception as e:
        logger.error(f"Error reading config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
def update_config(
    body: dict,
    db: Session = Depends(get_session),
):
    """
    Update risk configuration and trigger replay.
    
    Changes will re-score all events in the database.
    """
    # TODO: Implement config update and replay
    raise HTTPException(status_code=501, detail="Config update not yet implemented")
