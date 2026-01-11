#!/bin/bash

set -e  # exit immediately if any command fails

ROOT_DIR="$(pwd)"

echo "======================================"
echo " Installing FucyFuzzApp Components"
echo " Root: $ROOT_DIR"
echo "======================================"

#######################################
# Function to setup a Python project
#######################################
setup_project () {
  PROJECT_NAME=$1
  PROJECT_PATH="$ROOT_DIR/$PROJECT_NAME"

  echo ""
  echo "--------------------------------------"
  echo " Setting up: $PROJECT_NAME"
  echo "--------------------------------------"

  if [ ! -d "$PROJECT_PATH" ]; then
    echo "❌ Directory not found: $PROJECT_PATH"
    exit 1
  fi

  cd "$PROJECT_PATH"

  if [ ! -d "venv" ]; then
    echo "➡️  Creating virtual environment..."
    python3 -m venv venv
  else
    echo "ℹ️  Virtual environment already exists"
  fi

  echo "➡️  Activating virtual environment..."
  source venv/bin/activate

  echo "➡️  Upgrading pip..."
  pip install --upgrade pip

  if [ -f "requirements.txt" ]; then
    echo "➡️  Installing dependencies..."
    pip install -r requirements.txt
  else
    echo "⚠️  No requirements.txt found, skipping dependency install"
  fi

  deactivate
  echo "✅ $PROJECT_NAME setup complete"
}

#######################################
# Install both modules
#######################################
setup_project "fucyfuzz"
setup_project "Simulator"

echo ""
echo "======================================"
echo " ✅ All components installed successfully"
echo "======================================"
