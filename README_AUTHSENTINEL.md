# AuthSentinel: Risk-Based Brute-Force Detection for Lab Environments

A sophisticated, explainable risk-based detection system for credential abuse and brute-force attacks on Windows lab PCs.

## Features

### Core Risk Engine
- **Exponential Decay Scoring**: Continuous 0-100 risk scores (not binary alerts)
- **9 Configurable Signals**: failure_count, failure_velocity, burstiness, gap_compression, success_after_failures, multi_computer, password_spray, after_hours_success, unusual_computer
- **Deterministic & Order-Independent**: Same events always produce same score
- **Explainable**: Every signal contribution logged for audit trail

### Incident Lifecycle
- **OPEN**: Score ≥ 60 (incident threshold)
- **COOLED**: Score < 30 (cool threshold)
- **CLOSED**: Manual admin action
- **Reopen**: Score rises again after cooling
- **Human Review**: Track reviewer notes and decisions

### Data Import
- **CSV Batch Import**: Validate, quarantine, detect duplicates
- **Multiple Timestamp Formats**: Auto-detect from 7+ formats
- **Deduplication**: Content-based SHA256 hashing
- **Detailed Reporting**: See exactly what was quarantined and why

### Visualization
- **Risk Gauges**: Color-coded 0-100 circular gauges
- **Timeline Charts**: Real-time risk score evolution
- **Entity Detail Pages**: Deep dive into individual accounts/computers
- **Incident Management UI**: List, filter, review incidents

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Windows Event Logs (Laptop A)                               │
│ 4624 (Success) / 4625 (Failure)                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ FastAPI Backend (Central Server)                            │
│ ├── Risk Scoring Engine (exponential decay)                 │
│ ├── 9 Signal Detectors                                      │
│ ├── Incident Manager (lifecycle OPEN→COOLED)               │
│ ├── CSV Importer & Validator                                │
│ └── REST API + WebSocket                                    │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ↓               ↓               ↓
         SQLite        WebSocket        REST API
          (Data)     (Live Alerts)    (Queries)
            │               │               │
            └───────────────┼───────────────┘
                            │
                            ↓
        ┌─────────────────────────────────────┐
        │ React Frontend Dashboard (Laptop B)  │
        │ ├── Live risk gauges                │
        │ ├── Incident panel                  │
        │ ├── Entity detail pages             │
        │ └── Configuration UI                │
        └─────────────────────────────────────┘
```

## Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- Windows 10/11 (for event collector)
- Tailscale/LAN network

### Backend Setup

```bash
cd log/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from database import init_db; init_db()"

# Start backend
python main.py
# Runs on http://100.124.189.109:8000
```

### Frontend Setup

```bash
cd log/frontend

npm install
npm run dev
# Runs on http://100.124.189.109:5174
```

### Collector Setup (Laptop A)

```bash
cd log/collector

# Install Windows event dependencies
pip install pywin32
python Scripts/pywin32_postinstall.py -install

# Start collector (polls Windows Event Log every 2 seconds)
python collector.py
```

## Usage

### Run Demo

```bash
cd log
python demo.py
```

This imports sample CSV data, computes risk scores, and displays results.

### Import CSV Data

```bash
curl -X POST http://100.124.189.109:8000/api/import/csv \
  -H "X-Collector-Secret: your-secret-key" \
  -F "file=@events.csv"
```

CSV format:
```
username,computer,source_ip,timestamp,event_type,logon_type
alice,PC-LAB-01,192.168.1.100,2024-01-15 10:30:45,SUCCESS,3
bob,PC-LAB-02,192.168.1.101,2024-01-15 10:35:20,FAILURE,3
```

### Query Risk Scores

```bash
# Get entity risk detail
curl http://100.124.189.109:8000/api/entity/ACCOUNT/alice

# List incidents
curl http://100.124.189.109:8000/api/incidents?status=OPEN

# Get incident detail
curl http://100.124.189.109:8000/api/incidents/{incident_id}

# Get statistics
curl http://100.124.189.109:8000/api/stats/risk
```

### Review Incident

```bash
curl -X POST http://100.124.189.109:8000/api/incidents/{id}/review \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_name": "alice@lab.com",
    "notes": "Confirmed: user was testing password change"
  }'
```

## Configuration

Edit `log/backend/risk_config.yaml`:

```yaml
# Decay half-life (seconds)
# At this time, older signals have half their weight
half_life_seconds: 600

# Incident thresholds
incident_threshold: 60   # Open incident when score ≥ this
cool_threshold: 30       # Mark COOLED when score < this

# Lab hours (for after_hours_success signal)
lab_hours_start: 8       # 08:00 AM
lab_hours_end: 18        # 06:00 PM

# Signal coefficients (configurable per signal)
# Higher coefficient = more impact on risk score
signals:
  failure_count:
    base_coefficient: 1.0
    propagation:
      PAIR: 1.0
      ACCOUNT: 0.6
      COMPUTER: 0.3
      SOURCE: 0.5
  # ... (8 more signals)
