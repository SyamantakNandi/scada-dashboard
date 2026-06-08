"""
app.py – Main Flask application for the Industrial SCADA Dashboard.

Routes:
  GET  /                  → redirect to login
  GET  /login             → login page
  POST /login             → authenticate
  GET  /signup            → admin-signup step 1 (request OTP)
  POST /signup/otp        → send OTP email
  POST /signup/verify     → verify OTP + create admin account
  GET  /logout            → clear session
  GET  /dashboard         → main SCADA dashboard (login required)
  GET  /api/live          → JSON live data for all devices
  GET  /api/devices       → list PLC devices
  GET  /api/params/<id>   → list params for a device
  ─── Admin-only ────────────────────────────────────────────────────
  GET  /admin             → admin panel
  POST /admin/device/add  → add PLC device
  POST /admin/device/edit → edit PLC device
  POST /admin/device/delete → delete PLC device
  POST /admin/param/add   → add modbus param
  POST /admin/param/edit  → edit modbus param
  POST /admin/param/delete → delete modbus param
  GET  /admin/users       → list users
  POST /admin/user/add    → add user
  POST /admin/user/delete → delete user
"""

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash
)
import time
import config
import db
import mailer
import modbus_reader

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


# ─── Init DB on startup ───────────────────────────────────────────────────────
db.init_db()


@app.context_processor
def inject_admin_email():
    return {"admin_email": config.ADMIN_EMAIL}


# ─── Auth helpers ─────────────────────────────────────────────────────────────
def logged_in():
    return "username" in session

def is_admin():
    return session.get("role") == "admin"

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not logged_in():
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not logged_in():
            return redirect(url_for("login"))
        if not is_admin():
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


# ─── Public routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if logged_in():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = db.get_user(username)
        if user and user["password"] == db.hash_password(password):
            session["username"] = user["username"]
            session["role"]     = user["role"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# Admin signup – step 1: enter username/password then request OTP
@app.route("/signup", methods=["GET", "POST"])
def signup():
    return render_template("signup.html")


@app.route("/signup/otp", methods=["POST"])
def signup_send_otp():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    if not username or not password:
        flash("Username and password are required.", "danger")
        return redirect(url_for("signup"))
    if db.get_user(username):
        flash("Username already taken.", "danger")
        return redirect(url_for("signup"))

    otp = mailer.generate_otp()
    mailer.store_otp(config.ADMIN_EMAIL, otp)
    ok  = mailer.send_otp_email(config.ADMIN_EMAIL, otp)

    # temporarily store pending data in session
    session["pending_admin"] = {"username": username, "password": password}

    if ok:
        flash(f"OTP sent to {config.ADMIN_EMAIL}. Enter it below to complete signup.", "info")
    else:
        flash("OTP generated (SMTP not configured – check server logs).", "warning")

    return render_template("signup_verify.html", email=config.ADMIN_EMAIL)


@app.route("/signup/verify", methods=["POST"])
def signup_verify():
    otp = request.form.get("otp", "").strip()
    pending = session.get("pending_admin")
    if not pending:
        flash("Session expired. Please start signup again.", "danger")
        return redirect(url_for("signup"))

    if not mailer.verify_otp(config.ADMIN_EMAIL, otp):
        flash("Invalid or expired OTP.", "danger")
        return render_template("signup_verify.html", email=config.ADMIN_EMAIL)

    conn = db.get_conn()
    conn.execute(
        "INSERT INTO users (username, password, role, email) VALUES (?,?,?,?)",
        (pending["username"], db.hash_password(pending["password"]), "admin", config.ADMIN_EMAIL)
    )
    conn.commit()
    conn.close()

    session.pop("pending_admin", None)
    flash("Admin account created! You can now log in.", "success")
    return redirect(url_for("login"))


# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    devices = db.get_all_devices()
    return render_template("dashboard.html",
                           devices=devices,
                           username=session["username"],
                           role=session["role"])


# ─── Live data API ────────────────────────────────────────────────────────────

@app.route("/api/live")
@login_required
def api_live():
    data = modbus_reader.read_all_devices()
    return jsonify(data)


@app.route("/api/live/<int:device_id>")
@login_required
def api_live_device(device_id):
    dev = db.get_device(device_id)
    if not dev:
        return jsonify({"error": "Device not found"}), 404
    params = db.get_params_for_device(device_id)
    result = modbus_reader.read_device(dev, params)
    return jsonify(result)


@app.route("/api/devices")
@login_required
def api_devices():
    return jsonify(db.get_all_devices())


@app.route("/api/params/<int:device_id>")
@login_required
def api_params(device_id):
    return jsonify(db.get_params_for_device(device_id))


# ─── Admin panel ─────────────────────────────────────────────────────────────

@app.route("/admin")
@admin_required
def admin():
    devices = db.get_all_devices()
    params_map = {d["id"]: db.get_params_for_device(d["id"]) for d in devices}
    users = db.get_all_users()
    return render_template("admin.html",
                           devices=devices,
                           params_map=params_map,
                           users=users,
                           username=session["username"])


# ── PLC devices ───────────────────────────────────────────────────────────────

@app.route("/admin/device/add", methods=["POST"])
@admin_required
def admin_device_add():
    name     = request.form.get("name", "").strip()
    ip       = request.form.get("ip", "").strip()
    port     = int(request.form.get("port", 502))
    slave_id = int(request.form.get("slave_id", 1))
    enabled  = 1 if request.form.get("enabled") else 0
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO plc_devices (name,ip,port,slave_id,enabled) VALUES (?,?,?,?,?)",
        (name, ip, port, slave_id, enabled)
    )
    conn.commit()
    conn.close()
    flash(f"Device '{name}' added.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/device/edit", methods=["POST"])
