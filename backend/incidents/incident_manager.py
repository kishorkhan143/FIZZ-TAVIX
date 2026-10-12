"""
Incident lifecycle management.
Deterministic incident identity via hash(entity_type, entity_id, first_evidence_hash).
"""

import hashlib
from typing import Optional, Dict
from datetime import datetime
from enum import Enum


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    COOLED = "COOLED"
    CLOSED = "CLOSED"


class IncidentManager:
    """Manages incident lifecycle."""
    
    @staticmethod
    def compute_incident_id(
        entity_type: str,
        entity_id: str,
        first_evidence_hash: str
    ) -> str:
        """
        Deterministic incident ID via hash.
        Ensures re-imports are idempotent.
        """
        combined = f"{entity_type}:{entity_id}:{first_evidence_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    @staticmethod
    def should_open_incident(
        current_score: int,
        incident_threshold: int = 60
    ) -> bool:
        """Open incident when score crosses threshold."""
        return current_score >= incident_threshold
    
    @staticmethod
    def should_cool_incident(
        current_score: int,
        cool_threshold: int = 30
    ) -> bool:
        """Mark as COOLED when score drops below threshold."""
        return current_score < cool_threshold
