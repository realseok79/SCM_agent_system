#!/bin/bash
# Move to the directory where this script is located
cd "$(dirname "$0")"

echo "🎨 Starting SCM AI Multi-Agent Streamlit Dashboard..."
../venv/bin/python -m streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0