@admin_required
def admin_device_edit():
    dev_id   = int(request.form.get("device_id"))
    name     = request.form.get("name", "").strip()
    ip       = request.form.get("ip", "").strip()
    port     = int(request.form.get("port", 502))
    slave_id = int(request.form.get("slave_id", 1))
    enabled  = 1 if request.form.get("enabled") else 0
    conn = db.get_conn()
    conn.execute(
        "UPDATE plc_devices SET name=?,ip=?,port=?,slave_id=?,enabled=? WHERE id=?",
        (name, ip, port, slave_id, enabled, dev_id)
    )
    conn.commit()
    conn.close()
    flash("Device updated.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/device/delete", methods=["POST"])
@admin_required
def admin_device_delete():
    dev_id = int(request.form.get("device_id"))
    conn = db.get_conn()
    conn.execute("DELETE FROM plc_devices WHERE id=?", (dev_id,))
    conn.execute("DELETE FROM modbus_params WHERE device_id=?", (dev_id,))
    conn.commit()
    conn.close()
    flash("Device deleted.", "success")
    return redirect(url_for("admin"))


# ── Modbus parameters ─────────────────────────────────────────────────────────

@app.route("/admin/param/add", methods=["POST"])
@admin_required
def admin_param_add():
    device_id = int(request.form.get("device_id"))
    key     = request.form.get("key", "").strip()
    label   = request.form.get("label", "").strip()
    unit    = request.form.get("unit", "").strip()
    address = int(request.form.get("address"))
    max_val = float(request.form.get("max_val", 100))
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO modbus_params (device_id,key,label,unit,address,max_val) VALUES (?,?,?,?,?,?)",
        (device_id, key, label, unit, address, max_val)
    )
    conn.commit()
    conn.close()
    flash(f"Parameter '{label}' added.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/param/edit", methods=["POST"])
@admin_required
def admin_param_edit():
    param_id  = int(request.form.get("param_id"))
    key     = request.form.get("key", "").strip()
    label   = request.form.get("label", "").strip()
    unit    = request.form.get("unit", "").strip()
    address = int(request.form.get("address"))
    max_val = float(request.form.get("max_val", 100))
    conn = db.get_conn()
    conn.execute(
        "UPDATE modbus_params SET key=?,label=?,unit=?,address=?,max_val=? WHERE id=?",
        (key, label, unit, address, max_val, param_id)
    )
    conn.commit()
    conn.close()
    flash("Parameter updated.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/param/delete", methods=["POST"])
@admin_required
def admin_param_delete():
    param_id = int(request.form.get("param_id"))
    conn = db.get_conn()
    conn.execute("DELETE FROM modbus_params WHERE id=?", (param_id,))
    conn.commit()
    conn.close()
    flash("Parameter deleted.", "success")
    return redirect(url_for("admin"))


# ── User management ───────────────────────────────────────────────────────────

@app.route("/admin/user/add", methods=["POST"])
@admin_required
def admin_user_add():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    role     = request.form.get("role", "user")
    if db.get_user(username):
        flash("Username already exists.", "danger")
        return redirect(url_for("admin"))
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO users (username, password, role) VALUES (?,?,?)",
        (username, db.hash_password(password), role)
    )
    conn.commit()
    conn.close()
    flash(f"User '{username}' created.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/user/delete", methods=["POST"])
@admin_required
def admin_user_delete():
    user_id = int(request.form.get("user_id"))
    if user_id == 1:
        flash("Cannot delete the default admin.", "danger")
        return redirect(url_for("admin"))
    conn = db.get_conn()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash("User deleted.", "success")
    return redirect(url_for("admin"))


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"SCADA App running → http://localhost:{config.APP_PORT}")
    app.run(host=config.APP_HOST, port=config.APP_PORT, debug=False)
