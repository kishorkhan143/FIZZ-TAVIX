"""
AuthSentinel — Pydantic Schemas (API request / response shapes)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_serializer


def _utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


# ── Inbound from Collector ────────────────────────────────────────────────────

class EventIngestionRequest(BaseModel):
    """
    Posted by the Windows Event Collector.
    NEVER includes passwords — only security-event metadata.
    """
    event_id: int
    timestamp: datetime
    username: Optional[str] = None
    source_ip: Optional[str] = None
    laptop_ip: Optional[str] = None          # Collected LAN IP from Laptop A
    source_host: Optional[str] = None
    target_computer: Optional[str] = None
    logon_type: Optional[int] = None
    logon_type_description: Optional[str] = None
    status: str                              # "SUCCESS" | "FAILURE"
    raw_record_id: Optional[int] = None


class AlertActionRequest(BaseModel):
    action: str                              # "shutdown" | "lock_screen" | "authorize"
    note: Optional[str] = None
    terminal_id: Optional[str] = None


class CommandAckRequest(BaseModel):
    status: Literal["EXECUTED", "FAILED"] = "EXECUTED"
    message: Optional[str] = None


class RemoteCommandResponse(BaseModel):
    id: int
    terminal_id: str
    command: str
    alert_id: Optional[int] = None
    status: str
    payload: Optional[str] = None
    result_message: Optional[str] = None
    created_at: datetime
    executed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return _utc_timestamp(value)

    @field_serializer("executed_at")
    def serialize_executed_at(self, value: Optional[datetime]) -> Optional[str]:
        return _utc_timestamp(value) if value else None



# ── Outbound to Dashboard ─────────────────────────────────────────────────────

class EventResponse(BaseModel):
    id: int
    event_id: int
    timestamp: datetime
    username: Optional[str] = None
    source_ip: Optional[str] = None
    source_host: Optional[str] = None
    target_computer: Optional[str] = None
    logon_type: Optional[int] = None
    logon_type_description: Optional[str] = None
    status: str
    risk_score: float
    risk_level: str
    detection_reason: Optional[str] = None
    raw_record_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("timestamp", "created_at")
    def serialize_timestamps(self, value: datetime) -> str:
        return _utc_timestamp(value)


class AlertResponse(BaseModel):
    id: int
    alert_type: str
    username: Optional[str] = None
    source_ip: Optional[str] = None
    source_host: Optional[str] = None
    target_computer: Optional[str] = None
    risk_score: float
    risk_level: str
    failure_count: int
    time_window_seconds: int
    reason: Optional[str] = None
    status: Optional[str] = "OPEN"
    resolved: bool
    triggered_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("triggered_at", "created_at")
    def serialize_timestamps(self, value: datetime) -> str:
        return _utc_timestamp(value)


class StatsResponse(BaseModel):
    total_events: int
    successful_logins: int
    failed_logins: int
    active_alerts: int
    critical_alerts: Optional[int] = 0
    high_alerts: Optional[int] = 0
    active_incidents: Optional[int] = 0
    resolved_incidents: Optional[int] = 0


class CollectorStatusRequest(BaseModel):
    status: str          # "CONNECTED" | "DISCONNECTED" | "ONLINE" | "OFFLINE"
    hostname: str
    ip: Optional[str] = None
    terminal_id: Optional[str] = None
    computer_name: Optional[str] = None
    mac_address: Optional[str] = None
    os_name: Optional[str] = None
    os_version: Optional[str] = None
    logged_in_user: Optional[str] = None
    cpu: Optional[str] = None
    ram: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    backend: str
    database: str
    smtp_configured: bool = False
    websocket_connections: int
    collector_status: str
    collector_count: int = 0
    collector_hostname: Optional[str] = None
    collector_ip: Optional[str] = None
    uptime_seconds: float


class LabCreateRequest(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    location: Optional[str] = None


class LabHoursRequest(BaseModel):
    start_time: str
    end_time: str


class LabHoursResponse(BaseModel):
    start_time: str
    end_time: str
    is_open: bool
    status: str


class LabResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[datetime] = None
    terminals_count: Optional[int] = 0

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def serialize_created_at(self, value: Optional[datetime]) -> Optional[str]:
        return _utc_timestamp(value) if value else None


class TerminalAssignRequest(BaseModel):
    terminal_id: str
    lab_id: Optional[str] = None


class TerminalResponse(BaseModel):
    terminal_id: str
    account: Optional[str] = "—"
    source_ip: Optional[str] = "—"
    last_login: Optional[str] = "—"
    last_login_raw: Optional[datetime] = None
    status: Optional[str] = "UNKNOWN"
    lab_id: Optional[str] = None
    lab_name: Optional[str] = None


class LastAuthEventSummary(BaseModel):
    event_id: int
    status: str
    timestamp: datetime
    username: Optional[str] = None
    logon_type_description: Optional[str] = None
    source_ip: Optional[str] = None
    risk_level: Optional[str] = "LOW"

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return _utc_timestamp(value)


class ComputerSummary(BaseModel):
    terminal_id: str
    computer_name: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    os_name: Optional[str] = None
    os_version: Optional[str] = None
    logged_in_user: Optional[str] = None
    cpu: Optional[str] = None
    ram: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    status: str  # "Online" | "Offline" | "Unknown"
    last_seen: Optional[datetime] = None
    last_seen_formatted: Optional[str] = None
    last_auth_event: Optional[LastAuthEventSummary] = None
    incidents_count: int = 0
    lab_id: Optional[str] = None
    lab_name: Optional[str] = None

    @field_serializer("last_seen")
    def serialize_last_seen(self, value: Optional[datetime]) -> Optional[str]:
        return _utc_timestamp(value) if value else None


class LabComputersResponse(BaseModel):
    lab_id: str
    lab_name: str
    description: Optional[str] = None
    location: Optional[str] = None
    total_computers: int
    online_count: int
    offline_count: int
    unknown_count: int
    computers: list[ComputerSummary]


class ComputerDetailResponse(BaseModel):
    computer: ComputerSummary
    lab: Optional[LabResponse] = None
    auth_events: list[EventResponse] = []
    incidents: list[AlertResponse] = []



# ── Authentication Schemas ───────────────────────────────────────────────────

class VerificationRequestRequest(BaseModel):
    """Request to send verification email."""
    email: str


class VerificationRequestResponse(BaseModel):
    """Response after verification email is sent."""
    success: bool
    message: str


class VerifyEmailResponse(BaseModel):
    """Response after email is verified and JWT issued."""
    success: bool
    message: str
    jwt_token: str
    user: Optional[dict] = None


class UserResponse(BaseModel):
    """Current authenticated user info."""
    id: int
    email: str
    name: Optional[str] = None
    role: str = "admin"
    is_verified: bool
    created_at: datetime
    verified_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("created_at", "verified_at", "last_login_at")
    def serialize_timestamps(self, value: Optional[datetime]) -> Optional[str]:
        return _utc_timestamp(value) if value else None


class UpdateProfileRequest(BaseModel):
    """Request to update user profile."""
    name: str


class AdminLoginRequest(BaseModel):
    """Admin quick login request."""
    email: str
    passcode: Optional[str] = None


class TestAlertEmailRequest(BaseModel):
    """Request to trigger test incident alert email."""
    recipient_email: Optional[str] = None


class AdminInfoResponse(BaseModel):
    """Current admin and SMTP notification configuration."""
    admin_email: str
    smtp_host: str
    smtp_user: str
    smtp_enabled: bool
    recipient_emails: list[str]
    total_users: int
