"""
Bally AI — Bank Statement to Tally XML Converter
Windows launcher with system tray icon.

Flow:
  1. First run → Tkinter dialog asks for Groq API key → saved to %APPDATA%\bally-ai\config.json
  2. Starts FastAPI backend (uvicorn) in a background thread
  3. Starts Streamlit frontend as a subprocess
  4. Opens browser automatically
  5. System tray icon lets user open app, change API key, or quit
"""
import os
import sys
import time
import json
import threading
import webbrowser
import subprocess
import socket
from pathlib import Path

APP_NAME = "Bally AI"
APP_VERSION = "1.1.0"
CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "bally-ai"
CONFIG_FILE = CONFIG_DIR / "config.json"
API_PORT = 8000
UI_PORT = 8501

_streamlit_proc = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_base_path() -> Path:
    """Works both in dev and inside a PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


# ── API Key dialog ────────────────────────────────────────────────────────────

def show_api_key_dialog(current_key: str = "") -> str:
    """Tkinter dialog to enter / update the Groq API key."""
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title(f"{APP_NAME} — API Key Setup")
    root.geometry("500x240")
    root.resizable(False, False)
    root.lift()
    root.attributes("-topmost", True)

    # Header
    tk.Label(root, text="🏦 Bally AI Setup", font=("Arial", 15, "bold")).pack(pady=(18, 2))
    tk.Label(root, text="Enter your Groq API Key to get started.",
             font=("Arial", 10), fg="#444").pack()
    tk.Label(root, text="Get a free key at  https://console.groq.com",
             font=("Arial", 9), fg="#0066cc", cursor="hand2").pack(pady=(2, 10))

    frame = tk.Frame(root)
    frame.pack(padx=30, fill="x")
    tk.Label(frame, text="Groq API Key:", anchor="w").pack(fill="x")
    entry = tk.Entry(frame, width=60, show="*", font=("Consolas", 10))
    entry.pack(fill="x", pady=(2, 0))
    if current_key:
        entry.insert(0, current_key)

    result = {"key": None}

    def submit():
        key = entry.get().strip()
        if not key:
            messagebox.showerror("Required", "API key cannot be empty.")
            return
        result["key"] = key
        root.destroy()

    def on_close():
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    tk.Button(root, text="Save & Launch", command=submit,
              bg="#0066cc", fg="white", font=("Arial", 11, "bold"),
              padx=24, pady=6, relief="flat", cursor="hand2").pack(pady=14)

    root.mainloop()
    return result["key"]


def setup_env():
    """Load or prompt for GROQ_API_KEY."""
    config = load_config()
    key = config.get("GROQ_API_KEY", "").strip()

    if not key:
        key = show_api_key_dialog()
        if not key:
            sys.exit(0)
        config["GROQ_API_KEY"] = key
        save_config(config)

    os.environ["GROQ_API_KEY"] = key
    os.environ["FASTAPI_URL"] = f"http://localhost:{API_PORT}"
    return config


# ── Backend ───────────────────────────────────────────────────────────────────

def start_api():
    base = get_base_path()
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))

    # Add poppler to PATH if bundled
    poppler_path = base / "poppler" / "bin"
    if poppler_path.exists():
        os.environ["PATH"] = str(poppler_path) + os.pathsep + os.environ.get("PATH", "")

    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=API_PORT, log_level="error")


# ── Frontend ──────────────────────────────────────────────────────────────────

def start_frontend():
    global _streamlit_proc
    base = get_base_path()
    frontend_path = base / "frontend" / "app.py"

    # Wait for API to be ready
    for _ in range(30):
        if not is_port_free(API_PORT):
            break
        time.sleep(0.5)

    _streamlit_proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            str(frontend_path),
            "--server.port", str(UI_PORT),
            "--server.address", "127.0.0.1",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--theme.base", "light",
        ],
        env={**os.environ},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def open_browser():
    # Wait for Streamlit to be ready
    for _ in range(40):
        if not is_port_free(UI_PORT):
            break
        time.sleep(0.5)
    webbrowser.open(f"http://localhost:{UI_PORT}")


# ── System tray ───────────────────────────────────────────────────────────────

def build_tray_icon():
    """Build a pystray system tray icon with menu."""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        # pystray not available — just keep running without tray
        return None

    # Create a simple icon (blue square with "B")
    img = Image.new("RGB", (64, 64), color="#0066cc")
    draw = ImageDraw.Draw(img)
    draw.text((18, 14), "B", fill="white")

    def on_open(_icon, _item):
        webbrowser.open(f"http://localhost:{UI_PORT}")

    def on_change_key(_icon, _item):
        config = load_config()
        new_key = show_api_key_dialog(current_key=config.get("GROQ_API_KEY", ""))
        if new_key:
            config["GROQ_API_KEY"] = new_key
            save_config(config)
            os.environ["GROQ_API_KEY"] = new_key

    def on_quit(icon, _item):
        icon.stop()
        if _streamlit_proc:
            _streamlit_proc.terminate()
        os.kill(os.getpid(), 9)

    menu = pystray.Menu(
        pystray.MenuItem("Open Bally AI", on_open, default=True),
        pystray.MenuItem("Change API Key", on_change_key),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )

    return pystray.Icon(APP_NAME, img, APP_NAME, menu)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    setup_env()

    # Start backend
    threading.Thread(target=start_api, daemon=True).start()

    # Start frontend
    threading.Thread(target=start_frontend, daemon=True).start()

    # Open browser
    threading.Thread(target=open_browser, daemon=True).start()

    # System tray (keeps app alive on Windows)
    tray = build_tray_icon()
    if tray:
        tray.run()  # blocks — tray icon keeps process alive
    else:
        # Fallback: keep alive without tray
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            if _streamlit_proc:
                _streamlit_proc.terminate()
            sys.exit(0)
