"""
Core risk scoring engine.
Exponential decay formula: X(e,t) = sum(c_i * D(t - t_i)) where D(dt) = exp(-ln(2) * dt / HALF_LIFE)
Risk score: 100 * (1 - exp(-X))

Key property: Deterministic and order-independent.
Same set of events always produces same score regardless of processing order.
"""

import math
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta


class RiskScorer:
    """
    Computes risk scores deterministically using exponential decay.
    
    Formula:
    X(e,t) = Σ c_i * D(t - t_i)
    D(dt) = exp(-ln(2) * dt / HALF_LIFE)
    Risk(X) = 100 * (1 - exp(-X))
    """
    
    HALF_LIFE_SECONDS = 600  # Configurable from risk_config.yaml
    
    def __init__(self, half_life_seconds: int = HALF_LIFE_SECONDS):
        """
        Initialize scorer with decay half-life.
        
        Args:
            half_life_seconds: Decay half-life in seconds
                At dt = half_life, decay = 0.5
                At dt = 2*half_life, decay = 0.25
        """
        self.half_life_seconds = half_life_seconds
        # Decay constant: ln(2) / HALF_LIFE
        # This ensures exp(-constant * HALF_LIFE) = 0.5
        self.decay_constant = math.log(2) / half_life_seconds
    
    def decay_function(self, dt_seconds: float) -> float:
        """
        Exponential decay function: D(dt) = exp(-ln(2) * dt / HALF_LIFE)
        
        Properties:
        - D(0) = 1.0 (full weight now)
        - D(HALF_LIFE) = 0.5 (half weight at half-life)
        - D(2*HALF_LIFE) = 0.25 (quarter weight)
        - D(∞) → 0 (old events fade away)
        
        Args:
            dt_seconds: Time delta in seconds (age of event)
        
        Returns:
            Decay factor 0 to 1
        """
        if dt_seconds < 0:
            # Future events have no decay
            return 0.0
        return math.exp(-self.decay_constant * dt_seconds)
    
    def compute_accumulated_score(
        self,
        signal_events: List[Tuple[datetime, float]],
        reference_time: datetime
    ) -> float:
        """
        Compute accumulated signal X(t) for a set of timed events.
        This is the sum of all decay-weighted coefficients.
        
        X(e,t) = Σ c_i * D(t - t_i)
        
        Args:
            signal_events: List of (timestamp, coefficient) tuples
                          representing emissions from signals
            reference_time: Current time for decay calculation
        
        Returns:
            Accumulated score X (0 to infinity)
            Higher X → higher risk score
        
        Property: Order-independent
        Order of signal_events doesn't matter; summation is commutative.
        """
        from datetime import timezone as tz
        
        # Ensure reference_time is timezone-aware
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=tz.utc)
        
        accumulated = 0.0
        for event_time, coefficient in signal_events:
            # Ensure event_time is timezone-aware
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=tz.utc)
            
            # Time since event (always positive)
            dt = (reference_time - event_time).total_seconds()
            # Apply decay
            decay_value = self.decay_function(dt)
            # Accumulate weighted contribution
            accumulated += coefficient * decay_value
        return accumulated
    
    def score_from_accumulated(self, accumulated_x: float) -> int:
        """
        Convert accumulated X to 0-100 risk score.
        
        Risk(X) = 100 * (1 - exp(-X))
        
        This sigmoid-like curve has the property:
        - X = 0 → Risk = 0
        - X = 0.69 → Risk ≈ 50
        - X = 1.0 → Risk ≈ 63
        - X = 4.6 → Risk ≈ 99
        - X = ∞ → Risk → 100 (asymptotic)
        
        Args:
            accumulated_x: Accumulated X value from decay calculation
        
        Returns:
            Integer risk score 0-100
        """
        if accumulated_x <= 0:
            return 0
        
        # Compute risk score
        risk_score = 100 * (1 - math.exp(-accumulated_x))
        
        # Clamp to 0-100 and round
        return min(100, max(0, int(round(risk_score))))
    
    def compute_risk_score(
        self,
        signal_events: List[Tuple[datetime, float]],
        reference_time: datetime
    ) -> int:
        """
        Single call to compute complete risk score from signal events.
        
        This is the main entry point. It:
        1. Accumulates all signal events with decay
        2. Converts to 0-100 score
        
        Properties:
        - Deterministic: same events → same score
        - Order-independent: event order doesn't matter
        
        Args:
            signal_events: List of (timestamp, coefficient) from signals
            reference_time: Current time
        
        Returns:
            Risk score 0-100
        """
        accumulated = self.compute_accumulated_score(signal_events, reference_time)
        return self.score_from_accumulated(accumulated)
    
    def get_risk_band(self, score: int) -> str:
        """
        Categorize score into risk band for display.
        
        Args:
            score: Risk score 0-100
        
        Returns:
            Band name: 'NORMAL', 'WATCH', 'SUSPICIOUS', 'HIGH_RISK'
        """
        if score >= 80:
            return 'HIGH_RISK'
        elif score >= 60:
            return 'SUSPICIOUS'
        elif score >= 30:
            return 'WATCH'
        else:
            return 'NORMAL'
    
    def get_band_color(self, band: str) -> str:
        """
        Get hex color for risk band.
        
        Args:
            band: Risk band name
        
        Returns:
            Hex color string
        """
        colors = {
            'NORMAL': '#10b981',      # Green
            'WATCH': '#f59e0b',       # Amber
            'SUSPICIOUS': '#f97316',  # Orange
            'HIGH_RISK': '#ef4444'    # Red
        }
        return colors.get(band, '#6b7280')  # Gray default
