"""FastAPI API Router and Application for LabGuard SSH Security Module.

Provides modular endpoints that can be mounted into LabGuard or run standalone.
"""

from __future__ import annotations

import logging
import secrets
from typing import List, Optional
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from labguard_ssh.audit import get_audit_logger
from labguard_ssh.config import SSHModuleSettings, get_settings
from labguard_ssh.models import (
    ActionResponse,
    AllowlistApplyRequest,
    AllowlistPlan,
    AuditLogEntry,
    DisableSSHRequest,
    PolicyStatusResponse,
    PolicyUpdateRequest,
    SSHStatusReport,
)
from labguard_ssh.policy_engine import PolicyEngine
from labguard_ssh.remote_collector import RemoteCollectorError, RemoteSSHCollector
from labguard_ssh.service_controller import ControllerSecurityError

logger = logging.getLogger("labguard_ssh.api")


class AdminAuthDependency:
    """Dependency that verifies administrative credentials when configured."""

    def __init__(self, settings: Optional[SSHModuleSettings] = None):
        self.settings = settings or get_settings()

    def __call__(
        self,
        x_labguard_admin_key: Optional[str] = Header(None, alias="X-LabGuard-Admin-Key"),
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ) -> str:
        expected_key = self.settings.admin_key

        # If an admin key is configured, enforce strict match
        if expected_key:
            token = None
            if x_labguard_admin_key:
                token = x_labguard_admin_key
            elif authorization:
                parts = authorization.split(None, 1)
                if len(parts) == 2 and parts[0].lower() == "bearer":
                    token = parts[1].strip()

            if not token or not secrets.compare_digest(token, expected_key):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or missing LabGuard administrative credentials.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return "admin_authenticated"

        # If no admin key is configured in settings
        return "unauthenticated_local_admin"


def get_client_ip(request: Request) -> str:
    """Extract client IP safely from request."""
    if request.client:
        return request.client.host
    return "127.0.0.1"


