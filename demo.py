#!/usr/bin/env python3
"""
AuthSentinel Demo Script

Demonstrates the complete risk-based brute-force detection system:
1. Import sample CSV data
2. Compute risk scores for all entities
3. Display results with incident lifecycle
4. Show signal breakdown

Run: python demo.py
"""

import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy.orm import Session
from models_unified import Base
from database import engine, SessionLocal, init_db
from importer.csv_importer import CSVImporter
from scoring_orchestrator import ScoringOrchestrator
from risk_db import RiskDB


def print_banner(text):
    """Print a formatted banner."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_entity_result(entity_type, entity_id, score, details):
    """Print entity risk result."""
    band = details.get('band', 'UNKNOWN')
    signals = details.get('signals', [])
    incident = details.get('incident_action')
    
    # Color by band
    color_map = {
        'NORMAL': '\033[92m',      # Green
        'WATCH': '\033[93m',       # Yellow
        'SUSPICIOUS': '\033[91m',  # Red
        'HIGH_RISK': '\033[91m'    # Red
    }
    reset = '\033[0m'
    
    color = color_map.get(band, '')
    
    print(f"{color}[{band}]{reset} {entity_type}:{entity_id}")
    print(f"  Score: {score}/100")
    print(f"  Signals: {', '.join(signals) if signals else '(none)'}")
    
    if incident:
        action = incident.get('action', 'unknown')
        status = incident.get('status', 'unknown')
        print(f"  ⚠️  Incident {action.upper()}: {incident['incident_id']} ({status})")
    
    print()


def main():
    """Run the demo."""
    print_banner("AuthSentinel Risk-Based Brute-Force Detection — Demo")
    
    # Initialize database
    print("→ Initializing database...")
    init_db()
    print("  ✓ Database ready\n")
    
    session = SessionLocal()
    
    try:
        # ====== PHASE 1: Import Sample Data ======
        print_banner("Phase 1: Import Sample CSV Data")
        
        sample_files = [
            ('sample_data/normal_login.csv', 'Normal logins'),
            ('sample_data/single_typo.csv', 'Single password typo'),
            ('sample_data/brute_force_fast.csv', 'Rapid brute-force attack'),
            ('sample_data/after_hours.csv', 'After-hours access'),
            ('sample_data/password_spray.csv', 'Password spray attack'),
        ]
        
        total_imported = 0
        total_quarantined = 0
        
        for filepath, description in sample_files:
            if not Path(filepath).exists():
                print(f"⚠️  {filepath} not found, skipping")
                continue
            
            print(f"→ Importing {description}...")
            print(f"  File: {filepath}")
            
            events, result = CSVImporter.import_csv(filepath)
            
            # Store events in database
            from models_unified import AuthEvent
            for event_dict in events:
                event = AuthEvent(
                    event_id=event_dict.get('event_id'),
                    timestamp=event_dict.get('timestamp'),
                    username=event_dict.get('username'),
                    source_ip=event_dict.get('source_ip'),
                    target_computer=event_dict.get('target_computer'),
                    logon_type=event_dict.get('logon_type'),
                    status=event_dict.get('status'),
                    event_hash=event_dict.get('event_hash'),
                )
                session.add(event)
            
            session.commit()
            
            total_imported += result.imported_rows
            total_quarantined += len(result.quarantined_rows)
            
            print(f"  ✓ Imported: {result.imported_rows}")
            if result.merged_duplicates > 0:
                print(f"  ℹ Duplicates: {result.merged_duplicates}")
            if result.quarantined_rows:
                print(f"  ⚠ Quarantined: {len(result.quarantined_rows)}")
                for qr in result.quarantined_rows[:2]:  # Show first 2
                    print(f"    - Row {qr['row_number']}: {qr['reason']}")
        
        print(f"\n✓ Total imported: {total_imported}")
        if total_quarantined > 0:
            print(f"⚠ Total quarantined: {total_quarantined}")
        
        # ====== PHASE 2: Compute Risk Scores ======
        print_banner("Phase 2: Compute Risk Scores")
        
        print("→ Initializing scoring engine...")
        config = {
            'half_life_seconds': 600,
            'lookback_seconds': 3600,
            'incident_threshold': 60,
            'cool_threshold': 30,
        }
        orchestrator = ScoringOrchestrator(config)
        print("  ✓ Scoring engine ready\n")
        
        print("→ Computing all entity risks...")
        results = orchestrator.compute_all_entities(session)
        
        print(f"  ✓ Computed {len(results)} entities\n")
        
        # ====== PHASE 3: Display Results ======
        print_banner("Phase 3: Risk Score Results")
        
        # Sort by score descending
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1][0],
            reverse=True
        )
        
        print("Top entities by risk score:\n")
        
        # Show top 15
        for (entity_type, entity_id), (score, details) in sorted_results[:15]:
            print_entity_result(entity_type, entity_id, score, details)
        
        # ====== PHASE 4: Incident Summary ======
        print_banner("Phase 4: Incident Summary")
        
        summary = orchestrator.get_summary(session)
        
        print("Event Statistics:")
        for status, count in summary.get('events', {}).items():
            print(f"  {status}: {count}")
        
        print("\nIncident Statistics:")
        for status, count in summary.get('incidents', {}).items():
            print(f"  {status}: {count}")
        
        print("\nTop Risky Entities (by current score):")
        for entity in summary.get('risky_entities', [])[:5]:
            entity_type = entity.get('entity_type', '?')
            entity_id = entity.get('entity_id', '?')
            score = entity.get('score', 0)
            print(f"  {entity_type}:{entity_id} = {score}")
        
        # ====== PHASE 5: Signal Breakdown ======
        print_banner("Phase 5: Signal Breakdown Example")
        
        # Find an entity with high score and incidents
        from models_unified import Incident
        from sqlalchemy import select
        
        stmt = select(Incident).where(
            Incident.status == 'OPEN'
        ).order_by(Incident.peak_risk_score.desc()).limit(1)
        
        incident = session.execute(stmt).scalar_one_or_none()
        
        if incident:
            print(f"Example Incident: {incident.entity_type}:{incident.entity_id}")
            print(f"  ID: {incident.id}")
            print(f"  Status: {incident.status}")
            print(f"  Peak Score: {incident.peak_risk_score}")
            print(f"  Current Score: {incident.current_risk_score}")
            print(f"  Events: {incident.event_count}")
            
            if incident.signal_names:
                print(f"  Signals: {incident.signal_names}")
        else:
            print("(No open incidents in sample data)")
        
        # ====== PHASE 6: Configuration ======
        print_banner("Phase 6: Configuration")
        
        print("Risk Configuration:")
        print(f"  Half-life decay: {config['half_life_seconds']}s")
        print(f"  Lookback window: {config['lookback_seconds']}s")
        print(f"  Incident threshold: {config['incident_threshold']}")
        print(f"  Cool threshold: {config['cool_threshold']}")
        
        print("\nRisk Bands:")
        print("  NORMAL (0-29): Green 🟢")
        print("  WATCH (30-59): Yellow 🟡")
        print("  SUSPICIOUS (60-79): Orange 🟠")
        print("  HIGH_RISK (80-100): Red 🔴")
        
        # ====== Final Summary ======
        print_banner("Demo Complete!")
        
        print("✓ AuthSentinel is ready for use:")
        print("\n1. Backend API:")
        print("   Start: python backend/main.py")
        print("   URL: http://100.124.189.109:8000")
        print("\n2. Frontend Dashboard:")
        print("   Start: npm run dev (in frontend/)")
        print("   URL: http://100.124.189.109:5174")
        print("\n3. Key Endpoints:")
        print("   GET  /api/entity/ACCOUNT/alice         # Entity risk detail")
        print("   GET  /api/incidents                     # List incidents")
        print("   POST /api/import/csv                    # Import CSV")
        print("   GET  /api/stats/risk                    # Risk statistics")
        print("\n4. Next Steps:")
        print("   - Connect Windows event collector (Laptop A)")
        print("   - Monitor risk scores in real-time")
        print("   - Review incidents as they appear")
        print("   - Calibrate thresholds for your lab")
        print()
    
    finally:
        session.close()


if __name__ == '__main__':
    main()