```

### Tuning Guide

- **Decrease half_life** (e.g., 300): React faster to recent attacks, more sensitive
- **Increase half_life** (e.g., 1200): Smoother, less noisy, responds slower
- **Lower incident_threshold** (e.g., 50): More incidents, more false positives
- **Raise incident_threshold** (e.g., 70): Fewer incidents, might miss real attacks

## Risk Model

### Formula

```
X(t) = Σ c_i * D(t - t_i)    [accumulated risk]
D(dt) = exp(-ln(2) * dt / HALF_LIFE)    [exponential decay]
Risk(X) = 100 * (1 - exp(-X))    [0-100 score]
```

### Signals (9 Total)

1. **failure_count**: Recent failures in lookback window
2. **failure_velocity**: Failures per minute (rate)
3. **burstiness**: Sudden cluster of failures (spike)
4. **gap_compression**: Failure intervals shrinking (acceleration)
5. **success_after_failures**: Successful login after many failures (breach)
6. **multi_computer**: Account on multiple machines (lateral movement)
7. **password_spray**: Many targets from one source (spray attack)
8. **after_hours_success**: Success outside lab hours (anomalous)
9. **unusual_computer**: Account on never-before-seen machine (new compromise)

### Risk Bands

- **NORMAL (0-29)**: Background noise 🟢
- **WATCH (30-59)**: Monitor closely 🟡
- **SUSPICIOUS (60-79)**: Incident opened 🟠
- **HIGH_RISK (80-100)**: Critical attack pattern 🔴

### Entity Types

- **ACCOUNT**: User across all machines (account compromise)
- **COMPUTER**: All users on one machine (machine under attack)
- **PAIR**: (user, machine) combination (brute-force on specific account)
- **SOURCE**: IP address (attacker machine)

## Testing

Run all tests:

```bash
cd log
python -m pytest tests/ -v
```

Individual test suites:

```bash
python -m pytest tests/test_scoring.py -v         # Core decay formula
python -m pytest tests/test_calibration.py -v    # Risk band boundaries
python -m pytest tests/test_csv.py -v            # CSV import
python -m pytest tests/test_order.py -v          # Order independence
python -m pytest tests/test_end_to_end.py -v    # Full workflows
```

## Files

### Core Modules
- `backend/scoring/scoring.py`: Exponential decay + risk conversion
- `backend/scoring/signals.py`: 9 signal detectors
- `backend/incidents/incident_manager.py`: Deterministic ID generation
- `backend/incidents/incident_service.py`: Lifecycle management
- `backend/importer/csv_importer.py`: CSV validation + import
- `backend/scoring_orchestrator.py`: End-to-end pipeline
- `backend/risk_db.py`: Database operations
- `backend/models_unified.py`: ORM models

### API
- `backend/api_risk.py`: REST endpoints
- `backend/main.py`: FastAPI app (existing)

### Frontend
- `frontend/src/components/RiskGauge.jsx`: 0-100 circular gauge
- `frontend/src/components/RiskChart.jsx`: Timeline chart
- `frontend/src/pages/EntityDetail.jsx`: Entity risk view
- `frontend/src/pages/IncidentPanel.jsx`: Incident manager
- `frontend/src/pages/Environment.jsx`: Configuration UI

### Sample Data
- `sample_data/normal_login.csv`: Low-risk baseline
- `sample_data/single_typo.csv`: Minimal risk (one failure + success)
- `sample_data/brute_force_fast.csv`: HIGH_RISK (5 failures + success)
- `sample_data/after_hours.csv`: Off-hours access
- `sample_data/password_spray.csv`: Multiple accounts from one IP

### Documentation
- `docs/ARCHITECTURE.md`: System design
- `docs/RISK_MODEL.md`: Formula and signals
- `docs/SETUP.md`: Detailed setup guide

## Assumptions

- Lab timezone: US Eastern (configurable)
- Lab hours: 08:00-18:00 (configurable)
- Windows-only event collector (pywin32)
- Trusted lab network (no auth on APIs)
- SQLite acceptable for < 100K events
- No database migrations (file-based prototype)

## What's NOT Included

- Machine learning models
- Automatic account lockout/blocking
- Password storage
- Multi-tenancy
- Production-grade authentication
- High-availability deployment

## Future Enhancements

1. **Replay Engine**: Re-score all events with new config
2. **LDAP Integration**: User/computer attribute context
3. **Export**: PDF incident reports
4. **Alerting**: Email/Slack notifications
5. **SIEM Integration**: Forward to Splunk/ELK
6. **MITRE Mapping**: Attach TTPs to signals
7. **Multi-lab Support**: Multiple sites in same dashboard

## Troubleshooting

### Backend won't start
```bash
# Check port 8000 available
netstat -ano | findstr :8000

# Check database writable
ls -la backend/authsentinel.db

# Check config loaded
python -c "import yaml; print(yaml.safe_load(open('backend/risk_config.yaml')))"
```

### No events appearing
```bash
# Check collector running (Laptop A)
curl http://100.124.189.109:8000/api/events

# Check WebSocket connected
# (browser console should show "CONNECTED" message)

# Check X-Collector-Secret header (if enabled)
```

### Scores seem wrong
```bash
# Verify decay constant
python -c "from backend.scoring.scoring import RiskScorer; s=RiskScorer(); print(s.decay_function(600))"
# Should print ~0.5

# Verify signal firing (debug logs)
# Check backend logs for "Computed signals"
```

## Support

For questions or issues:
1. Check `docs/SETUP.md` for detailed setup
2. Review `docs/RISK_MODEL.md` for formula details
3. Run `python demo.py` to verify installation
4. Check backend logs: `backend/main.py` prints to console

## License

Educational lab tool. Use for learning Windows security monitoring.

## Authors

Built as a comprehensive risk-based detection system for educational lab environments.

---

**Version**: 1.0.0  
**Updated**: January 2026
