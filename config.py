import os

# ─── Email (OTP for admin signup) ───────────────────────────────────────────
SMTP_HOST        = "smtp.gmail.com"
SMTP_PORT        = 587
SMTP_USER        = "syamantaknandi499@gmail.com"
SMTP_PASSWORD    = os.environ.get("SMTP_PASSWORD", "")   # set via env var
ADMIN_EMAIL      = "syamantaknandi499@gmail.com"

# ─── Flask ───────────────────────────────────────────────────────────────────
SECRET_KEY       = os.environ.get("SECRET_KEY", "change-me-in-production-32chars!")
APP_HOST         = "0.0.0.0"
APP_PORT         = int(os.environ.get("PORT", 5000))

# ─── SQLite database path ────────────────────────────────────────────────────
DATABASE_PATH    = os.environ.get("DATABASE_PATH", "scada.db")

# ─── Default PLC (overridden by DB entries) ──────────────────────────────────
DEFAULT_PLC_IP   = os.environ.get("DEFAULT_PLC_IP",   "192.168.1.5")
DEFAULT_PLC_PORT = int(os.environ.get("DEFAULT_PLC_PORT", 502))

# ─── Modbus polling interval (seconds) ───────────────────────────────────────
POLL_INTERVAL    = 2
