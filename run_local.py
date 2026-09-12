"""
Live Spreadsheet - 1-Click Local Launcher
Runs backend + frontend with a clean SQLite database and opens the web app in your browser.
"""

import os
import sys
import time
import webbrowser
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"

def main():
    print("=" * 60)
    print("      Starting Live Spreadsheet (1-Click Local App)       ")
    print("=" * 60)

    # Check python version
    python_exe = sys.executable

    # Virtual environment check
    venv_python = BACKEND_DIR / ".webapp" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
    if venv_python.exists():
        python_exe = str(venv_python)

    # Check if frontend is built
    if not (FRONTEND_DIST / "index.html").exists():
        print("\n[!] Frontend build not found. Building now...")
        subprocess.run(["npm", "run", "build"], cwd=str(FRONTEND_DIR), shell=True, check=True)

    print("\n[*] Initializing app server on http://localhost:8000 ...")

    # Set default environment variables
    env = os.environ.copy()
    if "DATABASE_URL" not in env:
        env["DATABASE_URL"] = f"sqlite:///{ROOT_DIR / 'live_spreadsheet.db'}"

    # Schedule browser opening
    def open_browser():
        time.sleep(1.5)
        print("\n[*] Opening web browser to http://localhost:8000 ...")
        webbrowser.open("http://localhost:8000")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # Run uvicorn
    try:
        subprocess.run(
            [
                python_exe,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=str(BACKEND_DIR),
            env=env,
        )
    except KeyboardInterrupt:
        print("\n[!] Live Spreadsheet stopped.")

if __name__ == "__main__":
    main()