def get_ssh_router(
    engine: Optional[PolicyEngine] = None,
    settings: Optional[SSHModuleSettings] = None,
) -> APIRouter:
    """Create and configure the FastAPI APIRouter for LabGuard SSH module.

    Can be included directly in any existing FastAPI application:
        app.include_router(get_ssh_router())
    """
    router = APIRouter(prefix="/api/ssh", tags=["SSH Security"])
    active_settings = settings or get_settings()
    active_engine = engine or PolicyEngine(settings=active_settings)
    verify_admin = AdminAuthDependency(settings=active_settings)

    @router.get(
        "/status",
        response_model=SSHStatusReport,
        summary="Get SSH Status",
        description=(
            "Inspects OpenSSH installation, service state, listening ports, and configuration. "
            "Pass ?target=windows to collect status remotely from Windows PC over Tailscale."
        ),
    )
    def get_status(target: Optional[str] = None) -> SSHStatusReport:
        # Route to remote Windows collector if target=windows or target=remote is requested
        if target and target.lower() in ("windows", "remote"):
            collector = RemoteSSHCollector(settings=active_settings)
            try:
                return collector.collect_status()
            except RemoteCollectorError as err:
                err_msg = str(err)
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                if "not configured" in err_msg.lower():
                    status_code = status.HTTP_400_BAD_REQUEST
                elif "authentication failed" in err_msg.lower():
                    status_code = status.HTTP_502_BAD_GATEWAY
                raise HTTPException(status_code=status_code, detail=err_msg)

        try:
            return active_engine.get_ssh_status()
        except Exception as e:
            logger.error("Failed to collect SSH status: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error inspecting SSH status: {e}",
            )

    @router.get(
        "/policy",
        response_model=PolicyStatusResponse,
        summary="Get Configured Policy",
        description="Returns the currently active SSH security policy and safety locks.",
    )
    def get_policy() -> PolicyStatusResponse:
        return active_engine.get_policy_status()

    @router.post(
        "/policy",
        response_model=PolicyStatusResponse,
        summary="Update Security Policy",
        description="Accepts a validated policy selection. Does NOT trigger automatic destructive system changes.",
    )
    def update_policy(
        request: PolicyUpdateRequest,
        raw_request: Request,
        _auth: str = Depends(verify_admin),
    ) -> PolicyStatusResponse:
        client_ip = get_client_ip(raw_request)
        try:
            return active_engine.set_policy(request, operator=_auth, client_ip=client_ip)
        except Exception as e:
            logger.error("Error setting policy: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @router.post(
        "/actions/disable",
        response_model=ActionResponse,
        summary="Disable SSH Service",
        description=(
            "Requests an SSH shutdown operation. Requires explicit confirmation, "
            "administrator privileges, and lockout risk acknowledgment."
        ),
    )
    def disable_ssh(
        request: DisableSSHRequest,
        raw_request: Request,
        _auth: str = Depends(verify_admin),
    ) -> ActionResponse:
        client_ip = get_client_ip(raw_request)

        # Validate confirmation parameters
        if not request.confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Explicit confirmation ('confirm=true') is required.",
            )

        if not request.acknowledged_lockout_risk:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lockout risk must be acknowledged ('acknowledged_lockout_risk=true').",
            )

        try:
            response = active_engine.disable_ssh(request, operator=_auth, client_ip=client_ip)
            return response
        except ControllerSecurityError as err:
            err_msg = str(err)
            status_code = status.HTTP_403_FORBIDDEN
            if "MONITOR_ONLY" in err_msg:
                status_code = status.HTTP_409_CONFLICT
            raise HTTPException(status_code=status_code, detail=err_msg)
        except Exception as e:
            logger.error("Unhandled error during SSH disable action: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal error executing SSH disable: {e}",
            )

    @router.post(
        "/actions/allowlist",
        response_model=ActionResponse,
        summary="Apply or Dry-Run Network Allowlist",
        description=(
            "Plans or applies firewall allowlist rules for SSH. "
            "Preserves existing rules and requires alternative recovery verification."
        ),
    )
    def apply_allowlist(
        request: AllowlistApplyRequest,
        raw_request: Request,
        _auth: str = Depends(verify_admin),
    ) -> ActionResponse:
        client_ip = get_client_ip(raw_request)
        try:
            return active_engine.apply_allowlist(request, operator=_auth, client_ip=client_ip)
        except ControllerSecurityError as err:
            status_code = status.HTTP_409_CONFLICT if "MONITOR_ONLY" in str(err) else status.HTTP_403_FORBIDDEN
            raise HTTPException(status_code=status_code, detail=str(err))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal error processing allowlist: {e}",
            )

    @router.get(
        "/audit",
        response_model=List[AuditLogEntry],
        summary="Retrieve Audit Log",
        description="Returns recent structured audit events with sensitive secrets automatically redacted.",
    )
    def get_audit_events(
        limit: int = 50,
        _auth: str = Depends(verify_admin),
    ) -> List[AuditLogEntry]:
        return active_engine.audit.get_recent(limit=min(limit, 200))

    return router


def create_app(
    settings: Optional[SSHModuleSettings] = None,
    engine: Optional[PolicyEngine] = None,
) -> FastAPI:
    """Create a standalone FastAPI application for LabGuard SSH Module."""
    cfg = settings or get_settings()
    app = FastAPI(
        title="LabGuard SSH Monitoring & Access Control Module",
        description="Standalone backend module for monitoring and managing OpenSSH access in lab environments.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    ssh_router = get_ssh_router(engine=engine, settings=cfg)
    app.include_router(ssh_router)

    @app.get("/health", tags=["System"])
    def health_check():
        return {"status": "ok", "module": "labguard_ssh", "policy": cfg.ssh_policy.value}

    return app


# Default ASGI application instance
app = create_app()
