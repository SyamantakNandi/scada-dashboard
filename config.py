import os

ADMIN_EMAIL      = os.environ.get("ADMIN_EMAIL", "syamantaknandi499@gmail.com")
SECRET_KEY       = os.environ.get("SECRET_KEY",  "scada-industrial-secret-2024")
APP_HOST         = "0.0.0.0"
APP_PORT         = int(os.environ.get("PORT", 5000))
DATABASE_PATH    = os.environ.get("DATABASE_PATH", "scada.db")
DEFAULT_PLC_IP   = os.environ.get("DEFAULT_PLC_IP",   "192.168.1.5")
DEFAULT_PLC_PORT = int(os.environ.get("DEFAULT_PLC_PORT", 502))
