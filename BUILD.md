# Building the Windows Installer

## What gets produced

```
BallyAI-Setup.exe  (~150-250MB)
```

A standard Windows installer. Non-tech users:
1. Double-click `BallyAI-Setup.exe` → Next → Next → Finish
2. First launch → popup asks for Groq API key
3. Browser opens automatically at `http://localhost:8501`
4. System tray icon to open app, change API key, or quit

---

## Option A — Automatic (GitHub Actions)

Push a version tag and the installer is built and attached to a GitHub Release automatically:

```bash
git tag v1.1.0
git push origin v1.1.0
```

The workflow (`.github/workflows/release.yml`) will:
- Build the PyInstaller bundle on `windows-latest`
- Download and bundle Poppler binaries
- Compile the Inno Setup installer
- Attach `BallyAI-Setup.exe` to the GitHub Release

---

## Option B — Build locally on Windows

### 1. Install build tools

```bash
pip install pyinstaller pystray pillow
```

Install [Inno Setup 6](https://jrsoftware.org/isinfo.php) (free).

### 2. Download Poppler for Windows

Download from: https://github.com/oschwartz10612/poppler-windows/releases

Extract it, then set the environment variable:

```powershell
$env:POPPLER_PATH = "C:\tools\poppler-24.08.0\Library\bin"
```

### 3. (Optional) Add your app icon

Place a 256x256 `.ico` file at `assets/icon.ico`.
Place a 164x314 `.bmp` at `assets/wizard.bmp` (installer sidebar image).
Place a 55x58 `.bmp` at `assets/wizard_small.bmp` (installer top-right image).

### 4. Build the PyInstaller bundle

```bash
pyinstaller build.spec --noconfirm
```

Output: `dist/BallyAI/` folder (~150MB)

### 5. Build the installer

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

Output: `Output/BallyAI-Setup.exe`

---

## How the API key works for end users

- First launch: a dialog asks for the Groq API key
- Key is saved to `%APPDATA%\bally-ai\config.json` on their machine
- Never sent anywhere except directly to Groq's API
- To change the key: right-click the system tray icon → "Change API Key"
- To reset: delete `%APPDATA%\bally-ai\config.json` and relaunch

---

## Distributing

Share `Output/BallyAI-Setup.exe` directly, or upload it to:
- GitHub Releases (automatic via the release workflow)
- Google Drive / Dropbox
- Any file sharing service

The installer is self-contained — no Python, no dependencies, no technical knowledge required.
