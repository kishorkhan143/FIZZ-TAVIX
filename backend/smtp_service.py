"""
AuthSentinel / TAVIX GUARD — SMTP Email Service
================================================
Handles all email delivery via Gmail SMTP (smtp.gmail.com).
Sends immediate incident alert emails to logged-in admin accounts when
security incidents or threshold anomalies occur.
"""

import os
import asyncio
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Optional, List, Tuple

logger = logging.getLogger("authsentinel.smtp")

# ── SMTP Configuration ───────────────────────────────────────────────────────
# Pull from pydantic settings (config.py) so .env and hardcoded defaults work.
try:
    from config import settings as _cfg
    SMTP_HOST = _cfg.smtp_host
    SMTP_PORT = _cfg.smtp_port
    SMTP_USER = _cfg.smtp_user.strip()
    SMTP_PASSWORD = _cfg.smtp_password.replace(" ", "")
    SMTP_FROM_NAME = _cfg.smtp_from_name
    DEFAULT_ADMIN_EMAIL = _cfg.default_admin_email.strip()
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
except Exception:
    # Fallback to raw env vars if config import fails
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "").strip()
    _raw_pass = os.getenv("SMTP_PASSWORD", "")
    SMTP_PASSWORD = _raw_pass.replace(" ", "")
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "TAVIX GUARD SOC")
    DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "kishorkhan.dev@gmail.com").strip()
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def is_configured() -> bool:
    return bool(SMTP_HOST.strip() and SMTP_USER and SMTP_PASSWORD)


def get_smtp_connection(timeout: int = 15) -> smtplib.SMTP:
    """Create and authenticate a TLS SMTP connection."""
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=timeout)
    server.starttls()
    server.login(SMTP_USER, SMTP_PASSWORD)
    return server


def get_active_recipient_emails(db_session=None) -> List[str]:
    """
    Retrieve recipient emails for incident alerts.
    Includes:
    1. Default administrator email (kishorkhan.dev@gmail.com)
    2. All registered/verified users and admin accounts in database
    """
    recipients = set()
    if DEFAULT_ADMIN_EMAIL:
        recipients.add(DEFAULT_ADMIN_EMAIL.strip().lower())
    if SMTP_USER:
        recipients.add(SMTP_USER.strip().lower())

    if db_session:
        try:
            from models import User
            users = db_session.query(User).filter(
                (User.is_verified == True) | (User.role == "admin")
            ).all()
            for u in users:
                if u.email and "@" in u.email:
                    recipients.add(u.email.strip().lower())
        except Exception as e:
            logger.warning("Could not query User table for alert recipients: %s", e)

    return sorted(recipients)


