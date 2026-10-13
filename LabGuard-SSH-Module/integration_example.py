"""LabGuard Integration Example.

This script demonstrates how an existing LabGuard application can mount and
utilize the standalone LabGuard SSH Security Module.

Methods demonstrated:
1. Mounting the FastAPI APIRouter into an existing LabGuard FastAPI instance.
2. Direct Python programmatic API usage without HTTP overhead.
"""

import os
from fastapi import FastAPI
from uvicorn import run

# 1. Import router and module utilities from labguard_ssh
from labguard_ssh import (
    get_ssh_router,
    SSHDetector,
    PolicyEngine,
    SSHModuleSettings,
    PolicyMode,
)

# -------------------------------------------------------------------------
# Integration Method 1: Mount into existing LabGuard FastAPI application
# -------------------------------------------------------------------------

def create_labguard_app_with_ssh() -> FastAPI:
    """Simulates the main LabGuard backend application incorporating SSH security."""

    # Existing LabGuard application
    app = FastAPI(
        title="LabGuard Core Platform",
        description="Main LabGuard system with integrated SSH security monitoring.",
        version="2.0.0",
    )

    # Core LabGuard endpoint
    @app.get("/api/system/summary", tags=["Core LabGuard"])
    def get_system_summary():
        return {
            "status": "operational",
            "module_count": 4,
            "managed_hosts": 12,
        }

    # Register the LabGuard SSH module router
    # All endpoints are mounted cleanly under /api/ssh/*
    # e.g.:
    #   GET  /api/ssh/status
    #   GET  /api/ssh/policy
    #   POST /api/ssh/policy
    #   POST /api/ssh/actions/disable
    #   POST /api/ssh/actions/allowlist
    #   GET  /api/ssh/audit
    app.include_router(get_ssh_router())

    return app


# -------------------------------------------------------------------------
# Integration Method 2: Direct Python API (for worker daemons / scripts)
# -------------------------------------------------------------------------

def run_direct_python_detection_example():
    """Example of using the SSH module directly in background tasks or scripts."""
    print("--- LabGuard Direct Python Detection Demo ---")

    detector = SSHDetector()
    report = detector.get_full_report()

    print(f"OpenSSH Installed: {report.package_installed} ({report.package_version or 'N/A'})")
    print(f"Service Unit:     {report.service_name} (State: {report.service_state.value}, Enabled: {report.service_enabled})")
    print(f"Listening Ports:  {[p.model_dump() for p in report.listening_ports]}")
    print(f"Config Settings:  PermitRootLogin={report.config.permit_root_login}, PasswordAuth={report.config.password_authentication}")
    print(f"Timestamp:        {report.timestamp}")


if __name__ == "__main__":
    import sys

    if "--direct" in sys.argv:
        run_direct_python_detection_example()
    else:
        print("Starting LabGuard mock server with SSH module at http://127.0.0.1:8000 ...")
        print("API Documentation available at: http://127.0.0.1:8000/docs")
        labguard_app = create_labguard_app_with_ssh()
        run(labguard_app, host="127.0.0.1", port=8000)
