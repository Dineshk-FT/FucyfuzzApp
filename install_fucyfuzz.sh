#!/bin/bash

# ======================================================
#      FucyFuzz Environment Installer (Optimized)
# ======================================================

echo "=============================================="
echo "      Installing FucyFuzz Environments"
echo "=============================================="

# --- Paths ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FUCYFUZZ_DIR="$SCRIPT_DIR/fucyfuzz"
SIMULATOR_DIR="$SCRIPT_DIR/Simulator"

# --- Required packages ---
FUCYFUZZ_PKGS="customtkinter cantools reportlab asammdf matplotlib"
SIMULATOR_PKGS="pygame python-can"

# --- Helper: setup venv and install packages ---
setup_venv() {
    local DIR=$1
    local PKGS=$2
    local NAME=$3

    echo ""
    echo "----------------------------------------------"
    echo "Setting up $NAME environment..."
    echo "Directory: $DIR"
    echo "----------------------------------------------"

    # 1. Clean old venv
    if [ -d "$DIR/venv" ]; then
        echo "Removing old venv..."
        rm -rf "$DIR/venv"
    fi

    # 2. Create venv using the absolute path of python3.11
    # We use --copies to avoid symlink confusion if desired, though symlinks are standard.
    echo "Creating venv..."
    /usr/bin/python3 -m venv "$DIR/venv"

    # 3. Check if activate exists (Safety Check)
    if [ ! -f "$DIR/venv/bin/activate" ]; then
        echo "❌ Error: venv failed to create 'activate' script in $DIR/venv/bin"
        return 1
    fi

    # 4. Activate and install
    # Note: Use the absolute path to source to be safe
    source "$DIR/venv/bin/activate"
    
    echo "Upgrading pip inside venv..."
    pip install --upgrade pip

    for PKG in $PKGS; do
        echo "Installing $PKG..."
        pip install "$PKG"
    done
    
    deactivate
    echo "✔ $NAME environment ready!"
}

# --- Setup CAN interface ---
setup_can_interface() {
    echo ""
    echo "Setting up CAN interface..."
    if ip link show vcan0 >/dev/null 2>&1; then
        echo "vcan0 already exists, ensuring it is UP..."
        sudo ip link set vcan0 up
    else
        echo "Creating vcan0 interface..."
        sudo modprobe vcan
        sudo ip link add dev vcan0 type vcan
        sudo ip link set vcan0 up
    fi
}

# --- Execute Steps ---
# Ensure directories exist first
mkdir -p "$FUCYFUZZ_DIR"
mkdir -p "$SIMULATOR_DIR"

setup_venv "$FUCYFUZZ_DIR" "$FUCYFUZZ_PKGS" "FucyFuzz"
setup_venv "$SIMULATOR_DIR" "$SIMULATOR_PKGS" "Simulator"
setup_can_interface

echo ""
echo "=============================================="
echo "Installation completed successfully!"
echo "=============================================="