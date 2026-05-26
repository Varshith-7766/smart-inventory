#!/usr/bin/env bash
# ===========================================================================
# Smart Inventory — One-Command Setup (macOS / Linux)
# ===========================================================================
# Usage:  chmod +x scripts/setup.sh && ./scripts/setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "===== Smart Inventory Setup ====="
echo ""

# ---- 1. Check prerequisites ----
echo "[1/5] Checking prerequisites..."

if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "[ERROR] Python not found. Install Python 3.11+ first."
    exit 1
fi
echo "  [OK] Python: $($PYTHON --version)"

if command -v mysql &> /dev/null; then
    echo "  [OK] MySQL client found"
else
    echo "  [WARN] MySQL client not in PATH. Ensure MySQL is running."
fi

# ---- 2. Install Python dependencies ----
echo ""
echo "[2/5] Installing Python dependencies..."
cd "$ROOT_DIR/backend"
$PYTHON -m pip install -r requirements.txt -q
echo "  [OK] Dependencies installed"

# ---- 3. Create .env if missing ----
echo ""
echo "[3/5] Configuring environment..."
if [ ! -f ".env" ]; then
    if [ -f "$ROOT_DIR/.env.example" ]; then
        cp "$ROOT_DIR/.env.example" ".env"
        echo "  [INFO] Created .env from .env.example"
        echo "  [INFO] Edit backend/.env with your MySQL password before proceeding."
        echo ""
        read -p "  Edit .env now? (y/n): " EDIT_ENV
        if [ "$EDIT_ENV" = "y" ]; then
            ${EDITOR:-nano} .env
        fi
    fi
fi

# Prompt for MySQL password
read -sp "  MySQL root password: " MYSQL_PASS
echo ""

# ---- 4. Create database & schema ----
echo ""
echo "[4/5] Creating database..."
mysql -u root -p"$MYSQL_PASS" < "$ROOT_DIR/database/schema.sql" 2>/dev/null && \
    echo "  [OK] Database schema created" || \
    echo "  [WARN] Schema may have failed — check your MySQL credentials"

# ---- 5. Start server ----
echo ""
echo "[5/5] Starting development server..."
echo ""
echo "============================================"
echo "  Server:  http://localhost:5000"
echo "  Health:  http://localhost:5000/health"
echo "  Stop:    Ctrl+C"
echo "============================================"
echo ""

cd "$ROOT_DIR/backend"
$PYTHON app.py
