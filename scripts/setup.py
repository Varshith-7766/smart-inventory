"""
Cross-Platform Setup Script
===========================
Runs the entire setup process programmatically.

Usage:
    python scripts/setup.py

What it does:
  1. Creates the MySQL database and tables
  2. Seeds sample data
  3. Verifies the .env configuration
  4. Starts the Flask development server
"""

import os
import sys
import subprocess
from pathlib import Path

# Project root (two levels up from this script)
ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"


def run(cmd, cwd=None, shell=False, capture=False):
    """Run a command and print output."""
    print(f"  >> {' '.join(cmd)}")
    result = subprocess.run(
        cmd, cwd=cwd or str(ROOT), shell=shell,
        capture_output=capture, text=True
    )
    if result.returncode != 0:
        print(f"  [WARN] Command exited with code {result.returncode}")
        if capture:
            print(f"  stderr: {result.stderr}")
    return result


def step(num, total, label):
    print(f"\n{'='*60}")
    print(f"  Step {num}/{total}: {label}")
    print(f"{'='*60}")


def main():
    print(f"\n{'#'*60}")
    print(f"  Smart Inventory — Automated Setup")
    print(f"  Project: {ROOT}")
    print(f"{'#'*60}")

    total_steps = 5

    # ------------------------------------------------------------------
    # Step 1: Install Python dependencies
    # ------------------------------------------------------------------
    step(1, total_steps, "Installing Python dependencies")
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=str(BACKEND))

    # ------------------------------------------------------------------
    # Step 2: Set up .env
    # ------------------------------------------------------------------
    step(2, total_steps, "Setting up environment (.env)")
    env_file = BACKEND / ".env"
    env_example = ROOT / ".env.example"

    if not env_file.exists() and env_example.exists():
        import shutil
        shutil.copy(str(env_example), str(env_file))
        print("  Created .env from .env.example")

    if env_file.exists():
        print(f"  Found: {env_file}")
        # Read DATABASE_URL to detect MySQL config
        with open(env_file) as f:
            for line in f:
                if line.startswith("DATABASE_URL"):
                    print(f"  Using: {line.strip()}")
    else:
        print("  [WARN] No .env file found. Create one before running.")

    # ------------------------------------------------------------------
    # Step 3: Create database schema
    # ------------------------------------------------------------------
    step(3, total_steps, "Creating MySQL database and tables")

    # Try to get password from .env or prompt
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url and env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith("DATABASE_URL"):
                    db_url = line.split("=", 1)[1].strip().strip('"').strip("'")

    mysql_pass = os.getenv("MYSQL_ROOT_PASSWORD", "")
    if not mysql_pass:
        import getpass
        mysql_pass = getpass.getpass("  MySQL root password: ")

    schema_path = ROOT / "database" / "schema.sql"
    if schema_path.exists():
        result = subprocess.run(
            ["mysql", "-u", "root", f"-p{mysql_pass}"],
            stdin=open(schema_path),
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("  [OK] Database schema created successfully")
        else:
            print(f"  [WARN] Schema creation may have failed: {result.stderr}")

    # ------------------------------------------------------------------
    # Step 4: Seed sample data
    # ------------------------------------------------------------------
    step(4, total_steps, "Seeding sample data (60 days of sales)")
    result = run(
        [sys.executable, str(ROOT / "scripts" / "seed_data.py")],
        capture=True
    )
    if result.returncode == 0:
        print("  [OK] Sample data loaded")
    else:
        print("  [SKIP] Seeding failed — database may not be ready yet")

    # ------------------------------------------------------------------
    # Step 5: Start the server
    # ------------------------------------------------------------------
    step(5, total_steps, "Starting development server")
    print()
    print("  " + "-" * 50)
    print("  Server:  http://localhost:5000")
    print("  Health:  http://localhost:5000/health")
    print("  Stop:    Ctrl+C")
    print("  " + "-" * 50)
    print()

    os.chdir(str(BACKEND))
    os.environ["FLASK_DEBUG"] = "true"
    run([sys.executable, "app.py"])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)
