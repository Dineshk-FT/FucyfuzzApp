# FucyfuzzApp
# FucyFuzz – CAN Bus Fuzzing Toolkit

This repository contains **three main components**:

---

## 📁 Project Structure

### 🔹 **1. Simulator/**
This folder contains the **vCAN0 simulation environment** used to emulate CAN bus activity.  
It is useful for testing without using real vehicle hardware.

Contents include:
- Dashboard script  
- Assets  
- Virtual CAN setup  
- Supporting utilities for CAN playback and monitoring  

---

### 🔹 **2. fucyfuzz_tool/**
This folder contains the **modules and helper utilities** used by FucyFuzz.  
These include:
- Attack modules  
- Frame builders  
- CAN message utilities  
- Parsing tools  
- Helper functions used internally by the fuzzing engine  

This acts as the **core library** required by the fuzzer.

---

### 🔹 **3. fucyfuzz/**
This is the **main FucyFuzz fuzzing engine**.  
It contains:
- Fuzzing logic  
- CAN injection handlers  
- Attack scripts  
- Main fuzzing loop  

This is the actual **fuzzer** that interacts with CAN interfaces (physical or virtual).

---

## 🚀 How to Run the Fuzzer

To install the libraries (first time):

./install_fucyfuzz.sh

To start FucyFuzz automatically, simply run:

```sh
./run_fucyfuzz.sh

This script:

    Activates the environment (if needed)

    Initializes the CAN interface

    Launches the fuzzing engine

    Starts all required internal modules

If the script is not executable, run:

chmod +x run_fucyfuzz.sh

🖥️ Monitoring CAN Traffic (Open in Separate Terminals)

It is recommended to open multiple terminals to observe the simulation clearly.
✔ Terminal 1 – Run the Fuzzer

./run_fucyfuzz.sh

✔ Terminal 2 – CAN Dump Viewer

Use this to see live CAN messages:

candump vcan0

✔ Terminal 3 – Simulator Output

Navigate to the Simulator folder:

cd Simulator
python3 dashboard.py

Optional:

If you have additional utilities (listeners, injectors, etc.), you can run them in separate terminals inside their respective paths.
⚙ Requirements

    Python 3.10+

    python-can

    vCAN (virtual CAN) tools

    SocketCAN support

    Required Python modules installed in your environment

📌 Notes

    The venv/ folders are intentionally ignored in version control.

    All three components work together:

        Simulator generates virtual CAN activity

        fucyfuzz_tool provides modules

        fucyfuzz runs the actual fuzzing process

To make the simulator and fuzz tool executable

  1. go to path /path/Simulator and run build_simulator.sh. do the same for fuzz tool as well , /path/fucyfuzz and run build_fucyfuzz.sh