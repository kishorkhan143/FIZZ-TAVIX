# AuthSentinel Complete File Architecture

**Generated:** 2026-01-15  
**Status:** ✓ Complete - All directories and files created

## Backend Structure

```
log/backend/
├── main.py                          # FastAPI server (existing)
├── models.py                        # AuthEvent, Alert ORM (existing)
├── models_extended.py               # ✓ NEW: RiskContribution, RiskSnapshot, Incident tables
├── config.py                        # Settings (existing)
├── database.py                      # SQLAlchemy (existing)
├── schemas.py                       # Pydantic models (existing)
├── detection.py                     # Current threshold rules (existing)
├── ws_manager.py                    # WebSocket (existing)
├── authsentinel.db                  # SQLite database (existing)
│
├── risk_config.yaml                 # ✓ NEW: Risk model parameters
│                                      - half_life_seconds: 600
│                                      - incident_threshold: 60
│                                      - 9 signal definitions
│                                      - entity type config
│
├── scoring/                         # ✓ NEW DIRECTORY
│   ├── __init__.py
│   ├── scoring.py                   # Core: exponential decay + risk conversion
│   │                                  - RiskScorer class
│   │                                  - decay_function(dt_seconds)
│   │                                  - compute_risk_score()
│   │
│   └── signals.py                   # 9 configurable signals
│                                      - SignalComputer class
│                                      - failure_count()
│                                      - failure_velocity()
│                                      - burstiness()
│                                      - gap_compression()
│                                      - success_after_failures()
│                                      - multi_computer()
│                                      - password_spray()
│                                      - after_hours_success()
│                                      - unusual_computer()
│
├── incidents/                       # ✓ NEW DIRECTORY
│   ├── __init__.py
│   └── incident_manager.py          # Lifecycle management
│                                      - IncidentStatus enum
│                                      - compute_incident_id()
│                                      - should_open_incident()
│                                      - should_cool_incident()
│
├── importer/                        # ✓ NEW DIRECTORY
│   ├── __init__.py
│   └── csv_importer.py              # CSV validation + quarantine
│                                      - CSVImporter class
│                                      - parse_timestamp()
│                                      - compute_event_hash()
│                                      - import_csv()
│                                      - CSVImportResult
│
└── replay/                          # ✓ NEW DIRECTORY
    ├── __init__.py
    └── replay.py                    # Re-score with new config
                                      - ReplayEngine class
```

## Frontend Structure

```
log/frontend/
├── src/
│   ├── main.jsx                     # Entry point (existing)
│   ├── App.jsx                      # Main component (existing)
│   ├── App.css                      # Styles (existing)
│   ├── index.css                    # Global styles (existing)
│   ├── useAuthSentinel.js           # WebSocket hook (existing)
│   │
│   ├── components/                  # ✓ NEW DIRECTORY
│   │   ├── RiskChart.jsx            # Time-series line chart
│   │   │                              - LineChart with recharts
│   │   │                              - Reference lines (thresholds)
│   │   │                              - Real-time data
│   │   │
│   │   ├── RiskChart.css
│   │   │
│   │   ├── RiskGauge.jsx            # 0-100 circular gauge
│   │   │                              - getRiskBand()
│   │   │                              - getBandColor()
│   │   │                              - SVG rendering
│   │   │
│   │   └── RiskGauge.css            # Gauge styling
│   │
│   ├── pages/                       # ✓ NEW DIRECTORY
│   │   ├── EntityDetail.jsx         # Single entity view
│   │   │                              - Risk score + trend
│   │   │                              - Timeline chart
│   │   │                              - Active signals table
│   │   │
│   │   ├── IncidentPanel.jsx        # Incident manager
│   │   │                              - List incidents (OPEN/COOLED/CLOSED)
│   │   │                              - Filter by status
│   │   │                              - Review interface
│   │   │
│   │   └── Environment.jsx          # Settings page
│   │                                  - Edit risk_config parameters
│   │                                  - Lab hours, thresholds
│   │                                  - Save triggers replay
│   │
│   ├── hooks/                       # ✓ NEW DIRECTORY (reserved for future)
│   │
│   └── assets/                      # Images (existing)
│       ├── react.svg
│       ├── vite.svg
│       └── hero.png
│
├── public/
│   ├── favicon.svg
│   └── icons.svg
│
├── index.html
├── vite.config.js
├── package.json
├── package-lock.json
├── README.md
└── .oxlintrc.json
```

## Tests Structure

