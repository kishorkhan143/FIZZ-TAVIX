"""
AuthSentinel — Authentication Routes
=====================================
Email verification and JWT token management endpoints.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import (
    VerificationRequestRequest,
    VerificationRequestResponse,
    VerifyEmailResponse,
    UserResponse,
    AdminLoginRequest,
    TestAlertEmailRequest,
    AdminInfoResponse,
    UpdateProfileRequest,
)
import auth_service
import smtp_service

logger = logging.getLogger("authsentinel.auth_router")

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# ── Dependencies ──────────────────────────────────────────────────────────────
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to extract and validate JWT token from Authorization header.
    Returns the authenticated User object.
    Raises 401 if token is missing or invalid.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing",
        )
    
    token = auth_service.get_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Use: Bearer <token>",
        )
    
    payload = auth_service.verify_jwt_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )
    
    return user


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/request-verification",
    response_model=VerificationRequestResponse,
    summary="Request email verification",
    description="Send a verification email to the provided email address.",
)
async def request_verification(
    body: VerificationRequestRequest,
    db: Session = Depends(get_db),
) -> VerificationRequestResponse:
    """
    Request a verification email.
    
    Validates email format, checks if user exists, generates verification token,
    and sends email via SMTP.
    """
    email = body.email.strip().lower()
    
    # Validate email format
    is_valid, error_msg = auth_service.validate_email_format(email)
    if not is_valid:
        logger.warning(f"Invalid email format: {email} — {error_msg}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid email format: {error_msg}",
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    
    # Generate verification token (15-min expiry)
    verification_token = auth_service.generate_verification_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=auth_service.VERIFICATION_TOKEN_EXPIRY_MINUTES
    )
    
    # Create or update user
    if existing_user:
        existing_user.verification_token = verification_token
        existing_user.verification_token_expires_at = expires_at
        db.commit()
        user = existing_user
        logger.info(f"Updated verification token for existing user: {email}")
    else:
        user = User(
            email=email,
            role="admin",
            is_verified=False,
            verification_token=verification_token,
            verification_token_expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new user: {email}")
    
    # Send verification email via SMTP
    success, error = auth_service.send_verification_email(email, verification_token)
    if not success:
        logger.error(f"Failed to send verification email to {email}: {error}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send verification email: {error}",
        )
    
    logger.info(f"Verification email sent to {email}")
    return VerificationRequestResponse(
        success=True,
        message=f"Verification email sent to {email}. Please check your inbox.",
    )


@router.get(
    "/verify-email",
    response_model=VerifyEmailResponse,
    summary="Verify email with token",
    description="Verify email using the token sent in the verification link.",
)
async def verify_email(
    token: str = Query(..., description="Verification token from email link"),
    db: Session = Depends(get_db),
) -> VerifyEmailResponse:
    """
    Verify email using the token from the verification link.
    Validates token, marks user as verified, updates last_login_at, and issues a JWT token.
    """
    if not token or len(token) == 0:
        raise HTTPException(
            status_code=400,
            detail="Verification token is required",
        )
    
    # Find user by verification token
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        logger.warning(f"Verification attempted with invalid token: {token[:20]}...")
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token",
        )
    
    # Check if token has expired
    now = datetime.now(timezone.utc)
    if user.verification_token_expires_at and user.verification_token_expires_at < now:
        logger.warning(f"Verification token expired for user: {user.email}")
        raise HTTPException(
            status_code=400,
            detail="Verification token has expired. Please request a new one.",
        )
    
    # Mark user as verified
    user.is_verified = True
    user.verified_at = now
    user.last_login_at = now
    user.verification_token = None
    user.verification_token_expires_at = None
    db.commit()
    db.refresh(user)
    
    logger.info(f"User verified: {user.email}")
    
    # Generate JWT token
    jwt_token = auth_service.generate_jwt_token(user.id, user.email, user.role or "admin")
    
    return VerifyEmailResponse(
        success=True,
        message=f"Email verified successfully! Welcome, {user.email}",
        jwt_token=jwt_token,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role or "admin",
            "is_verified": user.is_verified,
        },
    )


@router.post(
    "/admin-login",
    response_model=VerifyEmailResponse,
    summary="Admin Quick Sign-in",
    description="Allows direct sign in for administrator accounts.",
)
async def admin_login(
    body: AdminLoginRequest,
    db: Session = Depends(get_db),
) -> VerifyEmailResponse:
    """
    Sign in directly as an administrator.
    Registers or updates the administrator profile, refreshes last login, and returns a JWT token.
    """
    email = body.email.strip().lower()
    now = datetime.now(timezone.utc)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            role="admin",
            is_verified=True,
            created_at=now,
            verified_at=now,
            last_login_at=now,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.is_verified = True
        user.role = user.role or "admin"
        user.last_login_at = now
        db.commit()
        db.refresh(user)

    jwt_token = auth_service.generate_jwt_token(user.id, user.email, user.role)
    logger.info(f"Admin logged in directly: {user.email}")

    return VerifyEmailResponse(
        success=True,
        message=f"Administrator session established for {user.email}",
        jwt_token=jwt_token,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role or "admin",
            "is_verified": user.is_verified,
        },
    )


@router.get(
    "/admin/info",
    response_model=AdminInfoResponse,
    summary="Get Admin & SMTP System Configuration",
)
async def get_admin_system_info(
    db: Session = Depends(get_db),
) -> AdminInfoResponse:
    """
    Returns active admin settings, SMTP delivery status, and notification recipient list.
    """
    recipients = smtp_service.get_active_recipient_emails(db)
    total_users = db.query(User).count()
    return AdminInfoResponse(
        admin_email=smtp_service.DEFAULT_ADMIN_EMAIL,
        smtp_host=smtp_service.SMTP_HOST,
        smtp_user=smtp_service.SMTP_USER,
        smtp_enabled=smtp_service.is_configured(),
        recipient_emails=recipients,
        total_users=total_users,
    )


@router.post(
    "/admin/test-alert-email",
    summary="Send Test Incident Alert Email via SMTP",
)
async def send_test_alert_email(
    body: Optional[TestAlertEmailRequest] = None,
    db: Session = Depends(get_db),
) -> dict:
    """
    Triggers an immediate test incident alert email via SMTP to verify recipient inbox delivery.
    """
    target = (body.recipient_email if body and body.recipient_email else None) or smtp_service.DEFAULT_ADMIN_EMAIL
    success, error = smtp_service.send_test_email(target)
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send SMTP test email: {error}",
        )
    return {
        "success": True,
        "message": f"Test incident alert email sent successfully to {target} via SMTP",
        "recipient": target,
    }


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get the profile of the currently authenticated user.",
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get the current authenticated user's information.
    Requires valid JWT token in Authorization header.
    """
    return UserResponse.model_validate(current_user)


@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update User Profile",
    description="Update user display name.",
)
@router.patch(
    "/profile",
    response_model=UserResponse,
    summary="Update User Profile",
    description="Update user display name.",
)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Update the current authenticated user's name.
    """
    current_user.name = body.name.strip()
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    logger.info(f"User profile updated: {current_user.email} -> name='{current_user.name}'")
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    summary="Logout",
    description="Logout the current user (frontend clears JWT from localStorage).",
)
async def logout(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Logout endpoint (frontend-driven).
    Frontend should clear the JWT token from localStorage.
    """
    logger.info(f"User logged out: {current_user.email}")
    return {
        "success": True,
        "message": "Logged out successfully. Clear your token from storage.",
    }
