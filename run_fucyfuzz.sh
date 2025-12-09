#!/bin/bash

# ======================================================
#      FucyFuzz Application Runner (Separated)
# ======================================================

echo "=============================================="
echo "          Starting FucyFuzz Apps"
echo "=============================================="

# --- Paths ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FUCYFUZZ_DIR="$SCRIPT_DIR/fucyfuzz"
SIMULATOR_DIR="$SCRIPT_DIR/Simulator"

echo ""
echo "Checking vcan0 interface..."

# --- Create vCAN0 if not exists ---
if ! ip link show vcan0 > /dev/null 2>&1; then
    echo "vcan0 not found. Creating vCAN interface..."

    sudo modprobe vcan
    sudo modprobe can
    sudo modprobe can_raw

    sudo ip link add dev vcan0 type vcan
    sudo ip link set up vcan0

    echo "vcan0 created successfully."
else
    echo "vcan0 already exists. Skipping creation."
fi

echo ""
echo "Launching applications..."

# --- Launch CAN Simulator ---
cd "$SIMULATOR_DIR"
./venv/bin/python dashboard.py &
SIMULATOR_PID=$!
echo "CAN Simulator PID: $SIMULATOR_PID"

sleep 2

# --- Launch FucyFuzz GUI ---
cd "$FUCYFUZZ_DIR"
./venv/bin/python main_app.py &
FUZZER_PID=$!
echo "FucyFuzz GUI PID: $FUZZER_PID"

echo ""
echo "=============================================="
echo "Applications launched successfully!"
echo "CAN Simulator PID: $SIMULATOR_PID"
echo "FucyFuzz GUI PID: $FUZZER_PID"
echo "=============================================="

# --- Wait for FucyFuzz GUI to finish ---
wait $FUZZER_PID

echo ""
echo "FucyFuzz GUI closed. Stopping CAN Simulator..."
kill $SIMULATOR_PID 2>/dev/null
wait $SIMULATOR_PID 2>/dev/null

echo "All applications stopped."
