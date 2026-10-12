# Implementation Plan — ML Integration for TAVIX Guard CSV Analytics

## Pre-read findings

- **`models.py`** — `CsvAlert` already has all ML columns (`ml_prediction`, `ml_risk`,
  `ml_confidence`, `ml_review_label`, `suggested_step`, `class_probabilities`, `evidence`,
  `anomaly_score`, `source`) and `to_dict()` already returns them. **No schema migration needed.**
- **`requirements.txt`** — `scikit-learn==1.3.2`, `numpy==1.24.3`, `joblib==1.3.2` are already
  present. **No pip changes needed.**
- **`predictor.py`** — `predict(records)` groups records into `(user, ip)` session windows and
  returns one dict per window. Key fields: `user`, `ip`, `event_ids` (list of `row_number`),
  `prediction`, `review_label`, `ml_risk`, `confidence`, `anomaly_score`,
  `class_probabilities`, `evidence`, `suggested_human_step`, `first_seen`, `last_seen`.
  `_merge_sprays` is called internally, so PASSWORD_SPRAY from the same IP arrives already
  collapsed (one entry, `user = "N accounts"`).
- **`service.py`** — ML hook goes at line ~250 right after step 7 (`alerts_list =
  SecurityDetector.detect_alerts(...)`). The bulk-save block at step 9 constructs `CsvAlert`
  objects with hard-coded fields — the ML fields must be added there.
- **`router.py`** — `get_csv_alerts` at line ~86 is clean; `source` query param must be added
  and threaded through to `get_alerts()`.
- **`CsvAlertsExplorer.jsx`** — 6-column table; "ML Review" column and "Source" filter go in
  without touching any existing columns.
- **`CsvAlertDetailsModal.jsx`** — "ML Analysis" section appended after "Why this was flagged"
  block, guarded by `alert.source === 'ML' || alert.source === 'RULE+ML'`.
- **`sample_security_events.csv`** — 20 rows; david has 6 rapid failures (BRUTE_FORCE), bob has
  4 failures then success (FAIL_THEN_SUCCESS), user1–4 from 198.51.100.50 are spray targets,
  alice and charlie have a single success each (NORMAL).

---

## Ordered Steps

