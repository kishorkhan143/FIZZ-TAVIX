"""
Inference wrapper.  Safe by design: it only produces REVIEW labels and a
human verification step. It never accuses a person and never blocks an account.
"""
import os
import joblib
import numpy as np
from ml.features import extract, FEATURE_NAMES

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.joblib")

REVIEW_STEP = {
    "BRUTE_FORCE": "Contact the account owner via a trusted channel; confirm whether they were typing the password; consider asking IT to review the source computer.",
    "PASSWORD_SPRAY": "Check the source computer/IP for a script or unattended session; ask the lab supervisor who was seated there at that time.",
    "FAIL_THEN_SUCCESS": "Ask the account owner to confirm this login; if unrecognised, a supervisor may request a password reset through the normal process.",
    "AFTER_HOURS": "Compare with the lab schedule / approved late-session list; confirm with the account owner or supervisor.",
    "NORMAL": "No action needed.",
}
REVIEW_LABEL = {
    "BRUTE_FORCE": "Needs review - repeated failures",
    "PASSWORD_SPRAY": "Needs review - one source, many accounts",
    "FAIL_THEN_SUCCESS": "Needs review - failures followed by success",
    "AFTER_HOURS": "Needs review - outside lab hours",
    "NORMAL": "Ordinary / isolated mistake",
}

_bundle = None


def _load():
    global _bundle
    if _bundle is None:
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


def predict(records, min_prob=0.5):
    """
    records: normalized event dicts (see features.py).
    returns: list of dicts, one per session window, sorted by ml_risk desc.
    """
    b = _load()
    X, wins = extract(records)
    if len(wins) == 0:
        return []
    proba = b["clf"].predict_proba(X)
    classes = list(b["clf"].classes_)
    lo, hi = b["iso_range"]
    anom = np.clip((-b["iso"].score_samples(X) - lo) / max(hi - lo, 1e-9), 0, 1)

    results = []
    for i, w in enumerate(wins):
        p = proba[i]
        top = classes[int(np.argmax(p))]
        p_threat = 1.0 - float(p[classes.index(0)])
        label = b["labels"][top]
        if label != "NORMAL" and p[classes.index(top)] < min_prob and anom[i] < 0.6:
            label = "NORMAL"            # weak evidence on both models -> don't raise
        elif label == "NORMAL" and anom[i] >= 0.85:
            label = "UNUSUAL_PATTERN"   # classifier says normal but pattern is novel
        risk = round(100 * max(p_threat, 0.6 * anom[i] if label == "UNUSUAL_PATTERN" else 0), 1)
        f = dict(zip(FEATURE_NAMES, X[i]))
        results.append({
            "user": w[0].get("user"), "ip": w[0].get("ip"),
            "computer": w[0].get("target_computer"),
            "event_ids": [r["row_number"] for r in w],
            "first_seen": w[0]["timestamp"], "last_seen": w[-1]["timestamp"],
            "prediction": label,
            "review_label": REVIEW_LABEL.get(label, "Needs review - unusual pattern"),
            "ml_risk": risk,
            "confidence": round(float(p.max()), 3),
            "anomaly_score": round(float(anom[i]), 3),
            "class_probabilities": {b["labels"][c]: round(float(p[j]), 3) for j, c in enumerate(classes)},
            "evidence": {
                "events": int(f["n_events"]), "failures": int(f["n_fail"]),
                "max_consecutive_failures": int(f["max_consec_fail"]),
                "failures_per_min": round(f["fail_per_min"], 1),
                "accounts_from_same_source": int(f["ctx_distinct_users_from_src"]),
                "success_after_failures": bool(f["success_after_fail"]),
                "after_hours_success": int(f["after_hours_success"]),
            },
            "suggested_human_step": REVIEW_STEP.get(label, "Have a supervisor review the events."),
        })
    results = _merge_sprays(results)
    return sorted(results, key=lambda r: -r["ml_risk"])


def _merge_sprays(results):
    """Collapse per-account spray windows from the same source IP into one incident."""
    merged, groups = [], {}
    for r in results:
        if r["prediction"] == "PASSWORD_SPRAY":
            groups.setdefault(r["ip"], []).append(r)
        else:
            merged.append(r)
    for ip, grp in groups.items():
        base = dict(max(grp, key=lambda r: r["ml_risk"]))
        base["user"] = f"{len(grp)} accounts"
        base["event_ids"] = sorted(e for r in grp for e in r["event_ids"])
        base["first_seen"] = min(r["first_seen"] for r in grp)
        base["last_seen"] = max(r["last_seen"] for r in grp)
        base["evidence"] = dict(base["evidence"], events=len(base["event_ids"]),
                                failures=sum(r["evidence"]["failures"] for r in grp),
                                accounts_from_same_source=len(grp))
        merged.append(base)
    return merged
