"""
db.py - SQLite helpers for SCADA web app.
Default accounts:
  Admin  → username: scada_admin   password: Admin@SCADA2024
  User   → username: scada_user    password: User@SCADA2024
"""

import sqlite3
import hashlib
import os
import config

DEFAULT_PARAMS_S1 = [
    ("v_r_phase",           "Voltage R Phase",       "V",    5,   500),
    ("v_y_phase",           "Voltage Y Phase",       "V",    7,   500),
    ("v_b_phase",           "Voltage B Phase",       "V",    9,   500),
    ("frequency",           "Frequency",             "Hz",  11,    60),
    ("current_r",           "Current R Phase",       "A",   13,   500),
    ("current_y",           "Current Y Phase",       "A",   15,   500),
    ("current_b",           "Current B Phase",       "A",   17,   500),
    ("v_ln_avg",            "LN Voltage Avg",        "V",   19,   500),
    ("v_ll_ry",             "LL Voltage RY",         "V",   21,   500),
    ("v_ll_yb",             "LL Voltage YB",         "V",   23,   500),
    ("v_ll_br",             "LL Voltage BR",         "V",   25,   500),
    ("v_ll_avg",            "LL Voltage Avg",        "V",   27,   500),
    ("current_total",       "Current Total",         "A",   29,   500),
    ("watt_total",          "Watt Total",            "W",   31,100000),
    ("watt_r",              "Watt R Phase",          "W",   33,100000),
    ("watt_y",              "Watt Y Phase",          "W",   35,100000),
    ("watt_b",              "Watt B Phase",          "W",   37,100000),
    ("var_total",           "VAR Total",             "VAR", 39,100000),
    ("var_r",               "VAR R Phase",           "VAR", 41,100000),
    ("var_y",               "VAR Y Phase",           "VAR", 43,100000),
    ("var_b",               "VAR B Phase",           "VAR", 45,100000),
    ("pf_avg",              "PF Avg",                "",    47,     1),
    ("pf_r",                "PF R Phase",            "",    49,     1),
    ("pf_y",                "PF Y Phase",            "",    51,     1),
    ("pf_b",                "PF B Phase",            "",    53,     1),
    ("va_total",            "VA Total",              "VA",  55,100000),
    ("va_r",                "VA R Phase",            "VA",  57,100000),
    ("va_y",                "VA Y Phase",            "VA",  59,100000),
    ("va_b",                "VA B Phase",            "VA",  61,100000),
    ("wh_delivered",        "WH Delivered",          "WH",  63,1000000),
    ("vah_delivered",       "VAH Delivered",         "VAH", 65,1000000),
    ("varh_ind",            "VARH IND Delivered",    "VARH",67,1000000),
    ("varh_cap",            "VARH CAP Delivered",    "VARH",69,1000000),
    ("volt_r_harm",         "Volt R Harmonic",       "%",   71,   100),
    ("volt_y_harm",         "Volt Y Harmonic",       "%",   73,   100),
    ("volt_b_harm",         "Volt B Harmonic",       "%",   75,   100),
    ("current_r_harm",      "Current R Harmonic",    "%",   77,   100),
    ("current_y_harm",      "Current Y Harmonic",    "%",   79,   100),
    ("current_b_harm",      "Current B Harmonic",    "%",   81,   100),
    ("rpm",                 "RPM",                   "RPM", 83,  4000),
    ("volt_vr_unbalance",   "Volt VR Unbalance",     "%",   85,   100),
    ("volt_vy_unbalance",   "Volt VY Unbalance",     "%",   87,   100),
    ("volt_vb_unbalance",   "Volt VB Unbalance",     "%",   89,   100),
    ("current_ar_unbalance","Current AR Unbalance",  "%",   91,   100),
    ("current_ay_unbalance","Current AY Unbalance",  "%",   93,   100),
    ("current_ab_unbalance","Current AB Unbalance",  "%",   95,   100),
    ("volt_r_angle",        "Volt R PH Angle",       "Deg", 97,   360),
    ("volt_y_angle",        "Volt Y PH Angle",       "Deg", 99,   360),
    ("volt_b_angle",        "Volt B PH Angle",       "Deg",101,   360),
    ("current_r_angle",     "Current R PH Angle",    "Deg",103,   360),
    ("current_y_angle",     "Current Y PH Angle",    "Deg",105,   360),
    ("current_b_angle",     "Current B PH Angle",    "Deg",107,   360),
    ("co2_emission",        "CO2 Emission",          "kg", 109,  1000),
    ("amp_max",             "Ampere Max",            "A",  111,   500),
]

