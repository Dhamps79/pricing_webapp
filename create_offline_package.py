"""
Live Spreadsheet - Offline Distribution Package Generator
Creates a clean, ready-to-share ZIP archive for distribution to local PCs.
Excludes user-specific files (.db, pycache, .git, node_modules) while preserving
pre-compiled frontend assets and all application source files.
"""

import os
import sys
import zipfile
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DIST_ZIP_PATH = ROOT_DIR / "LiveSpreadsheet-Offline-App.zip"

EXCLUDE_PATTERNS = [
    ".git",
    ".github",
    ".agents",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    ".venv",
    ".webapp",
    "node_modules",
    "live_spreadsheet.db",
    "storage",
    "LiveSpreadsheet-Offline-App.zip",
    "*.pyc",
    "*.swp",
    "*.swo",
]

def should_exclude(rel_path_str: str) -> bool:
    normalized = rel_path_str.replace("\\", "/").strip("/")
    parts = normalized.split("/")

    # Explicit directory name matches
    for p in parts:
        if p in [
            ".git",
            ".github",
            ".agents",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "__pycache__",
            ".venv",
            ".webapp",
            "node_modules",
            "storage",
        ]:
            return True

    # Exact or suffix matches
    if normalized.endswith(".db") or normalized.endswith(".pyc"):
        return True
    if "LiveSpreadsheet-Offline-App.zip" in normalized:
        return True

    return False

def build_frontend_if_needed():
    frontend_dist = ROOT_DIR / "frontend" / "dist" / "index.html"
    if not frontend_dist.exists():
        print("[*] Building frontend distribution...")
        subprocess.run(["npm", "run", "build"], cwd=str(ROOT_DIR / "frontend"), shell=True, check=True)
    else:
        print("[OK] Pre-built frontend distribution verified.")

def create_package():
    print("=" * 64)
    print("  Creating Downloadable Offline Application Archive")
    print("=" * 64)

    build_frontend_if_needed()

    if DIST_ZIP_PATH.exists():
        print(f"[*] Removing existing {DIST_ZIP_PATH.name} ...")
        DIST_ZIP_PATH.unlink()

    print(f"[*] Bundling clean application files into {DIST_ZIP_PATH.name} ...")

    file_count = 0
    with zipfile.ZipFile(DIST_ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ROOT_DIR):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(ROOT_DIR)
                rel_path_str = str(rel_path)

                if should_exclude(rel_path_str):
                    continue

                # Add to ZIP under top-level folder 'LiveSpreadsheet-Offline-App'
                archive_name = f"LiveSpreadsheet-Offline-App/{rel_path_str.replace(chr(92), '/')}"
                zf.write(full_path, archive_name)
                file_count += 1

    zip_size_mb = DIST_ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"\n[SUCCESS] Packaged {file_count} files successfully!")
    print(f"[Archive]: {DIST_ZIP_PATH}")
    print(f"[Size]: {zip_size_mb:.2f} MB")
    print("\nThis package contains:")
    print(" - 1-Click launcher: run_app.bat")
    print(" - Python launcher: run_local.py")
    print(" - Environment setup: setup_offline_env.bat")
    print(" - User instructions: INSTRUCTIONS.txt")
    print(" - Compiled React frontend: frontend/dist/")
    print(" - FastAPI backend source: backend/")
    print(" - ZERO pre-existing user data (pure clean starting state)")

if __name__ == "__main__":
    create_package()
