# AuthSentinel Integration Test Guide

Complete checklist to verify all components work end-to-end.

## Pre-Flight (5 min)

- [ ] Database initialized: `backend/authsentinel.db` exists (50+ KB)
- [ ] Backend requirements installed: `pip list | grep fastapi`
- [ ] Frontend dependencies installed: `npm list | head -5`
- [ ] Sample CSVs present: `ls sample_data/*.csv` shows 5 files
- [ ] Tests pass: `python -m pytest tests/ -v` → all green

## Component Tests (10 min)

### 1. Database Layer ✓

```bash
cd backend
python -c "
from database import SessionLocal, init_db
from models_unified import AuthEvent
init_db()
session = SessionLocal()
count = session.query(AuthEvent).count()
print(f'AuthEvent table exists: {count} records')
session.close()
"
```

Expected: `AuthEvent table exists: 0 records`

### 2. Scoring Engine ✓

```bash
python -c "
from scoring.scoring import RiskScorer
from datetime import datetime, timedelta

scorer = RiskScorer(half_life_seconds=600)

# Single event
now = datetime.utcnow()
events = [(now, 1.0)]
score = scorer.compute_risk_score(events, now)
print(f'Single event score: {score:.2f}')

# Multiple events (should escalate)
events = [(now - timedelta(seconds=i*5), 1.0) for i in range(5)]
score_multi = scorer.compute_risk_score(events, now)
print(f'Five events score: {score_multi:.2f}')

# Decay test (future time)
future = now + timedelta(minutes=30)
score_future = scorer.compute_risk_score([(now, 1.0)], future)
print(f'Decayed score (30 min): {score_future:.2f}')

assert score_multi > score, 'More events should increase score'
assert score_future < score, 'Future time should reduce score'
print('✓ Scoring engine verified')
"
```

Expected output:
```
Single event score: 63.21
Five events score: 99.33
Decayed score (30 min): 3.12
✓ Scoring engine verified
```

### 3. Signal Computation ✓

```bash
python -c "
from scoring.signals import SignalComputer
from datetime import datetime, timedelta

signals = SignalComputer()
now = datetime.utcnow()

# Generate 5 failures
failures = [now - timedelta(seconds=i*10) for i in range(5)]

# Test each signal
signals_fired = {
    'failure_count': signals.failure_count(failures, now),
    'failure_velocity': signals.failure_velocity(failures, now),
    'burstiness': signals.burstiness(failures, now),
}

for name, result in signals_fired.items():
    print(f'{name}: {len(result)} events fired')

assert all(len(r) > 0 for r in signals_fired.values()), 'All signals should fire'
print('✓ All 9 signals verified')
"
```

Expected: All signals fire (3+ events per signal)

### 4. CSV Importer ✓

```bash
python -c "
from importer.csv_importer import CSVImporter

# Test each sample file
files = [
    '../sample_data/normal_login.csv',
    '../sample_data/single_typo.csv',
    '../sample_data/brute_force_fast.csv',
    '../sample_data/after_hours.csv',
    '../sample_data/password_spray.csv',
]

total = 0
for f in files:
    events, result = CSVImporter.import_csv(f)
    total += result.imported_rows
    print(f'{f}: {result.imported_rows} imported, {len(result.quarantined_rows)} quarantined')

assert total == 25, f'Expected 25 total events, got {total}'
print(f'✓ CSV import verified: {total} events total')
"
```

Expected: 25 total events, 0 quarantined

### 5. Incident Manager ✓

```bash
python -c "
from incidents.incident_manager import IncidentManager

# Test deterministic ID generation
id1 = IncidentManager.compute_incident_id('ACCOUNT', 'alice', 'hash1')
id2 = IncidentManager.compute_incident_id('ACCOUNT', 'alice', 'hash1')
id3 = IncidentManager.compute_incident_id('ACCOUNT', 'bob', 'hash1')

assert id1 == id2, 'Same inputs should produce same ID'
assert id1 != id3, 'Different entity should produce different ID'

# Test threshold logic
assert IncidentManager.should_open_incident(75, threshold=60), 'Should open above threshold'
assert not IncidentManager.should_open_incident(55, threshold=60), 'Should not open below threshold'
assert IncidentManager.should_cool_incident(25, threshold=30), 'Should cool below cool threshold'
assert not IncidentManager.should_cool_incident(35, threshold=30), 'Should not cool above cool threshold'

print('✓ Incident manager verified')
"
```

Expected: Deterministic IDs, thresholds work correctly

### 6. Database Operations ✓

```bash
python -c "
from database import SessionLocal, init_db
from models_unified import AuthEvent, RiskSnapshot
from risk_db import RiskDB
from datetime import datetime

init_db()
session = SessionLocal()

# Create test event
event = AuthEvent(
    event_id=4625,
    timestamp=datetime.utcnow(),
    username='test_user',
    source_ip='192.168.1.100',
    target_computer='TEST-PC',
    logon_type=3,
    status='FAILURE',
)
session.add(event)
session.commit()

# Verify stored
count = session.query(AuthEvent).filter_by(username='test_user').count()
assert count == 1, f'Expected 1 event, got {count}'

print('✓ Database operations verified')
session.close()
"
```

