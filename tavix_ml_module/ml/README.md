# TAVIX Guard - lightweight ML layer

Train:    `python -m ml.train`              (seconds, writes ml/model.joblib ~0.5 MB)
Replay:   `python -m ml.analyze_csv ../sample_security_events.csv`

## What it does
Groups events into (account, source) session windows -> 21 features -> 
RandomForest (threat type + probability) + IsolationForest (novel-pattern score).
Classes: NORMAL, BRUTE_FORCE, PASSWORD_SPRAY, FAIL_THEN_SUCCESS, AFTER_HOURS
(+ UNUSUAL_PATTERN from the anomaly model).

## Safety / scope
Outputs a *review label* + suggested human step only. Never accuses a person,
never blocks an account. Department names are not features.

## Integrate (csv_analytics/service.py, right after SecurityDetector.detect_alerts)
    from ml.predictor import predict
    ml_findings = [p for p in predict(valid_records) if p["prediction"] != "NORMAL"]
Show `ml_findings` next to rule alerts (rules = auditable, ML = ranking/novelty).

## Limits (be upfront in your demo)
- Trained on SYNTHETIC data; holdout scores are optimistic. Retrain on real lab logs when available.
- Doesn't read event_type, so privileged-account probes (e.g. `admin`) stay with Rule 8.
