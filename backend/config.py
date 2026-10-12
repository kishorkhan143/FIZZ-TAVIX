"""
AuthSentinel — Central Configuration
=====================================
All runtime settings. Override via environment variables or a .env file.
"""

import os

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_sqlite_database_url(value: str) -> str:
    scheme, separator, database_path = value.partition(":///")
    if not separator or scheme not in {"sqlite", "sqlite+aiosqlite"}:
        return value

    path, query_separator, query = database_path.partition("?")
    if path == ":memory:" or os.path.isabs(path):
        return value

    absolute_path = os.path.abspath(os.path.join(BASE_DIR, path)).replace("\\", "/")
    resolved = f"{scheme}:///{absolute_path}"
    if query_separator:
        resolved += f"?{query}"
    return resolved


class Settings(BaseSettings):
    # ── Server ──────────────────────────────────────────────────────────────
    host: str = Field("0.0.0.0", description="Bind address (0.0.0.0 = LAN accessible)")
    port: int = Field(8000, description="FastAPI port")

    # ── Database ────────────────────────────────────────────────────────────
    database_url: str = Field(
        f"sqlite+aiosqlite:///{os.path.join(BASE_DIR, 'authsentinel.db').replace(os.sep, '/')}",
        description="Async SQLAlchemy database URL",
    )

    # ── Detection Engine ────────────────────────────────────────────────────
    brute_force_threshold: int = Field(
        5, description="Failed login count that triggers brute-force alert"
    )
    brute_force_window_seconds: int = Field(
        120, description="Time window for brute-force detection (seconds)"
    )
    success_after_failures_threshold: int = Field(
        3, description="Min prior failures for success-after-failures alert"
    )

    # ── Collector ────────────────────────────────────────────────────────────
    collector_poll_interval: float = Field(
        2.0, description="Event log poll interval in seconds"
    )
    collector_backend_url: str = Field(
        "http://localhost:8000", description="Backend base URL for the collector"
    )
    collector_secret: str = Field(
        "authsentinel-lab-secret-2026",
        description="Shared secret sent in X-Collector-Secret header",
    )

    # ── SMTP Configuration ──────────────────────────────────────────────────
    smtp_host: str = Field("smtp.gmail.com", description="SMTP server hostname")
    smtp_port: int = Field(587, description="SMTP server port")
    smtp_user: str = Field("kishorkhan.dev@gmail.com", description="SMTP username / sender")
    smtp_password: str = Field("rinv jjhh yxnh hyas", description="SMTP app password")
    smtp_from_name: str = Field("TAVIX GUARD SOC", description="SMTP sender display name")
    default_admin_email: str = Field("kishorkhan.dev@gmail.com", description="Default admin alert recipient")

    model_config = {"env_file": ".env", "env_prefix": "AS_", "extra": "ignore"}

    @field_validator("database_url")
    @classmethod
    def resolve_relative_database_url(cls, value: str) -> str:
        return _resolve_sqlite_database_url(value)


settings = Settings()
