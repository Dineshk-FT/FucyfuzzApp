#!/bin/bash

# ======================================================
#      FucyFuzz Environment Installer (Separated)
# ======================================================

echo "=============================================="
echo "      Installing FucyFuzz Environments"
echo "=============================================="

# --- Paths ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FUCYFUZZ_DIR="$SCRIPT_DIR/fucyfuzz"
SIMULATOR_DIR="$SCRIPT_DIR/Simulator"

# --- Required packages ---
FUCYFUZZ_PKGS="customtkinter cantools reportlab"
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

    # Remove old venv
    if [ -d "$DIR/venv" ]; then
        echo "Removing old venv..."
        rm -rf "$DIR/venv"
    fi

    # Create venv
    echo "Creating venv..."
    python3 -m venv "$DIR/venv"

    # Activate and install packages
    source "$DIR/venv/bin/activate"
    python -m pip install --upgrade pip
    for PKG in $PKGS; do
        echo "Installing $PKG..."
        python -m pip install "$PKG"
    done
    deactivate
    echo "✔ $NAME environment ready!"
}

# --- Setup CAN interface ---
setup_can_interface() {
    echo ""
    echo "Setting up CAN interface..."
    if ip link show vcan0 >/dev/null 2>&1; then
        if ip link show vcan0 | grep -q "state UP"; then
            echo "vcan0 already UP"
        else
            echo "vcan0 exists but is DOWN, bringing it UP..."
            sudo ip link set vcan0 up
        fi
    else
        echo "Creating vcan0 interface..."
        sudo modprobe vcan
        sudo ip link add dev vcan0 type vcan
        sudo ip link set vcan0 up
    fi
    echo "CAN interface status:"
    ip link show vcan0
    echo ""
}

# --- Step 1: Setup venvs ---
setup_venv "$FUCYFUZZ_DIR" "$FUCYFUZZ_PKGS" "FucyFuzz"
setup_venv "$SIMULATOR_DIR" "$SIMULATOR_PKGS" "Simulator"

# --- Step 2: Setup CAN interface ---
setup_can_interface

echo ""
echo "=============================================="
echo "Installation completed successfully!"
echo "Run './run_fucyfuzz.sh' to start applications."
echo "=============================================="
