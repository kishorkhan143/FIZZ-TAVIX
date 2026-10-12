"""
Feature extraction for the login-anomaly model.

Input  : normalized records (same dicts produced by csv_analytics.normalizer):
         {row_number, timestamp(datetime), user, ip, status('SUCCESS'|'FAILURE'),
          target_computer(optional), country(optional)}
Output : one feature vector per *session window* = events of one (user, source)
         pair separated from the next by more than SESSION_GAP_SEC.

Pure python + numpy. No pandas, so inference stays tiny and fast.
"""
from collections import defaultdict
from datetime import timedelta
import math
import numpy as np

SESSION_GAP_SEC = 15 * 60       # new window after 15 min of silence
CONTEXT_PAD_SEC = 5 * 60        # look +/-5 min around a window for cross-account context
LAB_START_HOUR = 8              # keep in sync with risk_config.yaml (after_hours_success)
LAB_END_HOUR = 18

FEATURE_NAMES = [
    "n_events", "n_fail", "fail_ratio", "max_consec_fail", "duration_s",
    "mean_gap_s", "min_gap_s", "gap_cv", "fail_per_min",
    "success_after_fail", "fails_before_first_success", "ends_with_success",
    "ctx_distinct_users_from_src", "ctx_fail_users_from_src",
    "ctx_distinct_src_for_user", "ctx_distinct_computers", "n_countries",
    "after_hours_success", "after_hours_ratio", "hour_sin", "hour_cos",
]
N_FEATURES = len(FEATURE_NAMES)


def _is_fail(r):
    return r.get("status") == "FAILURE"


def _after_hours(ts):
    return not (LAB_START_HOUR <= ts.hour < LAB_END_HOUR)


def build_windows(records):
    """Group records into (user, ip) session windows. Returns list of lists (time-sorted)."""
    pairs = defaultdict(list)
    for r in records:
        pairs[(r.get("user"), r.get("ip"))].append(r)
    windows = []
    for recs in pairs.values():
        recs = sorted(recs, key=lambda x: x["timestamp"])
        cur = [recs[0]]
        for r in recs[1:]:
            if (r["timestamp"] - cur[-1]["timestamp"]).total_seconds() > SESSION_GAP_SEC:
                windows.append(cur)
                cur = []
            cur.append(r)
        windows.append(cur)
    return windows


def _index_context(records):
    by_ip, by_user = defaultdict(list), defaultdict(list)
    for r in records:
        by_ip[r.get("ip")].append(r)
        by_user[r.get("user")].append(r)
    return by_ip, by_user


def window_features(win, by_ip, by_user):
    t0, t1 = win[0]["timestamp"], win[-1]["timestamp"]
    lo, hi = t0 - timedelta(seconds=CONTEXT_PAD_SEC), t1 + timedelta(seconds=CONTEXT_PAD_SEC)
    ip, user = win[0].get("ip"), win[0].get("user")

    n = len(win)
    fails = [_is_fail(r) for r in win]
    n_fail = sum(fails)
    dur = (t1 - t0).total_seconds()
    gaps = np.array([(win[i + 1]["timestamp"] - win[i]["timestamp"]).total_seconds()
                     for i in range(n - 1)], dtype=float)
    mean_gap = float(gaps.mean()) if gaps.size else 0.0
    min_gap = float(gaps.min()) if gaps.size else 0.0
    gap_cv = float(gaps.std() / mean_gap) if gaps.size > 1 and mean_gap > 0 else 0.0

    consec = best = 0
    for f in fails:
        consec = consec + 1 if f else 0
        best = max(best, consec)

    first_succ = next((i for i, f in enumerate(fails) if not f), None)
    fails_before = sum(fails[:first_succ]) if first_succ is not None else n_fail
    succ_after_fail = int(first_succ is not None and fails_before >= 2)

    ctx_ip = [r for r in by_ip.get(ip, []) if lo <= r["timestamp"] <= hi]
    ctx_user = [r for r in by_user.get(user, []) if lo <= r["timestamp"] <= hi]
    ctx_users = {r.get("user") for r in ctx_ip}
    ctx_fail_users = {r.get("user") for r in ctx_ip if _is_fail(r)}
    ctx_src = {r.get("ip") for r in ctx_user}
    comps = {r.get("target_computer") for r in ctx_user if r.get("target_computer")}
    countries = {r.get("country") for r in win if r.get("country")}

    ah_succ = sum(1 for r in win if not _is_fail(r) and _after_hours(r["timestamp"]))
    ah_ratio = sum(1 for r in win if _after_hours(r["timestamp"])) / n
    hr = t0.hour + t0.minute / 60.0

    return [
        n, n_fail, n_fail / n, best, dur, mean_gap, min_gap, gap_cv,
        (n_fail / max(dur, 1.0)) * 60.0,
        succ_after_fail, fails_before, int(not fails[-1]),
        len(ctx_users), len(ctx_fail_users), len(ctx_src), len(comps), len(countries),
        ah_succ, ah_ratio, math.sin(2 * math.pi * hr / 24), math.cos(2 * math.pi * hr / 24),
    ]


def extract(records):
    """-> (X: ndarray [n_windows, N_FEATURES], windows: list[list[record]])"""
    if not records:
        return np.zeros((0, N_FEATURES)), []
    windows = build_windows(records)
    by_ip, by_user = _index_context(records)
    X = np.array([window_features(w, by_ip, by_user) for w in windows], dtype=float)
    return X, windows
