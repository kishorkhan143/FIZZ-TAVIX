# ML Prediction Layer Grafted onto TAVIX Guard CSV Analytics

This change adds a scikit-learn prediction pipeline alongside the existing ten rule-based security detectors. When a CSV is uploaded, `predict()` is called on the normalized records; NORMAL findings are discarded; the rest are merged into existing rule alerts (source="RULE+ML") or inserted as new alerts (source="ML"). All ML fields are persisted, surfaced through a new `source` query parameter, and displayed in the frontend via a new "ML Review" column and "ML Analysis" modal section.

**Watch for:** (1) PASSWORD_SPRAY findings always land as source="ML" because the predictor collapses them to `user = "N accounts"` — no rule alert will ever match that key. Behaviorally correct but undocumented; a future rule-based spray detector would create a duplicate instead of merging. (2) The "both" filter label ("Rule + ML") maps to `source == "RULE+ML"` exclusively — a user could read it as "show alerts from either system," not "show only alerts that triggered both." (3) Safety wording in the modal relies entirely on `predictor.py`'s `REVIEW_LABEL` constants staying non-accusatory; there is no server-side validation that the review label text is safe before it reaches the UI.

**Verdict**: APPROVED

---

## High-level view

The ML hook sits after `SecurityDetector.detect_alerts()` inside a bare `except Exception` guard. Any model failure — missing file, bad import, runtime crash — silently downgrades to rule-only mode. The guard wraps both the `import` and the `predict()` call, so even a missing `model.joblib` is caught before the merge block.

The merge logic keys on `(user, ip)` with an `event_ids` overlap check. Brute-force and fail-then-success findings merge correctly with rule alerts because both systems key on the same user/IP pair. PASSWORD_SPRAY is always a new ML-only alert because the predictor collapses multi-user spray into a single finding with `user = "N accounts"` — this is correct behavior but the asymmetry is invisible to a future maintainer who adds a rule-based spray detector.

The "both" source filter option in the frontend dropdown maps to `source == "RULE+ML"`, meaning "only alerts where both rule and ML fired." The label "Rule + ML" in the dropdown is ambiguous — it reads naturally as an OR, not an AND.

Both integration tests passed per verification.md. `test_upload_without_model` correctly invalidates the in-process bundle cache (`_pred_mod._bundle = None`) before renaming the model file, which ensures the missing-model path is actually exercised rather than replayed from a prior load.

---

<details>
<summary>Issues (2)</summary>

1. **"both" filter label ambiguity** — The dropdown option "Rule + ML" (value `both`) maps to `source == "RULE+ML"`, filtering to alerts where both systems fired. A user could read this as "show alerts from rules OR from ML." Rename the option to "Merged (Rule+ML)" or add a tooltip clarifying the exclusive-and semantics.

2. **PASSWORD_SPRAY merge gap — undocumented** — Spray findings always land as source="ML" because `user = "N accounts"` never matches a rule alert key. This is correct now, but a future rule-based spray detector would create a duplicate alert instead of merging. Add a comment near the merge loop noting the spray collapse convention from `predictor.py`.

</details>

---

<details>
<summary>Details</summary>

## Try/except guard scope

The guard wraps both the import and the call:

```python
try:
    from ml.predictor import predict as ml_predict
    ml_findings = ml_predict(valid_records)
    ml_findings = [f for f in ml_findings if f.get("prediction") != "NORMAL"]
except Exception as ml_err:
    logger.warning(f"ML predictor skipped: {ml_err}")
    ml_findings = []
```

`ml_findings = []` causes the merge block to be skipped entirely (guarded by `if ml_findings:`), so the upload returns rule-only results with no error to the caller.

## PASSWORD_SPRAY always source="ML"

The predictor's `_merge_sprays` collapses all spray targets from the same IP into one finding with `user = "N accounts"`. The merge loop's `rule_lookup` is keyed on `(user, ip)`; no rule alert will ever have `user = "N accounts"`, so the overlap check is never reached for spray findings. They always fall through to the `else` branch and create a new ML-only alert. The test asserts exactly one PASSWORD_SPRAY alert from 198.51.100.50, which confirms this path, but the code contains no comment explaining why merge is structurally impossible for spray.

## Source filter "both" vs "ml"

- `source=ml` → `CsvAlert.source.in_(["ML", "RULE+ML"])` — returns anything ML touched
- `source=both` → `CsvAlert.source == "RULE+ML"` — returns only merged alerts

The frontend dropdown label for `both` is "Rule + ML", which reads as a union. The semantic is intersection. This is likely to confuse users filtering to understand what ML found that rules missed.

## Safety language in modal

The disclaimer is hardcoded JSX: "This is for review purposes only. The system does not block accounts or make final determinations." `ml_review_label` values come directly from the predictor's `REVIEW_LABEL` dict. There is no server-side check that prevents a future model update from emitting different wording through that field before it reaches the UI. This is a latent risk, not a current bug.

## Test gaps

Not tested: the `both`/`ml` source filter path via an HTTP request (service-layer filter is exercised only indirectly through `get_alerts()`). Not tested: WebSocket broadcast payload when ML-only high-risk alerts are present. Not tested: export CSV/JSON output with ML fields populated. All low severity.

</details>

---

<details>
<summary>File map</summary>

- `backend/csv_analytics/service.py` — ML predict() block with try/except after detect_alerts(); merge loop keyed on (user,ip)+event_id overlap; high_risk_alerts recompute; bulk-save CsvAlert extended with all nine ML columns; `source` filter param added to `get_alerts()`.
- `backend/csv_analytics/router.py` — `source: Optional[str]` query param added to `GET /alerts`; passed to `CsvAnalyticsService.get_alerts()`.
- `frontend/src/csv_analytics/CsvAlertsExplorer.jsx` — `sourceFilter` state; source param in fetch URL; Source dropdown (CustomSelect); "ML Review" column with risk-colored badge; colSpan 6→7.
- `frontend/src/csv_analytics/CsvAlertDetailsModal.jsx` — "ML Analysis" section gated on source=ML|RULE+ML; prediction, risk bar, confidence, review label, suggested step, time span, event IDs, evidence table, class probability bars, "review only" disclaimer.
- `backend/tests/test_ml_integration.py` — Two test functions: ML behavioral assertions on sample CSV and graceful degradation without model.joblib.

</details>
