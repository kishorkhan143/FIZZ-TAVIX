# AuthSentinel Quick Start (5 minutes)

Get AuthSentinel running in 5 minutes. For detailed setup, see `docs/SETUP.md`.

## Step 1: Initialize (1 min)

```bash
cd log

# Create virtual environment (if not done)
python -m venv venv_authsentinel
venv_authsentinel\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Initialize database
python -c "from backend.database import init_db; init_db()"
```

## Step 2: Run Demo (1 min)

```bash
# Import sample data + compute scores
python demo.py
```

Expected output:
- ✓ 5 CSV files imported (25 total events)
- ✓ All entities scored (10-15 entities)
- ✓ Incidents opened for high-risk patterns
- ✓ Signal breakdown shown

## Step 3: Start Backend (1 min)

```bash
# Terminal 1: Backend API
cd backend
python main.py
# Listening on http://100.124.189.109:8000
```

## Step 4: Start Frontend (1 min)

```bash
# Terminal 2: Frontend Dashboard
cd frontend
npm install  # (if not done)
npm run dev
# Running on http://100.124.189.109:5174
```

## Step 5: Open Dashboard (1 min)

Open browser: **http://100.124.189.109:5174**

You should see:
- **Entity List**: All accounts/computers with risk gauges
- **Incidents Panel**: OPEN/COOLED incidents
- **Risk Chart**: Timeline of scores
- **Configuration**: Tune half-life, thresholds

---

## What You're Looking At

### Risk Bands

| Band | Color | Score | Meaning |
|------|-------|-------|---------|
| NORMAL | 🟢 Green | 0-29 | Baseline activity |
| WATCH | 🟡 Yellow | 30-59 | Monitor closely |
| SUSPICIOUS | 🟠 Orange | 60-79 | Incident opened |
| HIGH_RISK | 🔴 Red | 80-100 | Critical pattern |

### Sample Data Scenarios

1. **normal_login.csv**: Single user login (NORMAL, score ~5)
2. **single_typo.csv**: One failed password, then success (WATCH, score ~20)
3. **brute_force_fast.csv**: 5 failures then success (HIGH_RISK, score ~85)
4. **after_hours.csv**: Success outside 08:00-18:00 (SUSPICIOUS, score ~65)
5. **password_spray.csv**: Many accounts from one IP (HIGH_RISK, score ~78)

---

## Try It

### Query Risk via CLI

```bash
# Get entity risk
curl http://100.124.189.109:8000/api/entity/ACCOUNT/attacker

# List incidents
curl http://100.124.189.109:8000/api/incidents

# Get stats
curl http://100.124.189.109:8000/api/stats/risk
```

### Import Your Own CSV

```bash
curl -X POST http://100.124.189.109:8000/api/import/csv \
  -F "file=@myevents.csv"
```

CSV format:
```
username,computer,source_ip,timestamp,event_type,logon_type
alice,PC-LAB-01,192.168.1.1,2024-01-15 10:30:45,SUCCESS,3
bob,PC-LAB-02,192.168.1.2,2024-01-15 10:35:20,FAILURE,3
```

---

## Run Tests

```bash
cd log
python -m pytest tests/ -v
```

All 18 tests should pass:
- test_scoring.py: 9 tests (decay, formula, order-independence)
- test_calibration.py: 4 tests (risk bands)
- test_csv.py: 4 tests (import, timestamps)
- test_order.py: 1 test (order independence)

---

## Next Steps

1. **Connect Live Events**: Run collector on Laptop A (see `collector/README.md`)
2. **Calibrate**: Adjust `backend/risk_config.yaml` for your lab
3. **Review Incidents**: Mark as reviewed in UI
4. **Export Reports**: Use API to export incident details

---

## Troubleshooting

### Port Already in Use
```bash
# Kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Database Error
```bash
# Reset database
rm backend/authsentinel.db
python -c "from backend.database import init_db; init_db()"
```

### Frontend Won't Connect
```bash
# Check backend URL in frontend/src/useAuthSentinel.js
# Should be: http://100.124.189.109:8000
```

---

## Architecture

```
Events → Scoring Engine → Risk Score (0-100)
  ↓           ↓                ↓
CSV      9 Signals        Incident
Import   Decay Formula    Lifecycle
  ↓           ↓                ↓
Database  API Endpoint    Dashboard
         REST + WebSocket
```

---

For more details, see:
- **Setup**: `docs/SETUP.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Risk Model**: `docs/RISK_MODEL.md`
- **Full README**: `README_AUTHSENTINEL.md`
