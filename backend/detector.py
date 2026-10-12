"""
AuthSentinel — Unified Detection Pipeline
===========================================
Combines rule-based and anomaly detection into one pipeline.
"""

from detection import evaluate as rule_based_evaluate
from anomaly_detector import evaluate_anomalies
import logging

logger = logging.getLogger("authsentinel.detector")


def evaluate_event(
    event_id: int,
    username: str,
    source_ip: str,
    timestamp,
    status: str,
) -> list:
    """
    Run both rule-based and anomaly detection.
    Returns list of alerts (0, 1, or 2 items).
    """
    alerts = []
    
    # Rule-based detection
    rule_alert = rule_based_evaluate(event_id, username, source_ip, timestamp, status)
    if rule_alert:
        rule_alert["detection_type"] = "RULE_BASED"
        alerts.append(rule_alert)
        logger.info("[DETECT] Rule-based alert: %s", rule_alert.get("alert_type"))
    
    # Anomaly detection
    anomaly_alert = evaluate_anomalies(username, source_ip, timestamp, status)
    if anomaly_alert:
        anomaly_alert["detection_type"] = "ANOMALY"
        alerts.append(anomaly_alert)
        logger.info("[DETECT] Anomaly alert: %s", anomaly_alert.get("alert_type"))
    
    return alerts
