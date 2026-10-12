"""
AuthSentinel Backend - Simplified Event Logger
Accepts events from collectors and logs them
"""
import logging
import json
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="AuthSentinel", description="Risk-based detection system", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory event store
events_log = []
COLLECTOR_SECRET = "authsentinel-lab-secret-2026"

@app.get("/api/health")
async def health():
    return {
        "status": "OK",
        "backend": "ONLINE",
        "database": "MEMORY",
        "events_logged": len(events_log),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/events")
async def ingest_event(
    event: dict,
    x_collector_secret: str = Header(None),
    x_source_label: str = Header(None),
):
    if x_collector_secret != COLLECTOR_SECRET:
        raise HTTPException(status_code=403, detail="Invalid collector secret")
    
    # Log the event
    event["source_label"] = x_source_label or "UNKNOWN"
    event["received_at"] = datetime.now(timezone.utc).isoformat()
    events_log.append(event)
    
    logger.info(f"[EVENT] {event.get('username')} - {event.get('status')} from {x_source_label}")
    
    return {
        "id": len(events_log),
        "status": "accepted",
        **event
    }

@app.get("/api/events")
async def list_events(limit: int = 50):
    return events_log[-limit:]

@app.get("/api/stats")
async def get_stats():
    success = sum(1 for e in events_log if e.get("status") == "SUCCESS")
    failure = sum(1 for e in events_log if e.get("status") == "FAILURE")
    return {
        "total_events": len(events_log),
        "successful_logins": success,
        "failed_logins": failure,
        "active_alerts": 0
    }

@app.post("/api/collector/status")
async def collector_status(
    status_data: dict,
    x_collector_secret: str = Header(None),
):
    if x_collector_secret != COLLECTOR_SECRET:
        raise HTTPException(status_code=403, detail="Invalid collector secret")
    
    logger.info(f"[COLLECTOR] {status_data.get('hostname')} - {status_data.get('status')}")
    return {"ok": True}

@app.delete("/api/reset")
async def reset():
    global events_log
    events_log.clear()
    logger.info("[RESET] All events cleared")
    return {"ok": True, "message": "All data cleared"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
