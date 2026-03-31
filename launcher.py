"""
Bally AI — Bank Statement to Tally XML Converter
Launcher script for the PyInstaller .exe bundle.

Starts FastAPI backend + Streamlit frontend, opens browser automatically.
On first run, prompts for GROQ_API_KEY via a GUI dialog.
"""
import os
import sys
import time
import json
import threading
import webbrowser
import subprocess
from pathlib import Path

# ── Config file location ──────────────────────────────────────────────────────
APP_NAME = "bally-ai"
CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"

API_PORT = 8000
UI_PORT = 8501


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}


def save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def ask_for_api_key() -> str:
    """Show a Tkinter dialog asking for the Groq API key."""
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("Bally AI — First Run Setup")
    root.geometry("480x200")
    root.resizable(False, False)

    tk.Label(root, text="Enter your Groq API Key", font=("Arial", 13, "bold")).pack(pady=(20, 5))
    tk.Label(root, text="Get a free key at https://console.groq.com", fg="gray").pack()

    entry = tk.Entry(root, width=55, show="*")
    entry.pack(pady=10)

    result = {"key": ""}

    def submit():
        key = entry.get().strip()
        if not key:
            messagebox.showerror("Required", "API key cannot be empty.")
            return
        result["key"] = key
        root.destroy()

    tk.Button(root, text="Save & Launch", command=submit, bg="#0066cc", fg="white",
              font=("Arial", 11), padx=20, pady=5).pack()

    root.mainloop()
    return result["key"]


def setup_env():
    """Ensure GROQ_API_KEY is set, prompting on first run."""
    config = load_config()
    key = config.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY", "")

    if not key:
        key = ask_for_api_key()
        if not key:
            sys.exit("No API key provided. Exiting.")
        config["GROQ_API_KEY"] = key
        save_config(config)

    os.environ["GROQ_API_KEY"] = key
    os.environ["FASTAPI_URL"] = f"http://localhost:{API_PORT}"


def get_base_path() -> Path:
    """Return the base path — works both in dev and PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def start_api():
    """Start the FastAPI backend using uvicorn."""
    import uvicorn
    # Add base path to sys.path so app package is found
    base = get_base_path()
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=API_PORT,
        log_level="warning",
    )


def start_frontend():
    """Start the Streamlit frontend."""
    base = get_base_path()
    frontend_path = base / "frontend" / "app.py"

    # Give the API a moment to start
    time.sleep(3)

    subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            str(frontend_path),
            "--server.port", str(UI_PORT),
            "--server.address", "127.0.0.1",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ],
        env={**os.environ},
    )


def open_browser():
    """Open the browser after giving Streamlit time to start."""
    time.sleep(6)
    webbrowser.open(f"http://localhost:{UI_PORT}")


if __name__ == "__main__":
    setup_env()

    # Start API in background thread
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()

    # Start frontend in background thread
    frontend_thread = threading.Thread(target=start_frontend, daemon=True)
    frontend_thread.start()

    # Open browser
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    print(f"Bally AI is running.")
    print(f"  API:      http://localhost:{API_PORT}/docs")
    print(f"  Frontend: http://localhost:{UI_PORT}")
    print("Press Ctrl+C to stop.")

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)
