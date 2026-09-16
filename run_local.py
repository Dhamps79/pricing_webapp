"""
Live Spreadsheet - 1-Click Local App Launcher
Runs backend + frontend locally without internet access.
Automatically initializes a clean database and opens the web application in your browser.
"""

import os
import sys
import time
import socket
import webbrowser
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def find_available_port(start_port: int = 8000) -> int:
    port = start_port
    while is_port_in_use(port) and port < start_port + 20:
        port += 1
    return port

def main():
    print("=" * 64)
    print("       LIVE SPREADSHEET - OFFLINE LOCAL APPLICATION")
    print("=" * 64)

    # 1. Resolve Python interpreter
    python_exe = sys.executable
    venv_candidates = [
        BACKEND_DIR / ".webapp" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python"),
        BACKEND_DIR / ".venv" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python"),
        ROOT_DIR / ".venv" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python"),
    ]
    for candidate in venv_candidates:
        if candidate.exists():
            python_exe = str(candidate)
            break

    # 2. Check if pre-compiled frontend distribution exists
    if not (FRONTEND_DIST / "index.html").exists():
        print("\n[*] Pre-compiled frontend not found. Building now...")
        try:
            subprocess.run(["npm", "run", "build"], cwd=str(FRONTEND_DIR), shell=True, check=True)
        except Exception as e:
            print(f"[!] Could not run npm build: {e}")
            print("[!] Please ensure frontend/dist is present.")

    # 3. Choose port
    port = find_available_port(8000)
    app_url = f"http://localhost:{port}"

    print(f"\n[*] Initializing offline app server at {app_url} ...")
    print("[*] Database: local embedded SQLite (clean, completely offline)")

    # 4. Configure environment
    env = os.environ.copy()
    db_path = ROOT_DIR / "live_spreadsheet.db"
    if "DATABASE_URL" not in env:
        env["DATABASE_URL"] = f"sqlite:///{db_path.resolve()}"
    env["PYTHONPATH"] = str(BACKEND_DIR)

    # 5. Open browser once server starts
    def open_browser():
        # Poll until the port starts accepting connections
        start_time = time.time()
        while time.time() - start_time < 15:
            if is_port_in_use(port):
                time.sleep(0.5)
                print(f"\n[OK] Server is ready! Opening your web browser to {app_url}")
                webbrowser.open(app_url)
                return
            time.sleep(0.4)
        # Fallback
        webbrowser.open(app_url)

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # 6. Run uvicorn server
    print("\n[+] Application running. Press Ctrl+C in this console to exit.\n")
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
                str(port),
            ],
            cwd=str(BACKEND_DIR),
            env=env,
        )
    except KeyboardInterrupt:
        print("\n[*] Live Spreadsheet closed cleanly.")

if __name__ == "__main__":
    main()


