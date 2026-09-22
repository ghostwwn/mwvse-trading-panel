#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Automated Launcher
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "⚡ Launching MWVSE Trading Panel (by @ghostwwn)..."

# 1. Determine best Python binary (prefer 3.11+)
if command -v python3.11 &> /dev/null; then
    PY_BIN="python3.11"
elif command -v python3.12 &> /dev/null; then
    PY_BIN="python3.12"
elif command -v python3 &> /dev/null; then
    PY_BIN="python3"
else
    echo "❌ Error: Python 3.10+ is required but not installed."
    exit 1
fi

# 2. Virtual environment setup
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment with $PY_BIN..."
    "$PY_BIN" -m venv venv
fi

source venv/bin/activate

# 3. Dependencies check
if ! python -c "import playwright, fastapi, rich, qrcode" &> /dev/null; then
    echo "📦 Installing required dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    playwright install chromium
fi

# 4. Check .env
if [ ! -f ".env" ]; then
    echo "⚙️ First-time launch detected! Running interactive setup wizard..."
    python main.py setup
fi

# 5. Launch panel
python main.py run "$@"
