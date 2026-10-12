"""
Nine configurable risk signals.
Each signal computes events and propagates to entity types via configurable shares.
Order-independent: signals are pure functions of event collections.
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, timezone
from collections import Counter


class SignalComputer:
    """
    Computes the 9 risk signals.
    Each method is pure: same input → same output regardless of call order.
    Returns list of (timestamp, coefficient) tuples for decay calculation.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize with config dict containing signal parameters."""
        self.config = config or {}
    
    # ========== Signal 1: Failure Count ==========
    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        """Ensure datetime is timezone-aware (UTC). For handling naive timestamps from DB."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def failure_count(
        self,
        failures: List[datetime],
        reference_time: datetime,
        lookback_seconds: int = 3600,
        base_coefficient: float = 1.0
    ) -> List[Tuple[datetime, float]]:
        """
        Signal 1: Recent failure count within lookback window.
        Each failure in the window emits one event with base coefficient.
        
        Args:
            failures: List of failure timestamps
            reference_time: Current time (for lookback calculation)
            lookback_seconds: Window size (default 3600 = 1 hour)
            base_coefficient: Coefficient per failure (default 1.0)
        
        Returns:
            List of (timestamp, coefficient) for decay calculation
        """
        reference_time = self._ensure_aware(reference_time)
        cutoff = reference_time - timedelta(seconds=lookback_seconds)
        recent_failures = [f for f in failures if cutoff <= self._ensure_aware(f) <= reference_time]
        
        # Each failure contributes base_coefficient
        events = [(f, base_coefficient) for f in recent_failures]
        return events
    
    # ========== Signal 2: Failure Velocity ==========
    def failure_velocity(
        self,
        failures: List[datetime],
        reference_time: datetime,
        window_seconds: int = 60,
        base_coefficient: float = 2.0
    ) -> List[Tuple[datetime, float]]:
        """
        Signal 2: Rate of failures per minute in recent window.
        Detects rapid-fire attempts.
        
        Args:
            failures: List of failure timestamps
            reference_time: Current time
            window_seconds: Velocity window (default 60s)
            base_coefficient: Scaling factor (default 2.0)
        
        Returns:
            Single event with coefficient = base_coefficient * (failures_per_minute)
            Or empty if no recent failures
        """
        cutoff = reference_time - timedelta(seconds=window_seconds)
        recent = [f for f in failures if cutoff <= f <= reference_time]
        
        if len(recent) == 0:
            return []
        
        # failures per minute
        velocity = len(recent) / (window_seconds / 60.0)
        # Single event at reference time with velocity coefficient
        return [(reference_time, base_coefficient * velocity)]
    
    # ========== Signal 3: Burstiness ==========
    def burstiness(
        self,
        failures: List[datetime],
        reference_time: datetime,
        burst_threshold: int = 3,
        short_window_seconds: int = 30,
        base_coefficient: float = 3.0
    ) -> List[Tuple[datetime, float]]:
        """
        Signal 3: Sudden cluster of failures (spike detection).
        Detects when attacker accelerates after slow reconnaissance.
        
        Args:
            failures: List of failure timestamps
            reference_time: Current time
            burst_threshold: Min failures to trigger (default 3)
            short_window_seconds: Short window (default 30s)
            base_coefficient: Scaling factor (default 3.0)
        
        Returns:
            Single event if burst detected, empty otherwise
        """
        if len(failures) < burst_threshold:
            return []
        
        cutoff = reference_time - timedelta(seconds=short_window_seconds)
        recent = [f for f in failures if cutoff <= f <= reference_time]
        
        if len(recent) >= burst_threshold:
            # Emit at the most recent failure with coefficient = base * cluster_size
            latest_time = max(recent)
            coefficient = base_coefficient * len(recent)
            return [(latest_time, coefficient)]
        
        return []
    
    # ========== Signal 4: Gap Compression ==========
    def gap_compression(
        self,
        failures: List[datetime],
        reference_time: datetime,
        min_failures: int = 3,
        compression_threshold: float = 0.7,
        base_coefficient: float = 2.5
    ) -> List[Tuple[datetime, float]]:
        """
        Signal 4: Failure intervals shrinking (attacker speeding up).
        Detects pattern: attacker is getting faster (more confident).
        
        Args:
            failures: List of failure timestamps (should be sorted)
            reference_time: Current time
            min_failures: Min failures to compute gaps (default 3)
            compression_threshold: Gap ratio threshold (default 0.7 = 30% compression)
            base_coefficient: Scaling factor (default 2.5)
        
        Returns:
            Single event if compression detected, empty otherwise
        """
        if len(failures) < min_failures:
            return []
        
        sorted_failures = sorted(failures)
        gaps = []
        
        # Compute all gaps
        for i in range(1, len(sorted_failures)):
            gap_seconds = (sorted_failures[i] - sorted_failures[i-1]).total_seconds()
            if gap_seconds > 0:
                gaps.append(gap_seconds)
        
        if len(gaps) < 2:
            return []
        
        # Check if most recent gap is significantly smaller than previous
        recent_gap = gaps[-1]
        older_gap = gaps[-2]
        
        if recent_gap < older_gap * compression_threshold:
            # Gaps are compressing - attacker speeding up
            compression_factor = older_gap / recent_gap
            coefficient = base_coefficient * compression_factor
            latest_time = sorted_failures[-1]
            return [(latest_time, coefficient)]
        
        return []
    
    # ========== Signal 5: Success After Failures ==========
    def success_after_failures(
        self,
        success_time: datetime,
        failures_before: List[datetime],
        lookback_seconds: int = 300,
        base_coefficient: float = 2.0
    ) -> List[Tuple[datetime, float]]:
        """
        Signal 5: Successful login following recent failures.
        High confidence indicator: failures then success = likely breach or compromise.
        
        Args:
            success_time: Timestamp of successful login
            failures_before: List of failure timestamps before success
            lookback_seconds: How far back to look (default 300s = 5 min)
            base_coefficient: Scaling factor (default 2.0)
        
        Returns:
            Single event if failures found before success, empty otherwise
        """
        cutoff = success_time - timedelta(seconds=lookback_seconds)
        recent_failures = [f for f in failures_before if cutoff <= f < success_time]
        
        if len(recent_failures) > 0:
            # Coefficient = base * number of failures before success
            coefficient = base_coefficient * len(recent_failures)
            return [(success_time, coefficient)]
        
        return []
    
    # ========== Signal 6: Multi-Computer ==========
    def multi_computer(
        self,
        computers: List[str],
        reference_time: datetime,
        base_coefficient: float = 1.5
    ) -> List[Tuple[datetime, float]]:
        """
        Signal 6: Account accessing multiple computers.
        Indicates potential lateral movement or account sharing.
        
        Args:
            computers: List of computer names this account accessed
            reference_time: Current time
            base_coefficient: Scaling factor (default 1.5)
        
        Returns:
            Single event if multiple computers, empty if only one
        """
        unique_computers = len(set(c for c in computers if c))
        
        if unique_computers > 1:
            coefficient = base_coefficient * unique_computers
            return [(reference_time, coefficient)]
        
        return []
    
    # ========== Signal 7: Password Spray ==========
    def password_spray(
        self,
        events: List[Dict],
        reference_time: datetime,
        threshold: int = 5,
        base_coefficient: float = 4.0
    ) -> List[Tuple[datetime, float]]:
        """
        Signal 7: Password spray pattern detection.
        One source trying many accounts, or many sources trying one account.
        
        Args:
            events: List of event dicts with 'username' and 'target_computer' keys
            reference_time: Current time
            threshold: Min unique targets to trigger (default 5)
            base_coefficient: Scaling factor (default 4.0)
        
        Returns:
            Single event if spray pattern detected, empty otherwise
        """
        # Count unique targets (usernames or computers)
        unique_targets = len(set(
            e.get('username', '') or e.get('target_computer', '')
            for e in events
            if e.get('status') == 'FAILURE'
        ))
        
        if unique_targets >= threshold:
            coefficient = base_coefficient * unique_targets
            return [(reference_time, coefficient)]
        
        return []
    
    # ========== Signal 8: After-Hours Success ==========
    def after_hours_success(
        self,
        success_time: datetime,
        reference_time: datetime,
        lab_hours_start: int = 8,
        lab_hours_end: int = 18,
        base_coefficient: float = 2.0
    ) -> List[Tuple[datetime, float]]:
        """
        Signal 8: Successful login outside normal lab hours.
        Lab PCs usually inactive after hours; success then is anomalous.
        
        Args:
            success_time: Timestamp of success
            reference_time: Current time (for consistency)
            lab_hours_start: Start of lab hours (default 8 = 08:00)
            lab_hours_end: End of lab hours (default 18 = 18:00)
            base_coefficient: Scaling factor (default 2.0)
        
        Returns:
            Single event if after-hours, empty if during lab hours
        """
        hour = success_time.hour
        is_after_hours = hour < lab_hours_start or hour >= lab_hours_end
        
        if is_after_hours:
            return [(success_time, base_coefficient)]
        
        return []
    
    # ========== Signal 9: Unusual Computer ==========
    def unusual_computer(
        self,
        account: str,
        computer: str,
        reference_time: datetime,
        historical_computers: Optional[Dict[str, set]] = None,
        base_coefficient: float = 1.5
    ) -> List[Tuple[datetime, float]]:
        """
        Signal 9: Account accessing computer for first time.
        New computer = potential moved compromised account or credential theft.
        
        Args:
            account: Username
            computer: Target computer name
            reference_time: Current time
            historical_computers: Dict mapping account -> set of known computers
            base_coefficient: Scaling factor (default 1.5)
        
        Returns:
            Single event if computer is new to account, empty if known
        """
        if historical_computers is None:
            historical_computers = {}
        
        seen_computers = historical_computers.get(account, set())
        
        if computer not in seen_computers:
            return [(reference_time, base_coefficient)]
        
        return []
    
    # ========== Utility: Combine all signals ==========
    def compute_all_signals(
        self,
        entity_events: List[Dict],
        reference_time: datetime,
        config: Optional[Dict] = None
    ) -> Dict[str, List[Tuple[datetime, float]]]:
        """
        Compute all 9 signals for an entity given its recent events.
        
        Args:
            entity_events: List of events for this entity (ACCOUNT/COMPUTER/PAIR/SOURCE)
            reference_time: Current time for relative calculations
            config: Optional config override
        
        Returns:
            Dict mapping signal name -> list of (timestamp, coefficient) events
        """
        cfg = config or self.config or {}
        signals_cfg = cfg.get('signals', {})
        
        # Ensure reference_time is timezone-aware
        reference_time = self._ensure_aware(reference_time)
        
        # Ensure all timestamps in events are timezone-aware
        for event in entity_events:
            if 'timestamp' in event and event['timestamp']:
                event['timestamp'] = self._ensure_aware(event['timestamp'])
        
        results = {}
        
        # Extract event lists by type
        failures = [
            e.get('timestamp') for e in entity_events
            if e.get('status') == 'FAILURE' and e.get('timestamp')
        ]
        
        successes = [
            e.get('timestamp') for e in entity_events
            if e.get('status') == 'SUCCESS' and e.get('timestamp')
        ]
        
        computers = [
            e.get('target_computer') for e in entity_events
            if e.get('target_computer')
        ]
        
        # Filter failures before each success
        failure_times_set = set(failures)
        
        # Signal 1: failure_count
        fc_cfg = signals_cfg.get('failure_count', {})
        if fc_cfg.get('enabled', True):
            results['failure_count'] = self.failure_count(
                failures,
                reference_time,
                lookback_seconds=cfg.get('lookback_seconds', 3600),
                base_coefficient=fc_cfg.get('base_coefficient', 1.0)
            )
        
        # Signal 2: failure_velocity
        fv_cfg = signals_cfg.get('failure_velocity', {})
        if fv_cfg.get('enabled', True):
            results['failure_velocity'] = self.failure_velocity(
                failures,
                reference_time,
                window_seconds=fv_cfg.get('window_seconds', 60),
                base_coefficient=fv_cfg.get('base_coefficient', 2.0)
            )
        
        # Signal 3: burstiness
        b_cfg = signals_cfg.get('burstiness', {})
        if b_cfg.get('enabled', True):
            results['burstiness'] = self.burstiness(
                failures,
                reference_time,
                burst_threshold=b_cfg.get('burst_threshold', 3),
                short_window_seconds=b_cfg.get('short_window_seconds', 30),
                base_coefficient=b_cfg.get('base_coefficient', 3.0)
            )
        
        # Signal 4: gap_compression
        gc_cfg = signals_cfg.get('gap_compression', {})
        if gc_cfg.get('enabled', True):
            results['gap_compression'] = self.gap_compression(
                failures,
                reference_time,
                min_failures=gc_cfg.get('min_failures', 3),
                compression_threshold=gc_cfg.get('compression_threshold', 0.7),
                base_coefficient=gc_cfg.get('base_coefficient', 2.5)
            )
        
        # Signal 5: success_after_failures
        saf_cfg = signals_cfg.get('success_after_failures', {})
        if saf_cfg.get('enabled', True):
            saf_events = []
            for success in successes:
                if success:
                    recent_failures = [f for f in failures if f < success]
                    saf_events.extend(self.success_after_failures(
                        success,
                        recent_failures,
                        lookback_seconds=saf_cfg.get('lookback_seconds', 300),
                        base_coefficient=saf_cfg.get('base_coefficient', 2.0)
                    ))
            results['success_after_failures'] = saf_events
        
        # Signal 6: multi_computer
        mc_cfg = signals_cfg.get('multi_computer', {})
        if mc_cfg.get('enabled', True):
            results['multi_computer'] = self.multi_computer(
                computers,
                reference_time,
                base_coefficient=mc_cfg.get('base_coefficient', 1.5)
            )
        
        # Signal 7: password_spray
        ps_cfg = signals_cfg.get('password_spray', {})
        if ps_cfg.get('enabled', True):
            results['password_spray'] = self.password_spray(
                entity_events,
                reference_time,
                threshold=ps_cfg.get('threshold', 5),
                base_coefficient=ps_cfg.get('base_coefficient', 4.0)
            )
        
        # Signal 8: after_hours_success
        ahs_cfg = signals_cfg.get('after_hours_success', {})
        if ahs_cfg.get('enabled', True):
            ahs_events = []
            for success in successes:
                if success:
                    ahs_events.extend(self.after_hours_success(
                        success,
                        reference_time,
                        lab_hours_start=ahs_cfg.get('lab_hours_start', 8),
                        lab_hours_end=ahs_cfg.get('lab_hours_end', 18),
                        base_coefficient=ahs_cfg.get('base_coefficient', 2.0)
                    ))
            results['after_hours_success'] = ahs_events
        
        # Signal 9: unusual_computer
        uc_cfg = signals_cfg.get('unusual_computer', {})
        if uc_cfg.get('enabled', True):
            # Would need historical data; for now empty
            results['unusual_computer'] = []
        
        return results
