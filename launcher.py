"""
SCADA Dashboard Launcher v2.0
- Auto installs all Python dependencies
- Auto downloads ngrok
- Saves config so setup only runs once
- Opens browser automatically
- Professional console UI
"""

import os, sys, subprocess, threading, time, zipfile
import urllib.request, shutil, socket, json, webbrowser

APP_DIR    = os.path.dirname(os.path.abspath(__file__))
FLASK_PORT = 5000
CFG_FILE   = os.path.join(APP_DIR, "launcher_config.json")
NGROK_EXE  = os.path.join(APP_DIR, "ngrok.exe")
VENV_DIR   = os.path.join(APP_DIR, "venv")
VENV_PY    = os.path.join(VENV_DIR, "Scripts", "python.exe")
VENV_PIP   = os.path.join(VENV_DIR, "Scripts", "pip.exe")

G="\033[92m"; R="\033[91m"; Y="\033[93m"; B="\033[94m"; C="\033[96m"; W="\033[1m"; X="\033[0m"

def cls():   os.system("cls" if os.name=="nt" else "clear")
def ok(m):   print(f"  {G}✔{X}  {m}")
def info(m): print(f"  {C}▸{X}  {m}")
def warn(m): print(f"  {Y}⚠{X}  {m}")
def err(m):  print(f"  {R}✘{X}  {m}")
def hr():    print(f"  {B}{'─'*50}{X}")

def banner():
    cls()
    print(f"""
{B}{W}
  ╔════════════════════════════════════════════════════╗
  ║      ⚡  SCADA INDUSTRIAL DASHBOARD  ⚡            ║
  ║         WL4415 Monitoring System v2.0             ║
  ╚════════════════════════════════════════════════════╝
{X}""")

def load_cfg():
    if os.path.exists(CFG_FILE):
        with open(CFG_FILE) as f: return json.load(f)
    return {}

def save_cfg(c):
    with open(CFG_FILE,"w") as f: json.dump(c,f,indent=2)

def is_port_free(p):
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost",p))!=0

# ── Setup steps ───────────────────────────────────────────────────────────────
def step_venv():
    print(f"\n  {W}[1/4] Virtual Environment{X}")
    if os.path.exists(VENV_PY):
        ok("Already exists"); return True
    info("Creating...")
    r = subprocess.run([sys.executable,"-m","venv",VENV_DIR], capture_output=True)
    if r.returncode==0: ok("Created"); return True
    err("Failed to create venv"); return False

def step_deps():
    print(f"\n  {W}[2/4] Installing Dependencies{X}")
    req = os.path.join(APP_DIR,"requirements.txt")
    info("Installing flask, pymodbus, gunicorn...")
    r = subprocess.run([VENV_PIP,"install","-r",req,"-q"], capture_output=True)
    if r.returncode==0: ok("All packages installed"); return True
    warn("Retrying...")
    r2 = subprocess.run([VENV_PIP,"install","-r",req])
    return r2.returncode==0

def step_ngrok():
    print(f"\n  {W}[3/4] ngrok Setup{X}")
    if os.path.exists(NGROK_EXE):
        ok("ngrok.exe already present"); return True
    info("Downloading ngrok for Windows (requires internet)...")
    url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
    zp  = os.path.join(APP_DIR,"_ngrok.zip")
    try:
        def prog(n,bs,tot):
            pct=min(int(n*bs*100/tot),100)
            print(f"\r  {C}▸{X}  Downloading... {pct}%  ", end="", flush=True)
        urllib.request.urlretrieve(url, zp, prog); print()
        with zipfile.ZipFile(zp) as z: z.extractall(APP_DIR)
        os.remove(zp)
        if os.path.exists(NGROK_EXE): ok("ngrok downloaded"); return True
        err("ngrok.exe not found after extraction"); return False
    except Exception as e:
        err(f"Download failed: {e}")
        warn("Place ngrok.exe manually in the SCADA folder")
        return False

def step_ngrok_config(cfg):
    print(f"\n  {W}[4/4] ngrok Account Setup{X}")
    if cfg.get("ngrok_ok"):
        ok(f"Already configured → {cfg.get('domain','')}")
        return True

    print(f"""
  {Y}You need your ngrok Authtoken and Domain.{X}

  Steps to get them:
  1. Open browser → go to {C}dashboard.ngrok.com{X}
  2. Log in to your ngrok account
  3. Click {W}'Your Authtoken'{X} in the left sidebar → Copy it
  4. Click {W}'Cloud Edge → Domains'{X} → Copy your domain
     (looks like: xyz-abc-123.ngrok-free.dev)
""")
    hr()

    token = input(f"  {W}Paste Authtoken here:{X} ").strip()
    if not token: err("Authtoken required"); return False

    domain = input(f"  {W}Paste your Domain here:{X} ").strip()
    if not domain: err("Domain required"); return False
    if not domain.startswith("http"):
        domain = domain.strip("/")

    r = subprocess.run([NGROK_EXE,"config","add-authtoken",token], capture_output=True, text=True)
    if r.returncode!=0:
        err(f"Token save failed: {r.stderr}"); return False

    ok("Authtoken saved to ngrok config")
    cfg["ngrok_token"] = token
    cfg["domain"]      = domain
    cfg["ngrok_ok"]    = True
    save_cfg(cfg)
    ok(f"Domain saved: {domain}")
    return True

