#!/bin/bash

# FucyFuzz Launcher Script

echo "=========================================="
echo "    FucyFuzz Launcher"
echo "=========================================="

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Script directory: $SCRIPT_DIR"

# Paths
FUCYFUZZ_DIR="$SCRIPT_DIR/fucyfuzz"
SIMULATOR_DIR="$SCRIPT_DIR/Simulator"

# Check if directories exist
if [ ! -d "$FUCYFUZZ_DIR" ]; then
    echo "ERROR: FucyFuzz directory not found: $FUCYFUZZ_DIR"
    exit 1
fi

if [ ! -d "$SIMULATOR_DIR" ]; then
    echo "ERROR: Simulator directory not found: $SIMULATOR_DIR"
    exit 1
fi

# Function to setup CAN interface
setup_can_interface() {
    echo "Setting up CAN interface..."
    
    # Check if vcan0 already exists and is up
    if ip link show vcan0 >/dev/null 2>&1; then
        if ip link show vcan0 | grep -q "state UP"; then
            echo "vcan0 interface already exists and is UP"
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

# Function to check virtual environment
check_venv() {
    local venv_path="$1"
    local dir_name="$2"
    
    if [ ! -f "$venv_path/bin/python" ]; then
        echo "ERROR: Virtual environment not found at $venv_path"
        echo "Please create it first:"
        echo "  cd $dir_name && python -m venv venv"
        return 1
    fi
    return 0
}

# Setup CAN interface
setup_can_interface

# Check virtual environments
echo "Checking virtual environments..."
if ! check_venv "$FUCYFUZZ_DIR/venv" "$FUCYFUZZ_DIR"; then
    exit 1
fi

if ! check_venv "$SIMULATOR_DIR/venv" "$SIMULATOR_DIR"; then
    exit 1
fi

echo "Starting applications..."
echo ""

# Start CAN Simulator Dashboard
echo "Starting CAN Simulator Dashboard..."
cd "$SIMULATOR_DIR"
./venv/bin/python dashboard.py &
SIMULATOR_PID=$!
echo "CAN Simulator started with PID: $SIMULATOR_PID"

# Wait a moment for the simulator to start
sleep 3

# Start FucyFuzz GUI
echo "Starting FucyFuzz GUI..."
cd "$FUCYFUZZ_DIR"
./venv/bin/python test.py &
FUZZER_PID=$!
echo "FucyFuzz GUI started with PID: $FUZZER_PID"

echo ""
echo "=========================================="
echo "Both applications have been started!"
echo ""
echo "CAN Simulator Dashboard PID: $SIMULATOR_PID"
echo "FucyFuzz GUI PID: $FUZZER_PID"
echo ""
echo "CAN interface status:"
ip link show vcan0
echo "=========================================="

# Wait for FucyFuzz GUI to finish (it's the main application)
wait $FUZZER_PID

echo "FucyFuzz GUI closed. Stopping CAN Simulator..."
kill $SIMULATOR_PID 2>/dev/null
wait $SIMULATOR_PID 2>/dev/null

echo "All applications stopped."