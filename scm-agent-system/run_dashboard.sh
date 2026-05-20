#!/bin/bash
# Move to the directory where this script is located
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "✅ Activating virtual environment..."
    source venv/bin/activate
fi

# Check if python/pip works in the activated environment
if ! command -v python &> /dev/null || ! python -c "import sys" &>/dev/null; then
    echo "⚠️ Virtual environment is broken or missing. Recreating virtual environment..."
    deactivate 2>/dev/null || true
    rm -rf venv
    python3 -m venv venv
    source venv/bin/activate
fi

# Install dependencies
echo "📥 Installing/updating dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# Run Streamlit dashboard
echo "🚀 Starting Streamlit SCM dashboard..."
python -m streamlit run dashboard/app.py