```
log/tests/
├── test_scoring.py                  # ✓ NEW
│                                      - TestRiskScoring class
│                                      - test_decay_at_half_life()
│                                      - test_score_from_accumulated()
│                                      - test_deterministic_scoring()
│                                      - test_order_independence()
│                                      - test_decay_over_time()
│
├── test_calibration.py              # ✓ NEW
│                                      - TestCalibration class
│                                      - test_normal_behavior_low_score()
│                                      - test_single_failure_moderate()
│                                      - test_multiple_failures_watches()
│                                      - test_burst_high_risk()
│
├── test_csv.py                      # ✓ NEW
│                                      - TestCSVImporter class
│                                      - test_timestamp_parsing()
│                                      - test_invalid_timestamp_returns_none()
│                                      - test_event_hash_consistency()
│                                      - test_different_events_different_hashes()
│
└── test_order.py                    # ✓ NEW
                                      - TestOrderIndependence class
                                      - test_scoring_independent_of_process_order()
```

## Sample Data Structure

```
log/sample_data/
├── normal_login.csv                 # ✓ NEW
│                                      - alice, 4 successful logins
│                                      - Expected score: NORMAL band (< 30)
│
├── single_typo.csv                  # ✓ NEW
│                                      - bob, 1 failure + 1 success
│                                      - Expected score: WATCH band (30-59)
│
├── brute_force_fast.csv             # ✓ NEW
│                                      - attacker, 5 failures + 1 success
│                                      - Expected score: HIGH_RISK band (≥ 60)
│
├── after_hours.csv                  # ✓ NEW
│                                      - charlie, 3 success logins at 22:00-23:00
│                                      - Expected: after_hours_success signal fires
│
└── password_spray.csv               # ✓ NEW
                                      - source 10.0.0.60, 6 different user failures
                                      - Expected: password_spray signal fires
```

## Documentation Structure

```
log/docs/
├── ARCHITECTURE.md                  # ✓ NEW
│                                      - System diagram
│                                      - File structure overview
│                                      - Data flows (live, CSV, replay)
│                                      - Integration points
│
├── RISK_MODEL.md                    # ✓ NEW
│                                      - Exponential decay formula
│                                      - 9 signal definitions with examples
│                                      - Entity types (ACCOUNT, COMPUTER, PAIR, SOURCE)
│                                      - Risk bands
│                                      - Incident lifecycle
│                                      - Brute-force attack example
│
└── SETUP.md                         # ✓ NEW
                                      - Prerequisites
                                      - Installation steps
                                      - Configuration (all 3 files)
                                      - Running AuthSentinel
                                      - Testing
                                      - Troubleshooting
                                      - Performance tuning
                                      - Reset procedures
```

## File Count Summary

| Category | Count | Notes |
|----------|-------|-------|
| **Backend New** | 10 | scoring, signals, incidents, importer, replay, config, models_extended |
| **Frontend New** | 6 | 2 components + 3 pages + 1 CSS |
| **Tests New** | 4 | scoring, calibration, CSV, order independence |
| **Sample Data** | 5 | normal, typo, brute_force, after_hours, spray |
| **Documentation** | 3 | architecture, risk_model, setup |
| **Total New** | 28 files | Complete ready-to-implement structure |

## Key Design Decisions Embedded in Files

1. **Single Scoring Function** → `scoring/scoring.py:RiskScorer.compute_risk_score()`
   - Used by live ingest, CSV import, and replay
   - Ensures determinism across all paths

2. **Exponential Decay** → `scoring/scoring.py:decay_function()`
   - Formula: `D(dt) = exp(-ln(2) * dt / HALF_LIFE)`
   - At dt = 600s, decay = 0.5

3. **9 Configurable Signals** → `scoring/signals.py:SignalComputer`
   - All 9 methods defined with configurable propagation
   - Parameters loaded from `risk_config.yaml`

4. **Entity Type Independence** → `risk_config.yaml:entity_types`
   - 4 types: ACCOUNT, COMPUTER, PAIR, SOURCE
   - Each has independent risk tracking

5. **Deterministic Incident IDs** → `incidents/incident_manager.py:compute_incident_id()`
   - Hash of (entity_type, entity_id, first_evidence_hash)
   - Re-imports are idempotent

6. **CSV Validation with Quarantine** → `importer/csv_importer.py`
   - Timestamp format parsing (multiple formats)
   - Duplicate detection via event_hash
   - Quarantine with reason reporting

## Next Steps

1. ✓ Task 1: File Architecture (COMPLETE)
2. → Task 4: Implement Risk Scoring Engine
   - Finish scoring/scoring.py integration
   - Complete signals/signals.py with real event computation
   - Add YAML config loading to backend

3. → Task 5: Implement CSV Importer
   - Hook to FastAPI endpoint
   - Database persistence

4. → Task 6: Update Database Models
   - Migration/creation for extended tables

5. → Task 7: API Endpoints
   - /api/entity/, /api/incidents/, /api/import/csv

6. → Task 8: Frontend Updates
   - Integrate new components and pages

7. → Task 9: Incidents Management
   - Full lifecycle (OPEN→COOLED→CLOSED)

8. → Task 10: Tests
   - Run all unit tests

9. → Task 11: Documentation & Demo
   - Complete setup guide and demo script