def send_incident_alert_sync(
    incident: dict,
    recipients: Optional[List[str]] = None,
    db_session=None,
) -> Tuple[bool, Optional[str]]:
    """
    Synchronously format and send a security incident alert email via SMTP.
    """
    target_recipients = recipients or get_active_recipient_emails(db_session)
    if not target_recipients:
        target_recipients = [DEFAULT_ADMIN_EMAIL]

    alert_type = incident.get("alert_type", "SECURITY_ALERT")
    username = incident.get("username", "Unknown")
    source_ip = incident.get("source_ip", "Unknown")
    source_host = incident.get("source_host", "Unknown")
    target_computer = incident.get("target_computer", "System Terminal")
    risk_score = incident.get("risk_score", 0.0)
    risk_level = str(incident.get("risk_level", "HIGH")).upper()
    reason = incident.get("reason", "Suspicious activity detected")
    triggered_at = incident.get("triggered_at", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))

    subject = f"🚨 [TAVIX GUARD] Incident Alert: {alert_type} ({risk_level} Risk - {username})"
    from_header = f"{SMTP_FROM_NAME} <{SMTP_USER}>"

    recipients_display = ", ".join(target_recipients)

    text_content = f"""
=====================================================
          TAVIX GUARD SECURITY INCIDENT ALERT        
=====================================================

An incident was detected on the monitored system.

INCIDENT DETAILS:
-----------------
Alert Type:       {alert_type}
Risk Level:       {risk_level} (Score: {risk_score}/100)
Target Account:   {username}
Target Computer:  {target_computer}
Source IP:        {source_ip}
Source Host:      {source_host}
Triggered At:     {triggered_at}

DETECTION REASON:
{reason}

NOTIFIED ACCOUNTS:
{recipients_display}

RECOMMENDED ACTION:
1. Verify if user '{username}' initiated this authentication attempt.
2. If unauthorized, isolate endpoint '{target_computer}' immediately.
3. Review TAVIX GUARD dashboard for correlated event telemetry.

Dashboard: {FRONTEND_URL}/dashboard
"""

    badge_color = "#ef4444" if risk_level in ("HIGH", "CRITICAL") else "#f59e0b"

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #0b0f19;
      color: #e2e8f0;
    }}
    .wrapper {{
      max-width: 620px;
      margin: 24px auto;
      background: #111827;
      border: 1px solid #1f2937;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
    }}
    .header {{
      background: linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%);
      padding: 24px;
      text-align: center;
      border-bottom: 2px solid #ef4444;
    }}
    .header h1 {{
      margin: 0;
      font-size: 22px;
      color: #ffffff;
      letter-spacing: 0.5px;
    }}
    .header p {{
      margin: 6px 0 0 0;
      color: #fca5a5;
      font-size: 13px;
      font-weight: 500;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 12px;
      border-radius: 9999px;
      background-color: {badge_color};
      color: #ffffff;
      font-size: 12px;
      font-weight: 700;
      margin-top: 10px;
      text-transform: uppercase;
      letter-spacing: 1px;
    }}
    .content {{
      padding: 24px;
    }}
    .alert-summary {{
      background: #1e293b;
      border-left: 4px solid {badge_color};
      padding: 14px 16px;
      border-radius: 6px;
      margin-bottom: 20px;
      font-size: 14px;
      line-height: 1.5;
      color: #f8fafc;
    }}
    .grid-table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 20px;
    }}
    .grid-table tr {{
      border-bottom: 1px solid #1e293b;
    }}
    .grid-table td {{
      padding: 10px 6px;
      font-size: 13px;
    }}
    .label {{
      color: #94a3b8;
      width: 35%;
      font-weight: 500;
    }}
    .value {{
      color: #f1f5f9;
      font-weight: 600;
      font-family: monospace, monospace;
    }}
    .recommendations {{
      background: #182234;
      border-radius: 8px;
      padding: 16px;
      margin-top: 20px;
    }}
    .recommendations h3 {{
      margin: 0 0 10px 0;
      font-size: 14px;
      color: #38bdf8;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .recommendations ol {{
      margin: 0;
      padding-left: 20px;
      color: #cbd5e1;
      font-size: 13px;
      line-height: 1.6;
    }}
    .footer {{
      padding: 18px 24px;
      background: #0f172a;
      border-top: 1px solid #1e293b;
      text-align: center;
      font-size: 12px;
      color: #64748b;
    }}
    .btn {{
      display: inline-block;
      margin-top: 16px;
      background: #2563eb;
      color: #ffffff !important;
      text-decoration: none;
      padding: 10px 22px;
      border-radius: 6px;
      font-weight: 600;
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>🚨 TAVIX GUARD INCIDENT DETECTED</h1>
      <p>Security Operations Center — Real-time Incident Notification</p>
      <span class="badge">{risk_level} SEVERITY &bull; SCORE {risk_score}</span>
    </div>

    <div class="content">
      <div class="alert-summary">
        <strong>Incident Summary:</strong> {reason}
      </div>

      <table class="grid-table">
        <tr>
          <td class="label">Alert Type</td>
          <td class="value">{alert_type}</td>
        </tr>
        <tr>
          <td class="label">Target Account</td>
          <td class="value">{username}</td>
        </tr>
        <tr>
          <td class="label">Target Computer / Host</td>
          <td class="value">{target_computer}</td>
        </tr>
        <tr>
          <td class="label">Source IP Address</td>
          <td class="value">{source_ip}</td>
        </tr>
        <tr>
          <td class="label">Source Host</td>
          <td class="value">{source_host}</td>
        </tr>
        <tr>
          <td class="label">Detection Timestamp</td>
          <td class="value">{triggered_at}</td>
        </tr>
        <tr>
          <td class="label">Notified Login Accounts</td>
          <td class="value" style="font-family: inherit; font-size: 12px; color: #93c5fd;">{recipients_display}</td>
        </tr>
      </table>

      <div class="recommendations">
        <h3>Recommended Incident Response</h3>
        <ol>
          <li>Verify whether this logon activity was authorized by <strong>{username}</strong>.</li>
          <li>If unauthorized, immediately isolate host <strong>{target_computer}</strong>.</li>
          <li>Check TAVIX GUARD Dashboard for correlated intrusion events.</li>
        </ol>
        <div style="text-align: center;">
          <a href="{FRONTEND_URL}/dashboard" class="btn">View Live Incident in Dashboard</a>
        </div>
      </div>
    </div>

    <div class="footer">
      This automated alert was dispatched via SMTP to authorized administrator accounts.<br>
      &copy; 2026 TAVIX GUARD Incident Response System.
    </div>
  </div>
</body>
</html>
"""

    try:
        server = get_smtp_connection(timeout=15)
        for recipient in target_recipients:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_header
            msg["To"] = recipient
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            server.sendmail(SMTP_USER, [recipient], msg.as_string())
        server.quit()
        logger.info("[SMTP] Incident alert successfully sent to: %s", target_recipients)
        return True, None
    except Exception as e:
        logger.error("[SMTP ERROR] Failed to send incident alert: %s", e)
        return False, str(e)


async def send_incident_alert_async(
    incident: dict,
    recipients: Optional[List[str]] = None,
    db_session_factory=None,
) -> None:
    """
    Asynchronously dispatch incident alert via thread to avoid blocking requests.
    """
    def _worker():
        session = None
        if db_session_factory:
            session = db_session_factory()
        try:
            send_incident_alert_sync(incident, recipients, session)
        finally:
            if session:
                session.close()

    try:
        await asyncio.to_thread(_worker)
    except Exception as e:
        logger.error("[SMTP ASYNC ERROR] Failed in incident alert dispatch: %s", e)


def send_verification_email(email: str, verification_token: str) -> Tuple[bool, Optional[str]]:
    """
    Send email verification link via SMTP.
    """
    callback_url = f"{FRONTEND_URL}/verify-email?token={verification_token}"
    subject = "Verify your TAVIX GUARD Account"
    from_header = f"{SMTP_FROM_NAME} <{SMTP_USER}>"

    text_body = f"""
Hello,

Please verify your email address to access the TAVIX GUARD Dashboard.
Click or copy the verification link below:

{callback_url}

This link expires in 15 minutes.

— TAVIX GUARD Security
"""

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; }}
    .container {{ max-width: 540px; margin: 0 auto; background: #1e293b; padding: 28px; border-radius: 12px; border: 1px solid #334155; }}
    .btn {{ display: inline-block; background: #2563eb; color: #fff !important; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
  </style>
</head>
<body>
  <div class="container">
    <h2 style="color: #60a5fa; margin-top: 0;">TAVIX GUARD Verification</h2>
    <p>Please click the button below to verify your email and sign in to the TAVIX GUARD Security Dashboard.</p>
    <a href="{callback_url}" class="btn">Verify & Access Dashboard</a>
    <p style="font-size: 12px; color: #94a3b8;">Or copy and paste this link in your browser:<br><code>{callback_url}</code></p>
    <p style="font-size: 12px; color: #64748b; margin-top: 24px;">This link will expire in 15 minutes.</p>
  </div>
</body>
</html>
"""

    try:
        server = get_smtp_connection(timeout=15)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_header
        msg["To"] = email
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        server.sendmail(SMTP_USER, [email], msg.as_string())
        server.quit()
        logger.info("[SMTP] Verification email sent to %s", email)
        return True, None
    except Exception as e:
        logger.error("[SMTP ERROR] Failed to send verification email to %s: %s", email, e)
        return False, str(e)


def send_test_email(to_email: str) -> Tuple[bool, Optional[str]]:
    """
    Send a test incident alert to verify SMTP functionality.
    """
    sample_incident = {
        "alert_type": "TEST_INCIDENT_SIMULATION",
        "username": "admin_test",
        "source_ip": "127.0.0.1",
        "source_host": "SEC-STATION-01",
        "target_computer": "PRIMARY-DC-01",
        "risk_score": 95.0,
        "risk_level": "CRITICAL",
        "reason": "Test SMTP Incident Alert triggered by Administrator to confirm real-time dispatch.",
        "triggered_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
    return send_incident_alert_sync(sample_incident, [to_email])