DEFAULT_PARAMS_S2 = [
    ("v_r_phase",           "Voltage R Phase",       "V",  113,   500),
    ("v_y_phase",           "Voltage Y Phase",       "V",  115,   500),
    ("v_b_phase",           "Voltage B Phase",       "V",  117,   500),
    ("frequency",           "Frequency",             "Hz", 119,    60),
    ("current_r",           "Current R Phase",       "A",  121,   500),
    ("current_y",           "Current Y Phase",       "A",  123,   500),
    ("current_b",           "Current B Phase",       "A",  125,   500),
    ("v_ln_avg",            "LN Voltage Avg",        "V",   19,   500),
    ("v_ll_ry",             "LL Voltage RY",         "V",   21,   500),
    ("v_ll_yb",             "LL Voltage YB",         "V",   23,   500),
    ("v_ll_br",             "LL Voltage BR",         "V",   25,   500),
    ("v_ll_avg",            "LL Voltage Avg",        "V",   27,   500),
    ("current_total",       "Current Total",         "A",   29,   500),
    ("watt_total",          "Watt Total",            "W",   31,100000),
    ("watt_r",              "Watt R Phase",          "W",   33,100000),
    ("watt_y",              "Watt Y Phase",          "W",   35,100000),
    ("watt_b",              "Watt B Phase",          "W",   37,100000),
    ("var_total",           "VAR Total",             "VAR", 39,100000),
    ("var_r",               "VAR R Phase",           "VAR", 41,100000),
    ("var_y",               "VAR Y Phase",           "VAR", 43,100000),
    ("var_b",               "VAR B Phase",           "VAR", 45,100000),
    ("pf_avg",              "PF Avg",                "",    47,     1),
    ("pf_r",                "PF R Phase",            "",    49,     1),
    ("pf_y",                "PF Y Phase",            "",    51,     1),
    ("pf_b",                "PF B Phase",            "",    53,     1),
    ("va_total",            "VA Total",              "VA",  55,100000),
    ("va_r",                "VA R Phase",            "VA",  57,100000),
    ("va_y",                "VA Y Phase",            "VA",  59,100000),
    ("va_b",                "VA B Phase",            "VA",  61,100000),
    ("wh_delivered",        "WH Delivered",          "WH",  63,1000000),
    ("vah_delivered",       "VAH Delivered",         "VAH", 65,1000000),
    ("varh_ind",            "VARH IND Delivered",    "VARH",67,1000000),
    ("varh_cap",            "VARH CAP Delivered",    "VARH",69,1000000),
    ("volt_r_harm",         "Volt R Harmonic",       "%",   71,   100),
    ("volt_y_harm",         "Volt Y Harmonic",       "%",   73,   100),
    ("volt_b_harm",         "Volt B Harmonic",       "%",   75,   100),
    ("current_r_harm",      "Current R Harmonic",    "%",   77,   100),
    ("current_y_harm",      "Current Y Harmonic",    "%",   79,   100),
    ("current_b_harm",      "Current B Harmonic",    "%",   81,   100),
    ("rpm",                 "RPM",                   "RPM", 83,  4000),
    ("volt_vr_unbalance",   "Volt VR Unbalance",     "%",   85,   100),
    ("volt_vy_unbalance",   "Volt VY Unbalance",     "%",   87,   100),
    ("volt_vb_unbalance",   "Volt VB Unbalance",     "%",   89,   100),
    ("current_ar_unbalance","Current AR Unbalance",  "%",   91,   100),
    ("current_ay_unbalance","Current AY Unbalance",  "%",   93,   100),
    ("current_ab_unbalance","Current AB Unbalance",  "%",   95,   100),
    ("volt_r_angle",        "Volt R PH Angle",       "Deg", 97,   360),
    ("volt_y_angle",        "Volt Y PH Angle",       "Deg", 99,   360),
    ("volt_b_angle",        "Volt B PH Angle",       "Deg",101,   360),
    ("current_r_angle",     "Current R PH Angle",    "Deg",103,   360),
    ("current_y_angle",     "Current Y PH Angle",    "Deg",105,   360),
    ("current_b_angle",     "Current B PH Angle",    "Deg",107,   360),
    ("co2_emission",        "CO2 Emission",          "kg", 109,  1000),
    ("amp_max",             "Ampere Max",            "A",  111,   500),
]