# ── Start services ────────────────────────────────────────────────────────────
flask_proc = None
ngrok_proc = None

def start_flask(cfg):
    global flask_proc
    print(f"\n  {W}Starting SCADA App...{X}")
    if not is_port_free(FLASK_PORT):
        ok(f"Already running on port {FLASK_PORT}"); return True

    env = os.environ.copy()
    env["SECRET_KEY"]    = "scada-industrial-secret-2024"
    env["DATABASE_PATH"] = os.path.join(APP_DIR,"scada.db")
    env["DEFAULT_PLC_IP"]= "192.168.1.5"

    flask_proc = subprocess.Popen(
        [VENV_PY, "app.py"], cwd=APP_DIR, env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name=="nt" else 0
    )

    for i in range(20):
        time.sleep(1)
        if not is_port_free(FLASK_PORT):
            ok(f"App started on port {FLASK_PORT}"); return True
        print(f"\r  {C}▸{X}  Starting{'.'*(i%4+1)}    ", end="", flush=True)
    print()
    err("App did not start — check the SCADA App window for errors")
    return False

def start_ngrok(cfg):
    global ngrok_proc
    domain = cfg.get("domain","")
    print(f"\n  {W}Starting ngrok Tunnel...{X}")
    if not domain:
        warn("No domain configured — running locally only"); return False
    if not os.path.exists(NGROK_EXE):
        warn("ngrok.exe not found — running locally only"); return False

    ngrok_proc = subprocess.Popen(
        [NGROK_EXE,"http",f"--domain={domain}",str(FLASK_PORT)],
        cwd=APP_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name=="nt" else 0
    )
    time.sleep(4)
    try:
        with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=5) as resp:
            data    = json.loads(resp.read())
            tunnels = data.get("tunnels",[])
            if tunnels:
                ok(f"Tunnel active → https://{domain}"); return True
    except: pass
    ok(f"ngrok started → https://{domain}"); return True

# ── Main loop ─────────────────────────────────────────────────────────────────
def live_screen(cfg):
    domain   = cfg.get("domain","")
    globalurl= f"https://{domain}" if domain else ""
    localurl = f"http://localhost:{FLASK_PORT}"

    print(f"""
{G}{W}  ╔════════════════════════════════════════════════════╗
  ║          ✅  SCADA DASHBOARD IS LIVE!              ║
  ╚════════════════════════════════════════════════════╝{X}

  {W}Default Login Credentials:{X}
  ┌─────────────────────────────────────────────────┐
  │  ADMIN  →  scada_admin  /  Admin@SCADA2024      │
  │  USER   →  scada_user   /  User@SCADA2024       │
  └─────────────────────────────────────────────────┘

  {W}Access URLs:{X}
  {C}Local  →  {localurl}{X}""")
    if globalurl:
        print(f"  {G}Global →  {globalurl}{X}")
    print(f"""
  {Y}Share the Global URL with your team.
  They can open it from any device, anywhere.{X}

  {W}Note:{X} PLC data shows LIVE only when laptop is
  connected to the PLC factory WiFi network.

  {R}Press Ctrl+C to stop the SCADA server.{X}
  {'─'*52}
""")
    try:
        i=0
        while True:
            time.sleep(3)
            app_ok  = not is_port_free(FLASK_PORT)
            astatus = f"{G}● Running{X}" if app_ok else f"{R}● Stopped{X}"
            print(f"\r  App: {astatus}  |  Uptime: {int(i*3//60)}m {int(i*3%60)}s   ", end="", flush=True)
            i+=1
    except KeyboardInterrupt:
        print(f"\n\n  {Y}Shutting down SCADA Dashboard...{X}")
        if flask_proc: flask_proc.terminate()
        if ngrok_proc: ngrok_proc.terminate()
        print(f"  {G}Done. Goodbye!{X}\n")

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    if os.name=="nt":
        os.system("color"); os.system("chcp 65001 > nul 2>&1")

    banner()
    cfg = load_cfg()

    # ── First-time setup ──────────────────────────────────────────────────────
    if not cfg.get("setup_done"):
        print(f"  {Y}{W}First-time setup — takes about 2-3 minutes.{X}\n")
        hr()

        if not step_venv():
            input("\n  Press Enter to exit..."); sys.exit(1)
        if not step_deps():
            warn("Some packages may be missing")
        step_ngrok()
        step_ngrok_config(cfg)

        cfg["setup_done"] = True
        save_cfg(cfg)

        print(f"\n  {G}{W}✔ Setup complete!{X}")
        hr()
        time.sleep(1)
        banner()

    # ── Re-check venv (in case manually deleted) ──────────────────────────────
    if not os.path.exists(VENV_PY):
        warn("Virtual environment missing — rebuilding...")
        step_venv()
        step_deps()

    # ── Start services ────────────────────────────────────────────────────────
    flask_ok = start_flask(cfg)
    if not flask_ok:
        input("\n  Press Enter to exit..."); sys.exit(1)

    ngrok_ok = start_ngrok(cfg)

    # ── Open browser ──────────────────────────────────────────────────────────
    domain = cfg.get("domain","")
    url    = f"https://{domain}" if (domain and ngrok_ok) else f"http://localhost:{FLASK_PORT}"
    def _open(): time.sleep(2); webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()

    live_screen(cfg)

if __name__=="__main__":
    main()
