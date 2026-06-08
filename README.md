# ⚡ Industrial SCADA Dashboard

A professional, full-featured SCADA web portal for WL4415 Modbus meters — with role-based access,
admin-managed PLC devices & parameters, real-time gauges, and free global hosting on Render.

---

## Features

| Feature | Details |
|---|---|
| **Login** | Admin & User roles, OTP-verified admin signup |
| **Dashboard** | Live Modbus data, metric cards + gauge charts, 2-second auto-refresh |
| **Multi-PLC** | Unlimited devices — each with its own IP, port, slave ID |
| **Admin Panel** | Add / Edit / Delete PLC devices, Modbus parameters, users — all in-browser |
| **Security** | Session auth, SHA-256 hashed passwords, admin-only routes |
| **Hosting** | Deployable to Render (free tier), Railway, or any VPS |

---

## Quick Start (local)

```bash
# 1. Clone / copy files
cd scada_project

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set Gmail App Password (for OTP emails)
export SMTP_PASSWORD="your-16-char-app-password"

# 5. Run
python app.py
# → http://localhost:5000
```

**Default admin login:** `admin` / `admin123`  ← **Change this immediately in the Admin Panel!**

---

## Gmail App Password (OTP email setup)

1. Go to your Google Account → Security → 2-Step Verification → **App Passwords**
2. Create an app password for "Mail"
3. Copy the 16-character password
4. Set it as `SMTP_PASSWORD` environment variable (see below)

> Without `SMTP_PASSWORD`, the OTP is printed to the server console — useful for local dev.

---

## 🌐 Deploying to Render (Free Global Hosting)

### Step 1 – Push to GitHub
```bash
git init
git add .
git commit -m "Initial SCADA app"
# Create a new repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/scada-dashboard.git
git push -u origin main
```

### Step 2 – Create Render Web Service
1. Go to **https://render.com** → Sign Up (free)
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
5. Under **Environment Variables**, add:
   | Key | Value |
   |---|---|
   | `SMTP_PASSWORD` | Your Gmail App Password |
   | `SECRET_KEY` | Any random 32+ character string |
   | `DATABASE_PATH` | `/opt/render/project/src/scada.db` |
   | `DEFAULT_PLC_IP` | Your PLC IP (e.g. `192.168.1.5`) |
6. Click **Deploy** — Render gives you a free URL like `https://scada-dashboard.onrender.com`

### Step 3 – First Login
- URL: `https://your-app.onrender.com`
- Login: `admin` / `admin123`
- Immediately go to **Admin Panel → Users** and change the default password

---

## ⚠ Important: PLC Network Access from the Cloud

When hosted on Render, the server cannot directly reach your local PLC
(which is on your factory LAN at e.g. `192.168.1.5`).

**Solutions:**

### Option A – VPN / Tunnel (Recommended)
Install **ngrok** or **Cloudflare Tunnel** on the machine connected to the PLC LAN:
```bash
# On the machine with PLC access:
pip install flask pymodbus==2.5.3
python app.py   # runs local API on port 5000

# Then expose it:
ngrok tcp 5000
# → gives you tcp://0.tcp.ngrok.io:XXXXX
```
Then in the Admin Panel, set the PLC IP to the ngrok address.

### Option B – Deploy on a local server / Raspberry Pi
Run the app on a machine **on the same network as the PLC**.
Use **no-ip.com** or **DuckDNS** for a free domain pointing to your router,
then port-forward port 5000 on your router.

### Option C – Industrial 4G Router
Many 4G industrial routers (Teltonika, Robustel) provide remote VPN access to your PLC network,
letting the cloud server reach the PLC directly.

---

## File Structure

```
scada_project/
├── app.py              ← Flask routes & auth
├── config.py           ← All settings (env-var overridable)
├── db.py               ← SQLite schema + helpers
├── modbus_reader.py    ← Pymodbus reader (reads from DB config)
├── mailer.py           ← Gmail OTP sender
├── requirements.txt
├── Procfile            ← For Render/Heroku
├── render.yaml         ← Render one-click deploy config
└── templates/
    ├── base.html
    ├── login.html
    ├── signup.html
    ├── signup_verify.html
    ├── dashboard.html
    └── admin.html
```

---

## Admin Capabilities

Everything in the Admin Panel is live — no code changes needed:

- **Add/Edit/Delete PLC devices** — IP, port, slave ID, enable/disable
- **Add/Edit/Delete Modbus parameters** — key, label, unit, register address, max gauge value
- **Add/Delete users** — assign admin or user (view-only) role
- **Admin signup** — OTP-protected, sent to `syamantaknandi499@gmail.com`

---

## Modbus Register Map (WL4415)

The default parameters match the WL4415 register map:

| Slave 1 | Slave 2 | Parameter |
|---|---|---|
| 5–6 | 113–114 | Voltage R Phase (V) |
| 7–8 | 115–116 | Voltage Y Phase (V) |
| 9–10 | 117–118 | Voltage B Phase (V) |
| 11–12 | 119–120 | Frequency (Hz) |
| 13–14 | 121–122 | Current R Phase (A) |
| … | … | … (see db.py for full list) |

All registers use **32-bit IEEE 754 float, little-endian word order**.
