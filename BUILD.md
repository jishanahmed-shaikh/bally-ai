# Building the Windows .exe

## Prerequisites

```bash
pip install pyinstaller
```

Also make sure poppler is installed and on PATH (needed for pdfplumber):
- Download from https://github.com/oschwartz10612/poppler-windows/releases
- Extract and add the `bin/` folder to your system PATH

## Build

```bash
pyinstaller build.spec
```

Output will be in `dist/BallyAI/` — a folder containing `BallyAI.exe` and all dependencies.

## Distribute

Zip the entire `dist/BallyAI/` folder and share it. The user:
1. Extracts the zip
2. Double-clicks `BallyAI.exe`
3. On first run, a dialog asks for their Groq API key
4. The key is saved to `%APPDATA%\bally-ai\config.json`
5. Browser opens automatically at `http://localhost:8501`

## API Key storage

The key is stored in `%APPDATA%\bally-ai\config.json` on the user's machine.
To change the key, the user can delete that file and re-run the app.

## Notes

- The .exe bundle will be ~200-400MB due to Python + all ML dependencies
- Streamlit is launched as a subprocess from within the bundle
- poppler binaries must be bundled separately or pre-installed on the target machine
- For a cleaner install experience, consider wrapping the dist/ folder with Inno Setup
