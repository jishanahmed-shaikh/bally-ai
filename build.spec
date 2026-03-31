# PyInstaller spec file for Bally AI
# Usage: pyinstaller build.spec
#
# Before building:
#   1. pip install pyinstaller pystray pillow
#   2. Download poppler for Windows from:
#      https://github.com/oschwartz10612/poppler-windows/releases
#      Extract to a folder, set POPPLER_PATH below.

import sys
import os
from pathlib import Path

block_cipher = None

# ── Set this to your extracted poppler folder ─────────────────────────────────
# e.g. POPPLER_PATH = r"C:\tools\poppler-24.08.0\Library\bin"
POPPLER_PATH = os.environ.get("POPPLER_PATH", "")

# Collect poppler binaries if path is set
poppler_binaries = []
if POPPLER_PATH and Path(POPPLER_PATH).exists():
    for dll in Path(POPPLER_PATH).glob("*.dll"):
        poppler_binaries.append((str(dll), "poppler/bin"))
    for exe in Path(POPPLER_PATH).glob("*.exe"):
        poppler_binaries.append((str(exe), "poppler/bin"))

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=poppler_binaries,
    datas=[
        ("app", "app"),
        ("frontend", "frontend"),
    ],
    hiddenimports=[
        # uvicorn
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # fastapi / pydantic
        "fastapi",
        "fastapi.middleware",
        "pydantic",
        "pydantic.v1",
        # pdf
        "pdfplumber",
        "pdfminer",
        "pdfminer.high_level",
        "pdfminer.layout",
        # langgraph
        "langgraph",
        "langgraph.graph",
        "langchain_core",
        # groq
        "groq",
        # streamlit
        "streamlit",
        "streamlit.web.cli",
        "streamlit.web.server",
        "streamlit.runtime",
        "streamlit.runtime.scriptrunner",
        # data
        "altair",
        "pandas",
        "numpy",
        # ui
        "tkinter",
        "tkinter.messagebox",
        # tray
        "pystray",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "IPython", "jupyter"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BallyAI",
    debug=False,
    strip=False,
    upx=True,
    console=False,       # No black console window
    icon="assets/icon.ico" if Path("assets/icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="BallyAI",
)
