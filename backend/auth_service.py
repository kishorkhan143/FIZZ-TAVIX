"""
AuthSentinel — Authentication Service
======================================
Email-based authentication using Resend for transactional emails.
Handles verification token generation, email sending, and JWT issuance.
"""

import os
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Tuple

import jwt
import resend
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger("authsentinel.auth")

# ── Configuration ────────────────────────────────────────────────────────────
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "noreply@tavix-guard.dev")
VERIFICATION_TOKEN_EXPIRY_MINUTES = 15
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30

# ── Frontend URL ─────────────────────────────────────────────────────────────
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
VERIFICATION_CALLBACK_URL = f"{FRONTEND_URL}/verify-email"


# ── Utility Functions ────────────────────────────────────────────────────────
def generate_verification_token() -> str:
    """Generate a secure random verification token."""
    return secrets.token_urlsafe(32)


def validate_email_format(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email format using email_validator library.
    Returns (is_valid, error_message).
    """
    try:
        validate_email(email, check_deliverability=False)
        return True, None
    except EmailNotValidError as e:
        return False, str(e)


import smtp_service


def send_verification_email(email: str, verification_token: str) -> Tuple[bool, Optional[str]]:
    """
    Send verification email via SMTP (smtp.gmail.com).
    Falls back to mock console logging if SMTP fails or is disabled.
    """
    success, error = smtp_service.send_verification_email(email, verification_token)
    if success:
        return True, None

    # Fallback to local console log
    logger.warning(f"[FALLBACK EMAIL] Verification link for {email}:")
    verification_url = f"{VERIFICATION_CALLBACK_URL}?token={verification_token}"
    logger.warning(f"[FALLBACK EMAIL] Click here: {verification_url}")
    return True, None


def generate_jwt_token(user_id: int, email: str, role: str = "admin") -> str:
    """
    Generate a JWT token for authenticated user.
    Expires in JWT_EXPIRY_DAYS days.
    """
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=JWT_EXPIRY_DAYS)
    
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": expiry,
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_jwt_token(token: str) -> Optional[Dict]:
    """
    Verify JWT token and return payload if valid.
    Returns None if token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        return None


def get_token_from_header(authorization_header: Optional[str]) -> Optional[str]:
    """
    Extract JWT token from Authorization header.
    Expected format: "Bearer <token>"
    """
    if not authorization_header:
        return None
    
    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]


# ── Initialization ───────────────────────────────────────────────────────────
def init_auth_service():
    """Initialize the auth service (called on app startup)."""
    if RESEND_API_KEY:
        logger.info("Resend API key configured. Emails will be sent via Resend.")
        resend.api_key = RESEND_API_KEY
    else:
        logger.warning("RESEND_API_KEY not set. Emails will be logged to console (mock mode).")
    
    logger.info(f"JWT secret key: {'configured' if JWT_SECRET_KEY != 'your-secret-key-change-in-production' else 'NOT CONFIGURED - using default'}")
    logger.info(f"Frontend URL: {FRONTEND_URL}")
