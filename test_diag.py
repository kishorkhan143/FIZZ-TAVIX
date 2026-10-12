#!/usr/bin/env python3
"""Quick diagnostic to check scoring"""

import sys
import os
sys.path.insert(0, 'backend')

from datetime import datetime, timezone
from database import SessionLocal, init_db
from models_unified import AuthEvent
from scoring.scoring import RiskScorer
from scoring.signals import SignalComputer

# Init
init_db()
session = SessionLocal()

# Check events
events = session.query(AuthEvent).all()
print("Total events in DB:", len(events))

if events:
    print("\nFirst event:", events[0])
    print("  username:", events[0].username)
    print("  status:", events[0].status)
    print("  timestamp:", events[0].timestamp)
    print("  timestamp type:", type(events[0].timestamp))
    
    # Get failures for 'attacker'
    failures_list = [e.timestamp for e in events if e.username == 'attacker' and e.status == 'FAILURE']
    print("\nFailures for 'attacker':", len(failures_list))
    for ts in failures_list[:3]:
        print(" ", ts)
    
    # Test signal computation
    if failures_list:
        now = max(ts for ts in [e.timestamp for e in events])
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        
        print("\nReference time:", now)
        
        computer = SignalComputer()
        config = {'lookback_seconds': 3600}
        
        fc_result = computer.failure_count(failures_list, now, lookback_seconds=86400*30)
        print("failure_count result:", len(fc_result), "events fired")
        for ts, coeff in fc_result[:3]:
            print(f"  {ts}: coeff={coeff}")
        
        # Try scoring
        scorer = RiskScorer(half_life_seconds=600)
        
        # Debug: check decay at 12 hours
        twelve_hours = 12 * 3600
        decay_val = scorer.decay_function(twelve_hours)
        print(f"Decay at 12 hours: {decay_val:.6f}")
        
        accumulated = scorer.compute_accumulated_score(fc_result, now)
        print(f"Accumulated X: {accumulated:.4f}")
        
        score = scorer.compute_risk_score(fc_result, now)
        print(f"\nScore from failure_count: {score:.2f}")

session.close()
