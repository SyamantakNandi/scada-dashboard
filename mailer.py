"""
mailer.py – Cloud-safe OTP email sender.

Strategy (tried in order):
  1. SendGrid HTTP API  (port 443 – works everywhere, free 100 emails/day)
  2. SMTP SSL port 465  (fallback if SendGrid not configured)
  3. Console log        (last resort – admin reads OTP from Railway logs)

Set these env vars on Railway:
  SENDGRID_API_KEY  →  your SendGrid API key  (recommended)
  SMTP_PASSWORD     →  Gmail App Password     (fallback)
"""

import random
import string
import time
import json
import urllib.request
import base64
import os
import config
import db

OTP_TTL = 600  # 10 minutes


# ─── OTP store helpers ────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def store_otp(email: str, otp: str):
    conn = db.get_conn()
    expires_at = time.time() + OTP_TTL
    conn.execute(
        "INSERT INTO otp_store (email, otp, expires_at) VALUES (?,?,?)",
        (email, otp, expires_at)
    )
    conn.commit()
    conn.close()


def verify_otp(email: str, otp: str) -> bool:
    conn = db.get_conn()
    row = conn.execute(
        "SELECT id, expires_at FROM otp_store WHERE email=? AND otp=? ORDER BY id DESC LIMIT 1",
        (email, otp)
    ).fetchone()
    if not row:
        conn.close()
        return False
    if time.time() > row["expires_at"]:
        conn.execute("DELETE FROM otp_store WHERE id=?", (row["id"],))
        conn.commit()
        conn.close()
        return False
    conn.execute("DELETE FROM otp_store WHERE id=?", (row["id"],))
    conn.commit()
    conn.close()
    return True


# ─── Email sending ────────────────────────────────────────────────────────────

def _html_body(otp: str) -> str:
    return f"""
    <html><body style="font-family:Segoe UI,sans-serif;background:#0b0f1a;padding:40px">
      <div style="max-width:420px;margin:auto;background:#111827;border-radius:16px;
                  padding:40px;border:1px solid #1e2d45">
        <div style="font-size:26px;font-weight:800;color:#2563eb;margin-bottom:8px">
          ⚡ SCADA Portal
        </div>
        <p style="color:#94a3b8;font-size:15px">
          Your one-time password for <b style="color:#f1f5f9">Admin signup</b>:
        </p>
        <div style="font-size:52px;font-weight:900;letter-spacing:14px;
                    color:#3b82f6;text-align:center;padding:24px 0;
                    background:#0b0f1a;border-radius:12px;margin:16px 0">
          {otp}
        </div>
        <p style="color:#64748b;font-size:13px">
          Valid for 10 minutes. Do not share this OTP with anyone.
        </p>
      </div>
    </body></html>
    """


def _send_via_sendgrid(to_email: str, otp: str) -> bool:
    """Send via SendGrid Web API (HTTPS port 443 — never blocked)."""
    api_key = os.environ.get("SENDGRID_API_KEY", "")
    if not api_key:
        return False

    payload = json.dumps({
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": config.SMTP_USER, "name": "SCADA Portal"},
        "subject": "SCADA Dashboard – Admin Signup OTP",
        "content": [
            {"type": "text/plain", "value": f"Your SCADA Admin OTP: {otp}  (valid 10 min)"},
            {"type": "text/html",  "value": _html_body(otp)}
        ]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[mailer] SendGrid response: {resp.status}")
            return resp.status == 202
    except urllib.error.HTTPError as e:
        print(f"[mailer] SendGrid HTTP error: {e.code} {e.read()}")
        return False
    except Exception as e:
        print(f"[mailer] SendGrid error: {e}")
        return False


def _send_via_smtp_ssl(to_email: str, otp: str) -> bool:
    """Fallback: Gmail SMTP SSL on port 465."""
    if not config.SMTP_PASSWORD:
        return False
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "SCADA Dashboard – Admin Signup OTP"
        msg["From"]    = config.SMTP_USER
        msg["To"]      = to_email
        msg.attach(MIMEText(f"Your SCADA Admin OTP: {otp}  (valid 10 min)", "plain"))
        msg.attach(MIMEText(_html_body(otp), "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_USER, to_email, msg.as_string())

        print(f"[mailer] OTP sent via SMTP SSL port 465")
        return True
    except Exception as e:
        print(f"[mailer] SMTP SSL failed: {e}")
        return False


def send_otp_email(to_email: str, otp: str) -> bool:
    """Try SendGrid first, then SMTP SSL, then log to console."""

    # Method 1: SendGrid
    if _send_via_sendgrid(to_email, otp):
        return True

    # Method 2: Gmail SMTP SSL port 465
    if _send_via_smtp_ssl(to_email, otp):
        return True

    # Method 3: Console fallback — admin reads OTP from Railway deployment logs
    print("=" * 60)
    print(f"[mailer] ADMIN OTP = {otp}")
    print(f"[mailer] Recipient  = {to_email}")
    print(f"[mailer] Valid for 10 minutes")
    print("=" * 60)
    return True  # return True so signup flow still works
