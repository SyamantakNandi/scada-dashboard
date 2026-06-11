"""
app.py - SCADA Dashboard Flask Application
Two roles: admin (full access) and user (dashboard view only)
"""

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash
)
from functools import wraps
import config, db, modbus_reader

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

db.init_db()


@app.context_processor
def inject_globals():
    return {
        "admin_email": config.ADMIN_EMAIL,
        "app_version": "2.0"
    }


# ─── Auth decorators ──────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


# ─── Auth routes ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "username" in session:
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
    return jsonify(modbus_reader.read_all_devices())

@app.route("/api/live/<int:device_id>")
@login_required
def api_live_device(device_id):
    dev = db.get_device(device_id)
    if not dev:
        return jsonify({"error": "Not found"}), 404
    params = db.get_params_for_device(device_id)
    return jsonify(modbus_reader.read_device(dev, params))

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
    devices   = db.get_all_devices()
    params_map= {d["id"]: db.get_params_for_device(d["id"]) for d in devices}
    users     = db.get_all_users()
    return render_template("admin.html",
                           devices=devices,
                           params_map=params_map,
                           users=users,
                           username=session["username"])


# ── PLC devices ───────────────────────────────────────────────────────────────
@app.route("/admin/device/add", methods=["POST"])
@admin_required
def admin_device_add():
    name     = request.form.get("name","").strip()
    ip       = request.form.get("ip","").strip()
    port     = int(request.form.get("port", 502))
    slave_id = int(request.form.get("slave_id", 1))
    enabled  = 1 if request.form.get("enabled") else 0
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO plc_devices (name,ip,port,slave_id,enabled) VALUES (?,?,?,?,?)",
        (name, ip, port, slave_id, enabled)
    )
    conn.commit(); conn.close()
    flash(f"Device '{name}' added.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/device/edit", methods=["POST"])
@admin_required
def admin_device_edit():
    dev_id   = int(request.form.get("device_id"))
    name     = request.form.get("name","").strip()
    ip       = request.form.get("ip","").strip()
    port     = int(request.form.get("port", 502))
    slave_id = int(request.form.get("slave_id", 1))
    enabled  = 1 if request.form.get("enabled") else 0
    conn = db.get_conn()
    conn.execute(
        "UPDATE plc_devices SET name=?,ip=?,port=?,slave_id=?,enabled=? WHERE id=?",
        (name, ip, port, slave_id, enabled, dev_id)
    )
    conn.commit(); conn.close()
    flash("Device updated.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/device/delete", methods=["POST"])
@admin_required
def admin_device_delete():
    dev_id = int(request.form.get("device_id"))
    conn = db.get_conn()
    conn.execute("DELETE FROM modbus_params WHERE device_id=?", (dev_id,))
    conn.execute("DELETE FROM plc_devices WHERE id=?", (dev_id,))
    conn.commit(); conn.close()
    flash("Device deleted.", "success")
    return redirect(url_for("admin"))


# ── Modbus parameters ─────────────────────────────────────────────────────────
@app.route("/admin/param/add", methods=["POST"])
@admin_required
def admin_param_add():
    device_id = int(request.form.get("device_id"))
    key     = request.form.get("key","").strip()
    label   = request.form.get("label","").strip()
    unit    = request.form.get("unit","").strip()
    address = int(request.form.get("address"))
    max_val = float(request.form.get("max_val", 100))
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO modbus_params (device_id,key,label,unit,address,max_val) VALUES (?,?,?,?,?,?)",
        (device_id, key, label, unit, address, max_val)
    )
    conn.commit(); conn.close()
    flash(f"Parameter '{label}' added.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/param/edit", methods=["POST"])
@admin_required
def admin_param_edit():
    param_id = int(request.form.get("param_id"))
    key     = request.form.get("key","").strip()
    label   = request.form.get("label","").strip()
    unit    = request.form.get("unit","").strip()
    address = int(request.form.get("address"))
    max_val = float(request.form.get("max_val", 100))
    conn = db.get_conn()
    conn.execute(
        "UPDATE modbus_params SET key=?,label=?,unit=?,address=?,max_val=? WHERE id=?",
        (key, label, unit, address, max_val, param_id)
    )
    conn.commit(); conn.close()
    flash("Parameter updated.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/param/delete", methods=["POST"])
@admin_required
def admin_param_delete():
    param_id = int(request.form.get("param_id"))
    conn = db.get_conn()
    conn.execute("DELETE FROM modbus_params WHERE id=?", (param_id,))
    conn.commit(); conn.close()
    flash("Parameter deleted.", "success")
    return redirect(url_for("admin"))


# ── User management ───────────────────────────────────────────────────────────
@app.route("/admin/user/add", methods=["POST"])
@admin_required
def admin_user_add():
    username = request.form.get("username","").strip()
    password = request.form.get("password","").strip()
    role     = request.form.get("role","user")
    if db.get_user(username):
        flash("Username already exists.", "danger")
        return redirect(url_for("admin"))
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO users (username,password,role) VALUES (?,?,?)",
        (username, db.hash_password(password), role)
    )
    conn.commit(); conn.close()
    flash(f"User '{username}' created.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/user/delete", methods=["POST"])
@admin_required
def admin_user_delete():
    user_id = int(request.form.get("user_id"))
    conn = db.get_conn()
    # prevent deleting last admin
    row = conn.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
    if row and row["username"] == "scada_admin":
        flash("Cannot delete the default admin account.", "danger")
        conn.close()
        return redirect(url_for("admin"))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit(); conn.close()
    flash("User deleted.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/user/edit", methods=["POST"])
@admin_required
def admin_user_edit():
    user_id  = int(request.form.get("user_id"))
    password = request.form.get("password","").strip()
    role     = request.form.get("role","user")
    conn = db.get_conn()
    if password:
        conn.execute(
            "UPDATE users SET password=?,role=? WHERE id=?",
            (db.hash_password(password), role, user_id)
        )
    else:
        conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
    conn.commit(); conn.close()
    flash("User updated.", "success")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    print(f"SCADA App running → http://localhost:{config.APP_PORT}")
    app.run(host=config.APP_HOST, port=config.APP_PORT, debug=False)