def get_conn():
    conn = sqlite3.connect(config.DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role     TEXT NOT NULL DEFAULT 'user',
        email    TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS plc_devices (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        name     TEXT NOT NULL,
        ip       TEXT NOT NULL,
        port     INTEGER NOT NULL DEFAULT 502,
        slave_id INTEGER NOT NULL DEFAULT 1,
        enabled  INTEGER NOT NULL DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS modbus_params (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER NOT NULL,
        key       TEXT NOT NULL,
        label     TEXT NOT NULL,
        unit      TEXT NOT NULL DEFAULT '',
        address   INTEGER NOT NULL,
        max_val   REAL NOT NULL DEFAULT 100,
        FOREIGN KEY (device_id) REFERENCES plc_devices(id) ON DELETE CASCADE
    )""")

    conn.commit()

    # ── Seed default admin ────────────────────────────────────────────────────
    c.execute("SELECT id FROM users WHERE username='scada_admin'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username,password,role,email) VALUES (?,?,?,?)",
            ("scada_admin", hash_password("Admin@SCADA2024"), "admin", config.ADMIN_EMAIL)
        )

    # ── Seed default user ─────────────────────────────────────────────────────
    c.execute("SELECT id FROM users WHERE username='scada_user'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username,password,role) VALUES (?,?,?)",
            ("scada_user", hash_password("User@SCADA2024"), "user")
        )

    conn.commit()

    # ── Seed default PLC devices ──────────────────────────────────────────────
    c.execute("SELECT id FROM plc_devices")
    if not c.fetchone():
        c.execute(
            "INSERT INTO plc_devices (name,ip,port,slave_id) VALUES (?,?,?,?)",
            ("WL4415 - Unit 1", config.DEFAULT_PLC_IP, config.DEFAULT_PLC_PORT, 1)
        )
        d1 = c.lastrowid
        c.execute(
            "INSERT INTO plc_devices (name,ip,port,slave_id) VALUES (?,?,?,?)",
            ("WL4415 - Unit 2", config.DEFAULT_PLC_IP, config.DEFAULT_PLC_PORT, 2)
        )
        d2 = c.lastrowid
        conn.commit()
        for row in DEFAULT_PARAMS_S1:
            c.execute(
                "INSERT INTO modbus_params (device_id,key,label,unit,address,max_val) VALUES (?,?,?,?,?,?)",
                (d1, *row)
            )
        for row in DEFAULT_PARAMS_S2:
            c.execute(
                "INSERT INTO modbus_params (device_id,key,label,unit,address,max_val) VALUES (?,?,?,?,?,?)",
                (d2, *row)
            )
        conn.commit()

    conn.close()


def get_all_devices():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM plc_devices ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_device(device_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM plc_devices WHERE id=?", (device_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_params_for_device(device_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM modbus_params WHERE device_id=? ORDER BY address",
        (device_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user(username):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT id,username,role,email FROM users ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]