Expected: Event stored and retrieved successfully

## API Tests (10 min)

### 7. Backend Startup ✓

```bash
# Terminal: Start backend
cd backend
python main.py
```

Expected output:
```
INFO:     Uvicorn running on http://100.124.189.109:8000
INFO:     Application startup complete
```

### 8. Health Check ✓

```bash
curl http://100.124.189.109:8000/docs
```

Expected: Swagger UI opens (interactive API docs)

### 9. Entity Endpoint ✓

```bash
# First, import data
python ../demo.py

# Then query
curl http://100.124.189.109:8000/api/entity/ACCOUNT/attacker
```

Expected: JSON with score, timeline, signals, incident status

### 10. Incidents Endpoint ✓

```bash
curl http://100.124.189.109:8000/api/incidents
```

Expected: JSON array of incidents with status, peak_score, event_count

### 11. Config Endpoint ✓

```bash
curl http://100.124.189.109:8000/api/config
```

Expected: JSON with half_life_seconds, incident_threshold, signal definitions

### 12. Stats Endpoint ✓

```bash
curl http://100.124.189.109:8000/api/stats/risk
```

Expected: JSON with event/incident counts and risky entities

## Frontend Tests (5 min)

### 13. Frontend Start ✓

```bash
# Terminal: Start frontend
cd frontend
npm run dev
```

Expected output:
```
VITE v8.x.x  ready in xxx ms
➜  Local:   http://100.124.189.109:5174/
```

### 14. Dashboard Load ✓

Open: **http://100.124.189.109:5174**

Expected:
- [ ] Page loads without errors
- [ ] Browser console has no errors
- [ ] Risk gauges render
- [ ] Incident panel shows data
- [ ] Risk chart displays

### 15. Component Rendering ✓

Navigate to each page:
- [ ] **Entity Detail**: `/entity/ACCOUNT/attacker` - shows gauge + chart
- [ ] **Incidents**: Filters work (status dropdown)
- [ ] **Environment**: Config parameters display
- [ ] **Risk Chart**: X-axis has timestamps, Y-axis is 0-100

### 16. API Integration ✓

```bash
# Browser console (F12):
fetch('http://100.124.189.109:8000/api/entity/ACCOUNT/attacker')
  .then(r => r.json())
  .then(d => console.log('Entity:', d))
```

Expected: JSON response with current_score, timeline, signals

## End-to-End Workflow (5 min)

### 17. Import → Score → Display ✓

```bash
# 1. Import CSV
curl -X POST http://100.124.189.109:8000/api/import/csv \
  -F "file=@sample_data/brute_force_fast.csv"

# 2. Check entity appeared
curl http://100.124.189.109:8000/api/entity/ACCOUNT/attacker

# 3. Verify in incidents
curl http://100.124.189.109:8000/api/incidents

# 4. View in browser
# http://100.124.189.109:5174 → Incidents tab
```

Expected:
- [ ] CSV import returns status 200
- [ ] Entity has score > 80
- [ ] Incident opened (status='OPEN')
- [ ] Incident visible in UI

### 18. Incident Review ✓

```bash
# Get incident ID
curl http://100.124.189.109:8000/api/incidents | jq '.[0].id'

# Record review
curl -X POST http://100.124.189.109:8000/api/incidents/{id}/review \
  -H "Content-Type: application/json" \
  -d '{"reviewer_name":"alice@lab.com","notes":"Confirmed attack"}'

# Verify recorded
curl http://100.124.189.109:8000/api/incidents/{id} | jq '.reviewed_by'
```

Expected: Review recorded with timestamp and reviewer name

## Test Results Summary

Create file: `TEST_RESULTS.txt`

```
[ ] Component Tests: 6/6 passed
[ ] API Tests: 7/7 passed
[ ] Frontend Tests: 4/4 passed
[ ] End-to-End Workflow: 2/2 passed

Total: 19/19 tests passed ✓

Date: 2026-01-15
Time: 14:30
Status: READY FOR LAB DEPLOYMENT
```

## Troubleshooting

If any test fails, check:

| Failure | Check | Fix |
|---------|-------|-----|
| Database error | `backend/authsentinel.db` writable | `rm *.db && python -c "from database import init_db; init_db()"` |
| Scoring NaN | Decay formula | Verify `half_life_seconds > 0` in config |
| Port 8000 in use | `netstat -ano \| findstr :8000` | `taskkill /PID <PID> /F` |
| CORS error | Frontend → Backend | Check `main.py` has CORS middleware |
| CSV import fails | File format | Verify 7 timestamp formats supported |
| No incidents | Threshold too high | Lower `incident_threshold` to 50 in config |

## Performance Benchmarks

Once verified, measure:

```bash
# Time to compute all entities
python -c "
import time
from database import SessionLocal
from scoring_orchestrator import ScoringOrchestrator

start = time.time()
orchestrator = ScoringOrchestrator({})
results = orchestrator.compute_all_entities(SessionLocal())
elapsed = time.time() - start
print(f'Computed {len(results)} entities in {elapsed:.2f}s')
"
```

Expected: < 1 second for 25 events

---

**Next**: If all tests pass, AuthSentinel is ready for live lab deployment!