- [ ] 1. **`service.py` — Add ML predict() call with try/except after detect_alerts**

  Immediately after `alerts_list = SecurityDetector.detect_alerts(import_id=import_id, records=valid_records)`
  (step 7, ~line 250), insert the following logic:

  ```python
  # --- ML Prediction (safe, never crashes upload) ---
  try:
      from ml.predictor import predict as ml_predict
      ml_findings = ml_predict(valid_records)
      ml_findings = [f for f in ml_findings if f.get("prediction") != "NORMAL"]
  except Exception as ml_err:
      logger.warning(f"ML predictor skipped: {ml_err}")
      ml_findings = []
  ```

  Safety rule: this is inside try/except; any missing model.joblib, import error, or runtime
  error silently downgrades to rule-only mode.

  File: `backend/csv_analytics/service.py`
  Verify: `cd backend && python -m pytest tests/test_csv_analytics.py -q` — existing tests
  still pass (they don't exercise ML but the import must not break them).

- [ ] 2. **`service.py` — Add merge logic: produce final `alerts_list` with ML fields populated**

  Directly after the try/except block from step 1, add the merge function:

  ```python
  # Build lookup: rule alerts keyed by (user, ip)
  def _overlapping(ids_a, ids_b):
      return bool(set(ids_a) & set(ids_b))

  rule_lookup = {}   # (user, ip) -> alert dict index in alerts_list
  for idx, a in enumerate(alerts_list):
      rule_lookup[(a["user"], a["ip"])] = idx

  for finding in ml_findings:
      f_user = finding.get("user", "")
      f_ip   = finding.get("ip", "")
      f_ids  = finding.get("event_ids", [])
      match_idx = rule_lookup.get((f_user, f_ip))
      if match_idx is not None and _overlapping(
              alerts_list[match_idx].get("related_events", []), f_ids):
          # Merge: augment existing rule alert
          a = alerts_list[match_idx]
          a["source"] = "RULE+ML"
          a["ml_prediction"]     = finding["prediction"]
          a["ml_risk"]           = finding["ml_risk"]
          a["ml_confidence"]     = finding["confidence"]
          a["ml_review_label"]   = finding["review_label"]
          a["suggested_step"]    = finding["suggested_human_step"]
          a["class_probabilities"] = finding["class_probabilities"]
          a["evidence"]          = finding["evidence"]
          a["anomaly_score"]     = finding["anomaly_score"]
      else:
          # New ML-only alert
          ml_alert = {
              "id": str(uuid.uuid4())[:8],
              "import_id": import_id,
              "alert_type": finding["prediction"],
              "severity": "HIGH" if finding["ml_risk"] >= 70 else (
                           "MEDIUM" if finding["ml_risk"] >= 40 else "LOW"),
              "risk_score": finding["ml_risk"],
              "user": f_user,
              "ip": f_ip,
              "country": (valid_records[0].get("country") if valid_records else None),
              "message": finding["review_label"],
              "first_seen": finding["first_seen"],
              "last_seen": finding["last_seen"],
              "event_count": len(f_ids),
              "failed_count": finding.get("evidence", {}).get("failures", 0),
              "time_window_seconds": int(
                  (finding["last_seen"] - finding["first_seen"]).total_seconds()
                  if finding.get("last_seen") and finding.get("first_seen") else 0),
              "status": "OPEN",
              "reasons": [finding["review_label"]],
              "related_events": f_ids,
              "source": "ML",
              "ml_prediction": finding["prediction"],
              "ml_risk": finding["ml_risk"],
              "ml_confidence": finding["confidence"],
              "ml_review_label": finding["review_label"],
              "suggested_step": finding["suggested_human_step"],
              "class_probabilities": finding["class_probabilities"],
              "evidence": finding["evidence"],
              "anomaly_score": finding["anomaly_score"],
              "created_at": datetime.now(timezone.utc),
          }
          alerts_list.append(ml_alert)
  ```

  Note: For PASSWORD_SPRAY spray-merged findings `user` is `"N accounts"` — keep as-is
  (the predictor already merged them).

  File: `backend/csv_analytics/service.py`
  Verify: same as step 1 — `python -m pytest tests/test_csv_analytics.py -q` passes.

- [ ] 3. **`service.py` — Update `high_risk_alerts` recompute and update `csv_import_obj` counts**

  After the merge block (step 2), add:

  ```python
  # Recompute counts to include ML-only alerts
  high_risk_alerts = [a for a in alerts_list if a["severity"] in ("CRITICAL", "HIGH")]
  ```

  Then update the two fields on `csv_import_obj` (already constructed further below) to use the
  final `alerts_list` length. The `csv_import_obj` is constructed after this block at step 9;
  change those two lines:

  ```python
  alerts_count=len(alerts_list),       # was already alerts_list; now reflects ML additions
  high_risk_count=len(high_risk_alerts), # recomputed above
  ```

  (These lines in the existing code already use `alerts_list` and `high_risk_alerts` by name,
  so no literal text change is needed here — only confirm they reference the recomputed
  variables set above.)

  File: `backend/csv_analytics/service.py`
  Verify: `python -m pytest tests/test_csv_analytics.py -q`

- [ ] 4. **`service.py` — Update bulk-save `db_alerts` to write all ML fields**

  In the bulk-save block, replace the existing `CsvAlert(...)` construction to include all ML
  fields. The current constructor omits `source`, `ml_prediction`, `ml_risk`, `ml_confidence`,
  `ml_review_label`, `suggested_step`, `class_probabilities`, `evidence`, `anomaly_score`.

  Replace the list comprehension for `db_alerts` with:

  ```python
  db_alerts = [
      CsvAlert(
          id=f"{import_id[:8]}-{a['id']}",
          import_id=import_id,
          alert_type=a["alert_type"],
          severity=a["severity"],
          risk_score=a["risk_score"],
          user=a["user"],
          ip=a["ip"],
          country=a.get("country"),
          message=a["message"],
          first_seen=a["first_seen"],
          last_seen=a["last_seen"],
          event_count=a["event_count"],
          failed_count=a["failed_count"],
          time_window_seconds=a["time_window_seconds"],
          status=a["status"],
          reasons=json.dumps(a["reasons"]),
          related_events=json.dumps(a.get("related_events", [])),
          source=a.get("source", "RULE"),
          ml_prediction=a.get("ml_prediction"),
          ml_risk=a.get("ml_risk"),
          ml_confidence=a.get("ml_confidence"),
          ml_review_label=a.get("ml_review_label"),
          suggested_step=a.get("suggested_step"),
          class_probabilities=json.dumps(a["class_probabilities"])
              if a.get("class_probabilities") else None,
          evidence=json.dumps(a["evidence"])
              if a.get("evidence") else None,
          anomaly_score=a.get("anomaly_score"),
          created_at=a["created_at"],
      )
      for a in alerts_list
  ]
  ```

  File: `backend/csv_analytics/service.py`
  Verify: `python -m pytest tests/test_csv_analytics.py -q` passes; no SQLAlchemy column errors.

- [ ] 5. **`service.py` — Fix the alert `id` construction for ML-only alerts**

  The bulk-save uses `f"{import_id[:8]}-{a['id']}"`. Rule alerts from `SecurityDetector` have
  an `id` field (e.g. `"ALERT-001"`). ML-only alert dicts built in step 2 also have `"id"`
  set to a UUID fragment. No change needed to the id line — just confirm the `id` key is
  present in both paths (it is, per step 2 above).

  File: `backend/csv_analytics/service.py`
  Verify: manual smoke-check — upload `sample_security_events.csv` and confirm no key errors
  in the response.

- [ ] 6. **`router.py` — Add optional `source` query param to `GET /alerts`**

  In `get_csv_alerts()`, add:

  ```python
  source: Optional[str] = Query(None, description="all | rule | ml | both"),
  ```

  Pass it through to the service:

  ```python
  alerts = CsvAnalyticsService.get_alerts(
      import_id=import_id,
      severity=severity,
      status=status,
      source=source,
      db=db,
  )
  ```

  File: `backend/csv_analytics/router.py`
  Verify: FastAPI starts without errors; `GET /api/csv/alerts?source=ml` returns HTTP 200.

- [ ] 7. **`service.py` — Add `source` filter to `get_alerts()`**

  In `CsvAnalyticsService.get_alerts()`, add `source: Optional[str] = None` parameter, then
  after the existing `status` filter block add:

  ```python
  if source and source.lower() not in ("all", ""):
      if source.lower() == "rule":
          stmt = stmt.where(CsvAlert.source == "RULE")
      elif source.lower() == "ml":
          stmt = stmt.where(CsvAlert.source.in_(["ML", "RULE+ML"]))
      elif source.lower() == "both":
          stmt = stmt.where(CsvAlert.source == "RULE+ML")
  ```

  File: `backend/csv_analytics/service.py`
  Verify: `python -m pytest tests/test_csv_analytics.py -q` passes.

- [ ] 8. **`CsvAlertsExplorer.jsx` — Add `sourceFilter` state and "Source" dropdown**

  Add state:
  ```js
  const [sourceFilter, setSourceFilter] = useState('all');
  ```

  In the `fetchAlerts` URL builder, add:
  ```js
  if (sourceFilter !== 'all') url += `source=${sourceFilter}&`;
  ```

  Add `sourceFilter` to the `useCallback` dependency array.

  In the filters bar, add a third `CustomSelect` after the Status dropdown:
  ```jsx
  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
    <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
      Source:
    </span>
    <CustomSelect
      value={sourceFilter}
      onChange={(e) => setSourceFilter(e.target.value)}
      options={[
        { value: 'all',  label: 'All' },
        { value: 'rule', label: 'Rule Only' },
        { value: 'ml',   label: 'ML Only' },
        { value: 'both', label: 'Rule+ML' },
      ]}
      style={{ minWidth: '130px' }}
    />
  </div>
  ```

  File: `frontend/src/csv_analytics/CsvAlertsExplorer.jsx`
  Verify: frontend compiles without errors (`npm run build` from `frontend/`).

- [ ] 9. **`CsvAlertsExplorer.jsx` — Add "ML Review" column to the alerts table**

  Change `<th>Risk Level</th>` to add one column after it:
  ```jsx
  <th>Risk Level</th>
  <th>ML Review</th>
  ```

  Update the `colSpan` on the loading/empty rows from `"6"` to `"7"`.

  In the table row, after the Risk Level `<td>`, add:
  ```jsx
  <td>
    {(al.source === 'ML' || al.source === 'RULE+ML') && al.ml_review_label
      ? (
        <span style={{
          fontSize: '11px',
          fontWeight: 600,
          padding: '2px 8px',
          borderRadius: '100px',
          background: al.ml_risk >= 70 ? '#ef4444'
                    : al.ml_risk >= 40 ? '#f59e0b'
                    : '#10b981',
          color: '#fff',
          whiteSpace: 'nowrap',
        }}>
          {al.ml_review_label}
        </span>
      )
      : <span style={{ color: 'var(--text-tertiary)' }}>—</span>
    }
  </td>
  ```

  File: `frontend/src/csv_analytics/CsvAlertsExplorer.jsx`
  Verify: frontend compiles; ML badge visible for ML/RULE+ML alerts, "—" for RULE alerts.

- [ ] 10. **`CsvAlertDetailsModal.jsx` — Add "ML Analysis" section**

  After the closing `</div>` of the `alert-flagged-section` block (the "Why this was flagged"
  section), add the following JSX, guarded by the source check:

  ```jsx
  {/* ML Analysis — only shown when ML contributed to this alert */}
  {(alert.source === 'ML' || alert.source === 'RULE+ML') && (
    <div className="alert-flagged-section" style={{ marginTop: '12px' }}>
      <h4 className="alert-flagged-heading">ML Analysis</h4>

      <div className="alert-details-table">

        {/* ML Prediction */}
        <div className="alert-details-row">
          <div className="alert-details-label">ML Prediction</div>
          <div className="alert-details-value" style={{ fontWeight: 600 }}>
            {alert.ml_prediction ? alert.ml_prediction.replace(/_/g, ' ') : '—'}
          </div>
        </div>

        {/* ML Risk Score */}
        <div className="alert-details-row">
          <div className="alert-details-label">ML Risk Score</div>
          <div className="alert-details-value">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{
                flex: 1, height: '6px', borderRadius: '3px',
                background: 'var(--border-light)', overflow: 'hidden',
              }}>
                <div style={{
                  width: `${alert.ml_risk ?? 0}%`, height: '100%', borderRadius: '3px',
                  background: (alert.ml_risk ?? 0) >= 70 ? '#ef4444'
                            : (alert.ml_risk ?? 0) >= 40 ? '#f59e0b' : '#10b981',
                }} />
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', minWidth: '32px' }}>
                {alert.ml_risk ?? '—'}
              </span>
            </div>
          </div>
        </div>

        {/* Confidence */}
        <div className="alert-details-row">
          <div className="alert-details-label">Confidence</div>
          <div className="alert-details-value">
            {alert.ml_confidence != null
              ? `${(alert.ml_confidence * 100).toFixed(1)}%`
              : '—'}
          </div>
        </div>

        {/* Review Label */}
        <div className="alert-details-row">
          <div className="alert-details-label">Review Label</div>
          <div className="alert-details-value">{alert.ml_review_label ?? '—'}</div>
        </div>

        {/* Suggested Step */}
        {alert.suggested_step && (
          <div className="alert-details-row">
            <div className="alert-details-label">Suggested Step</div>
            <div className="alert-details-value" style={{ fontStyle: 'italic', color: 'var(--text-secondary)' }}>
              {alert.suggested_step}
            </div>
          </div>
        )}

        {/* Time Span */}
        {alert.first_seen && alert.last_seen && (() => {
          const t0 = new Date(alert.first_seen);
          const t1 = new Date(alert.last_seen);
          const mins = Math.round((t1 - t0) / 60000);
          return (
            <div className="alert-details-row">
              <div className="alert-details-label">Time Span</div>
              <div className="alert-details-value" style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                {fmtTime(alert.first_seen)} – {fmtTime(alert.last_seen)}
                {mins > 0 && <span style={{ marginLeft: '6px', color: 'var(--text-tertiary)' }}>({mins} min)</span>}
              </div>
            </div>
          );
        })()}

        {/* Event IDs */}
        {Array.isArray(alert.related_events) && alert.related_events.length > 0 && (
          <div className="alert-details-row">
            <div className="alert-details-label">Event IDs</div>
            <div className="alert-details-value" style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
              {alert.related_events.slice(0, 20).join(', ')}
              {alert.related_events.length > 20 && ` … +${alert.related_events.length - 20} more`}
            </div>
          </div>
        )}

      </div>

      {/* Evidence table */}
      {alert.evidence && Object.keys(alert.evidence).length > 0 && (
        <div style={{ marginTop: '8px' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
            Evidence
          </div>
          <div className="alert-details-table">
            {Object.entries(alert.evidence).map(([k, v]) => (
              <div key={k} className="alert-details-row">
                <div className="alert-details-label" style={{ fontSize: '11px' }}>
                  {k.replace(/_/g, ' ')}
                </div>
                <div className="alert-details-value" style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                  {String(v)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Class Probabilities */}
      {alert.class_probabilities && Object.keys(alert.class_probabilities).length > 0 && (
        <div style={{ marginTop: '8px' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
            Class Probabilities
          </div>
          <div className="alert-details-table">
            {Object.entries(alert.class_probabilities)
              .sort(([, a], [, b]) => b - a)
              .map(([cls, prob]) => (
                <div key={cls} className="alert-details-row">
                  <div className="alert-details-label" style={{ fontSize: '11px' }}>
                    {cls.replace(/_/g, ' ')}
                  </div>
                  <div className="alert-details-value" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '80px', height: '4px', borderRadius: '2px', background: 'var(--border-light)', overflow: 'hidden' }}>
                      <div style={{ width: `${(prob * 100).toFixed(0)}%`, height: '100%', background: 'var(--accent-primary)', borderRadius: '2px' }} />
                    </div>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                      {(prob * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

    </div>
  )}
  ```

  File: `frontend/src/csv_analytics/CsvAlertDetailsModal.jsx`
  Verify: frontend compiles; open a RULE+ML or ML alert and confirm the "ML Analysis" section
  renders with prediction, risk bar, evidence table, and class probabilities.

- [ ] 11. **`backend/tests/test_ml_integration.py` — Create pytest integration test**

  Create `backend/tests/test_ml_integration.py`. The test:

  1. Inserts `sys.path` so `backend/` is importable.
  2. Creates an in-memory SQLite session using `init_db` and `SessionLocal`.
  3. Reads `sample_security_events.csv` as bytes from the known absolute path
     `<workspace>/Working prototype/log/sample_security_events.csv`.
  4. Calls `CsvAnalyticsService.process_csv_upload(file_bytes, "sample_security_events.csv", db)`.
  5. Calls `CsvAnalyticsService.get_alerts(import_id=result["import_id"], severity=None, status=None, source=None, db=db)`.
  6. Builds a lookup `alerts_by_user = {a["user"]: a for a in alerts}`.
  7. Assertions:

     ```python
     # david: BRUTE_FORCE
     david_alerts = [a for a in alerts if a.get("user") == "david" and a.get("source") in ("ML","RULE+ML")]
     assert any(a.get("ml_prediction") == "BRUTE_FORCE" for a in david_alerts), \
         "david should be flagged BRUTE_FORCE"

     # bob: FAIL_THEN_SUCCESS
     bob_alerts = [a for a in alerts if a.get("user") == "bob" and a.get("source") in ("ML","RULE+ML")]
     assert any(a.get("ml_prediction") == "FAIL_THEN_SUCCESS" for a in bob_alerts), \
         "bob should be flagged FAIL_THEN_SUCCESS"

     # user1-4 spray from 198.51.100.50: single PASSWORD_SPRAY incident
     spray_alerts = [a for a in alerts
                     if a.get("ip") == "198.51.100.50"
                     and a.get("ml_prediction") == "PASSWORD_SPRAY"
                     and a.get("source") in ("ML","RULE+ML")]
     assert len(spray_alerts) == 1, \
         f"Expected exactly one PASSWORD_SPRAY from 198.51.100.50, got {len(spray_alerts)}"

     # alice and charlie: NOT flagged by ML
     ml_alerts = [a for a in alerts if a.get("source") in ("ML","RULE+ML")]
     assert not any(a.get("user") == "alice" for a in ml_alerts), "alice must not be ML-flagged"
     assert not any(a.get("user") == "charlie" for a in ml_alerts), "charlie must not be ML-flagged"

     # at least one alert has an ML source
     assert any(a.get("source") in ("ML","RULE+ML") for a in alerts), \
         "At least one alert must have ML source"
     ```

  8. Separate test function `test_upload_without_model()`:
     - Temporarily rename `backend/ml/model.joblib` to `model.joblib.bak`.
     - Call `process_csv_upload(...)` in a fresh db session.
     - Assert the result has `"success": True` and `alerts` count >= 0.
     - Rename the file back in a `finally` block.
     - Assert at least one alert exists (rule-only).

  File: `backend/tests/test_ml_integration.py`
  Verify: `cd backend && python -m pytest tests/test_ml_integration.py -v` — all assertions pass.

---

## Safety rules checklist (must remain true after all changes)

- All `ml_review_label` values and `message` strings for ML-only alerts use "Needs review"
  phrasing sourced directly from `predictor.py:REVIEW_LABEL` — never "guilty" or "blocked".
- `SecurityDetector.detect_alerts()` is never touched (rules 1–10 intact).
- `backend/ml/` is read-only — only `predictor.py` is imported, nothing written.
- If `predict()` raises any exception, upload continues with rule-only alerts (step 1 guard).
- Existing RULE alerts (`source="RULE"`) are unchanged; the `source` field defaults to `"RULE"`
  in the existing `CsvAlert` model definition.

---

## Dependency order

Steps 1 → 2 → 3 → 4 must be done in order (all in `service.py`).
Steps 6 and 7 must be done together (router + service `get_alerts` signature).
Steps 8 and 9 are independent of each other and can be done in either order.
Step 10 depends on steps 1–4 (needs ML data in alerts).
Step 11 depends on steps 1–7 (needs the full backend pipeline working).
