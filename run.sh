#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Automated Launcher
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "⚡ Launching MWVSE Trading Panel (by @ghostwwn)..."

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3.10+ is required but not installed."
    exit 1
fi

# 2. Virtual environment setup
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# 3. Dependencies check
if ! python -c "import playwright, fastapi, rich" &> /dev/null; then
    echo "📦 Installing required dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    playwright install chromium
fi

# 4. Check .env
if [ ! -f ".env" ]; then
    echo "⚙️ First-time launch detected! Running interactive setup wizard..."
    python -m mwvse_panel setup
fi

# 5. Launch panel
python -m mwvse_panel run "$@"
