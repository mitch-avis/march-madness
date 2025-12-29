#!/usr/bin/env bash
set -euo pipefail

# March Madness Web Application (WSL/Ubuntu)

# Change to the project directory (directory containing this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists and activate it
if [[ -f ".venv/bin/activate" ]]; then
  echo "Activating virtual environment (.venv)..."
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
elif [[ -f "venv/bin/activate" ]]; then
  echo "Activating virtual environment (venv)..."
  # shellcheck disable=SC1091
  source "venv/bin/activate"
else
  echo "WARNING: Virtual environment not found at .venv/bin/activate (or venv/bin/activate)"
  echo "The application may not run correctly if dependencies aren't installed."
  read -r -p "Press Enter to continue anyway..." _
fi

# Start the Django development server on port 8080, accessible from network
echo "Starting Django server on 0.0.0.0:8080..."

# Where CSVs are written (WSL -> Windows OneDrive path)
export MARCH_MADNESS_DATA_PATH="/mnt/c/Users/mitch/OneDrive/March Madness/Data"

python manage.py runserver 0.0.0.0:8080
