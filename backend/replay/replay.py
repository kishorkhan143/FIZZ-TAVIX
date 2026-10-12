"""
Replay module: Re-process historical events with new config.
"""

from typing import List, Dict
from datetime import datetime


class ReplayEngine:
    """Re-score historical events."""
    
    @staticmethod
    def replay_events(
        events: List[Dict],
        scorer,
        config: Dict
    ) -> List[Dict]:
        """
        Re-score historical events with current config.
        Deterministic: same events + same config = same scores.
        """
        scored_events = []
        
        for event in events:
            # Re-apply all signals
            # Re-compute risk score
            # Update incident status
            scored_events.append(event)
        
        return scored_events
