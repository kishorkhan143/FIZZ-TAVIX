"""
Risk Scoring Bridge
===================
Reuses the core RiskScorer (exponential decay: 100 * (1 - exp(-X))) and
SignalComputer from backend/scoring to calculate explainable entity risk scores.
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from collections import defaultdict

from scoring.scoring import RiskScorer
from scoring.signals import SignalComputer


class ScoringBridge:
    """Computes explainable entity risk scores using the existing RiskScorer & SignalComputer."""

    def __init__(self, half_life_seconds: int = 600):
        self.scorer = RiskScorer(half_life_seconds=half_life_seconds)
        self.signal_computer = SignalComputer()

    @staticmethod
    def get_risk_band(score: float) -> str:
        """Map numeric score to semantic risk band."""
        if score >= 80.0:
            return "CRITICAL"
        elif score >= 60.0:
            return "HIGH"
        elif score >= 30.0:
            return "MEDIUM"
        return "LOW"

    def compute_records_risk(self, records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Calculates risk score and explainable reasons for every user and IP in the records.

        Returns:
            Dict mapping entity_key (e.g. 'user:bob', 'ip:192.168.1.20') ->
            {
                "entity": str,
                "type": 'USER' | 'IP',
                "score": float,
                "band": 'LOW'|'MEDIUM'|'HIGH'|'CRITICAL',
                "reasons": List[{"points": int, "label": str}],
                "events_count": int,
                "failures_count": int,
                "success_count": int,
                "unique_ips": int,
                "unique_users": int,
            }
        """
        if not records:
            return {}

        ref_time = max((r["timestamp"] for r in records), default=datetime.now(timezone.utc))
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=timezone.utc)

        # Group by user and by IP
        user_map = defaultdict(list)
        ip_map = defaultdict(list)

        for r in records:
            u = r.get("user")
            ip = r.get("ip")
            if u:
                user_map[u].append(r)
            if ip and ip != "0.0.0.0":
                ip_map[ip].append(r)

        entity_scores: Dict[str, Dict[str, Any]] = {}

        # 1. Compute for Users
        for user, u_recs in user_map.items():
            failures = [r["timestamp"] for r in u_recs if r.get("status") == "FAILURE"]
            successes = [r["timestamp"] for r in u_recs if r.get("status") == "SUCCESS"]
            distinct_ips = {r.get("ip") for r in u_recs if r.get("ip")}

            # Compute signals using SignalComputer
            fc_events = self.signal_computer.failure_count(failures, ref_time, lookback_seconds=7200, base_coefficient=1.2)
            fv_events = self.signal_computer.failure_velocity(failures, ref_time, window_seconds=120, base_coefficient=2.5)
            burst_events = self.signal_computer.burstiness(failures, ref_time, burst_threshold=3, short_window_seconds=60, base_coefficient=3.0)

            all_signals = fc_events + fv_events + burst_events
            accumulated_x = self.scorer.compute_accumulated_score(all_signals, ref_time)
            base_score = float(self.scorer.score_from_accumulated(accumulated_x))

            # Additional multi-IP / ratio factors
            reasons = []
            bonus_score = 0.0

            if len(failures) > 0:
                fail_pts = min(40, len(failures) * 8)
                reasons.append({"points": fail_pts, "label": f"{len(failures)} failed login attempts"})
                bonus_score += fail_pts

            if len(distinct_ips) >= 3:
                reasons.append({"points": 20, "label": f"Multiple IP addresses ({len(distinct_ips)} unique IPs)"})
                bonus_score += 20.0

            fail_ratio = len(failures) / len(u_recs) if u_recs else 0
            if fail_ratio >= 0.5 and len(u_recs) >= 3:
                ratio_pts = int(fail_ratio * 25)
                reasons.append({"points": ratio_pts, "label": f"High failure ratio ({int(fail_ratio * 100)}%)"})
                bonus_score += ratio_pts

            if len(u_recs) >= 15:
                reasons.append({"points": 15, "label": f"Unusual event activity frequency ({len(u_recs)} events)"})
                bonus_score += 15.0

            # Final blended score (0 to 100)
            final_score = min(100.0, max(base_score, bonus_score))
            if not reasons:
                reasons.append({"points": int(final_score), "label": "Baseline standard activity"})

            entity_scores[f"user:{user}"] = {
                "entity": user,
                "type": "USER",
                "score": round(final_score, 1),
                "band": self.get_risk_band(final_score),
                "reasons": reasons,
                "events_count": len(u_recs),
                "failures_count": len(failures),
                "success_count": len(successes),
                "unique_ips": len(distinct_ips),
                "unique_users": 1,
            }

        # 2. Compute for IPs
        for ip, ip_recs in ip_map.items():
            failures = [r["timestamp"] for r in ip_recs if r.get("status") == "FAILURE"]
            successes = [r["timestamp"] for r in ip_recs if r.get("status") == "SUCCESS"]
            distinct_users = {r.get("user") for r in ip_recs if r.get("user")}

            fc_events = self.signal_computer.failure_count(failures, ref_time, lookback_seconds=7200, base_coefficient=1.5)
            fv_events = self.signal_computer.failure_velocity(failures, ref_time, window_seconds=120, base_coefficient=3.0)
            all_signals = fc_events + fv_events
            accumulated_x = self.scorer.compute_accumulated_score(all_signals, ref_time)
            base_score = float(self.scorer.score_from_accumulated(accumulated_x))

            reasons = []
            bonus_score = 0.0

            if len(failures) >= 4:
                fail_pts = min(45, len(failures) * 9)
                reasons.append({"points": fail_pts, "label": f"{len(failures)} failed login attempts from IP"})
                bonus_score += fail_pts

            if len(distinct_users) >= 3:
                spray_pts = min(35, len(distinct_users) * 10)
                reasons.append({"points": spray_pts, "label": f"Targeting {len(distinct_users)} different user accounts (potential password spray)"})
                bonus_score += spray_pts

            fail_ratio = len(failures) / len(ip_recs) if ip_recs else 0
            if fail_ratio >= 0.6 and len(ip_recs) >= 3:
                ratio_pts = int(fail_ratio * 20)
                reasons.append({"points": ratio_pts, "label": f"Elevated IP error rate ({int(fail_ratio * 100)}%)"})
                bonus_score += ratio_pts

            final_score = min(100.0, max(base_score, bonus_score))
            if not reasons:
                reasons.append({"points": int(final_score), "label": "Baseline standard traffic"})

            entity_scores[f"ip:{ip}"] = {
                "entity": ip,
                "type": "IP",
                "score": round(final_score, 1),
                "band": self.get_risk_band(final_score),
                "reasons": reasons,
                "events_count": len(ip_recs),
                "failures_count": len(failures),
                "success_count": len(successes),
                "unique_ips": 1,
                "unique_users": len(distinct_users),
            }

        return entity_scores
