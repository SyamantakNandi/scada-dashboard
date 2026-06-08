"""
mailer.py – Sends OTP emails for admin signup.
Uses Gmail SMTP with App Password (set SMTP_PASSWORD env var).
"""

import smtplib
import random
import string
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config
import db
import sqlite3


OTP_TTL = 600   # 10 minutes


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


def send_otp_email(to_email: str, otp: str) -> bool:
    """Send the OTP via Gmail SMTP. Returns True on success."""
    if not config.SMTP_PASSWORD:
        print("[mailer] SMTP_PASSWORD not set – printing OTP to console:", otp)
        return True  # still allow flow in dev when password not set

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "SCADA Dashboard – Admin Signup OTP"
        msg["From"]    = config.SMTP_USER
        msg["To"]      = to_email

        html = f"""
        <html><body style="font-family:Segoe UI,sans-serif;background:#f0f4ff;padding:40px">
          <div style="max-width:420px;margin:auto;background:#fff;border-radius:16px;
                      padding:40px;box-shadow:0 4px 24px rgba(37,99,235,.12)">
            <div style="font-size:28px;font-weight:800;color:#2563eb;margin-bottom:8px">
              🏭 SCADA Portal
            </div>
            <p style="color:#334155;font-size:15px">Your one-time password for <b>Admin signup</b>:</p>
            <div style="font-size:44px;font-weight:900;letter-spacing:12px;
                        color:#1e40af;text-align:center;padding:20px 0">{otp}</div>
            <p style="color:#64748b;font-size:13px">This OTP is valid for 10 minutes.
            Do not share it with anyone.</p>
          </div>
        </body></html>
        """
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_USER, to_email, msg.as_string())

        return True

    except Exception as e:
        print(f"[mailer] Failed to send OTP: {e}")
        return False
