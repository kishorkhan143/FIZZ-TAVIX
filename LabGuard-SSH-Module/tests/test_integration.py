"""Verification test for integrating LabGuard SSH router into an existing FastAPI app."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from labguard_ssh import get_ssh_router


def test_mount_into_existing_fastapi_app():
    """Verify that get_ssh_router() integrates seamlessly with an existing FastAPI app."""
    # Simulate existing LabGuard app
    existing_app = FastAPI(title="Existing LabGuard Backend", version="1.0.0")

    # Existing LabGuard routes
    @existing_app.get("/api/v1/status")
    def existing_status():
        return {"app": "LabGuard", "status": "running"}

    # Mount the LabGuard SSH module router
    ssh_router = get_ssh_router()
    existing_app.include_router(ssh_router)

    client = TestClient(existing_app)

    # 1. Verify original LabGuard route still works
    res_orig = client.get("/api/v1/status")
    assert res_orig.status_code == 200
    assert res_orig.json() == {"app": "LabGuard", "status": "running"}

    # 2. Verify integrated SSH status endpoint is accessible
    res_ssh = client.get("/api/ssh/status")
    assert res_ssh.status_code == 200
    ssh_data = res_ssh.json()
    assert "package_installed" in ssh_data
    assert "service_active" in ssh_data
    assert "listening_ports" in ssh_data
    assert "config" in ssh_data

    # 3. Verify integrated SSH policy endpoint is accessible
    res_policy = client.get("/api/ssh/policy")
    assert res_policy.status_code == 200
    policy_data = res_policy.json()
    assert policy_data["configured_policy"] == "MONITOR_ONLY"
