# skelion_agent/email_service.py — Transactional Email Service (Resend / SMTP / Console)

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger("skelion.email")


class EmailService:
    """
    Transactional email sender for:
    - Team invitations
    - Magic sign-in links
    - Critical production incident notifications
    - 0-regression PR synthesis alerts
    """

    def __init__(self):
        self.resend_api_key = os.getenv("RESEND_API_KEY")
        self.from_email = os.getenv("SKELION_FROM_EMAIL", "Skelion <alerts@skelion.dev>")
        self.is_configured = bool(self.resend_api_key)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email via Resend API or log to console fallback."""
        if not text_content:
            text_content = subject

        if self.resend_api_key:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {self.resend_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "from": self.from_email,
                            "to": [to_email],
                            "subject": subject,
                            "html": html_content,
                            "text": text_content
                        }
                    )
                    if resp.status_code in (200, 201):
                        return {"status": "sent", "provider": "resend", "id": resp.json().get("id")}
                    else:
                        logger.warning(f"Resend error {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"Email delivery exception: {e}")

        # Fallback for dev / unconfigured environments
        logger.info(f"[EmailService Fallback] To: {to_email} | Subject: {subject}")
        return {
            "status": "logged_to_console",
            "provider": "console_fallback",
            "recipient": to_email,
            "subject": subject,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def send_team_invitation(self, inviter_name: str, org_name: str, to_email: str, invite_url: str):
        """Send team member invitation email."""
        subject = f"You've been invited to join {org_name} on Skelion"
        html = f"""
        <div style="font-family:sans-serif; max-width:600px; margin:0 auto; padding:20px; background:#090d16; color:#f3f4f6; border-radius:8px;">
          <h2 style="color:#38bdf8;">Join {org_name} on Skelion</h2>
          <p>{inviter_name} has invited you to collaborate on Skelion Autonomous Production Intelligence.</p>
          <div style="margin:24px 0;">
            <a href="{invite_url}" style="background:#38bdf8; color:#000; font-weight:bold; padding:12px 24px; text-decoration:none; border-radius:6px; display:inline-block;">Accept Invitation</a>
          </div>
          <p style="font-size:12px; color:#9ca3af;">Or copy this link: {invite_url}</p>
        </div>
        """
        return await self.send_email(to_email, subject, html)

    async def send_incident_alert(self, org_name: str, to_email: str, incident_data: dict):
        """Send urgent incident notification."""
        route = incident_data.get("route", "POST /api")
        status = incident_data.get("status_code", 500)
        summary = incident_data.get("summary", "Unhandled exception")
        subject = f"[URGENT] Incident captured on {route} ({status})"
        html = f"""
        <div style="font-family:sans-serif; max-width:600px; margin:0 auto; padding:20px; background:#090d16; color:#f3f4f6; border-radius:8px;">
          <h2 style="color:#ef4444;">💥 Production Incident Captured</h2>
          <p>Organization: <b>{org_name}</b></p>
          <p>Endpoint: <code>{route}</code></p>
          <p>Status: <span style="background:#ef4444; color:#fff; padding:2px 6px; border-radius:4px;">{status}</span></p>
          <p>Summary: <i>{summary}</i></p>
          <p style="color:#10b981;">🛡️ Fail-Open Boundary Engaged: Request was buffered safely with Zero-PII exposure.</p>
        </div>
        """
        return await self.send_email(to_email, subject, html)


email_service = EmailService()
