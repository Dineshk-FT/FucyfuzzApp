#!/usr/bin/env python3

import os
import subprocess
import sys
import time
import signal
import threading

class FucyFuzzLauncher:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.fucyfuzz_dir = os.path.join(self.script_dir, "fucyfuzz")
        self.simulator_dir = os.path.join(self.script_dir, "Simulator")
        self.processes = []
        
    def run_command(self, cmd, cwd=None, shell=False, use_venv=None):
        """Run a command and return the process"""
        try:
            if use_venv:
                venv_python = os.path.join(use_venv, "bin", "python")
                if shell:
                    # For shell commands, use the venv python directly
                    cmd = f'"{venv_python}" {cmd}'
                else:
                    # For non-shell commands, replace the command
                    cmd = [venv_python] + cmd
            
            if shell:
                process = subprocess.Popen(cmd, shell=True, cwd=cwd)
            else:
                process = subprocess.Popen(cmd, cwd=cwd)
            
            self.processes.append(process)
            return process
        except Exception as e:
            print(f"Error running command: {e}")
            return None
    
    def setup_can_interface(self):
        """Setup the CAN interface"""
        print("Setting up CAN interface...")
        
        # Check if vcan0 already exists and is up
        try:
            result = subprocess.run(["ip", "link", "show", "vcan0"], 
                                  capture_output=True, text=True, check=False)
            if result.returncode == 0:
                if "state UP" in result.stdout:
                    print("vcan0 interface already exists and is UP")
                    return
                else:
                    print("vcan0 exists but is DOWN, bringing it UP...")
                    subprocess.run(["sudo", "ip", "link", "set", "vcan0", "up"], check=True)
            else:
                # Interface doesn't exist, create it
                print("Creating vcan0 interface...")
                subprocess.run(["sudo", "modprobe", "vcan"], check=True)
                subprocess.run(["sudo", "ip", "link", "add", "dev", "vcan0", "type", "vcan"], check=True)
                subprocess.run(["sudo", "ip", "link", "set", "vcan0", "up"], check=True)
                
        except subprocess.CalledProcessError as e:
            print(f"Warning: CAN interface setup failed: {e}")
        
        # Show interface status
        print("CAN interface status:")
        subprocess.run(["ip", "link", "show", "vcan0"])
    
    def start_simulator(self):
        """Start the CAN simulator dashboard"""
        print("Starting CAN Simulator Dashboard...")
        venv_path = os.path.join(self.simulator_dir, "venv")
        
        if not os.path.exists(os.path.join(venv_path, "bin", "python")):
            print(f"ERROR: Virtual environment not found at {venv_path}")
            print("Please create the virtual environment first:")
            print(f"cd {self.simulator_dir} && python -m venv venv")
            return None
        
        # Use the virtual environment's Python directly
        return self.run_command(["dashboard.py"], cwd=self.simulator_dir, use_venv=venv_path)
    
    def start_fucyfuzz(self):
        """Start the FucyFuzz GUI"""
        print("Starting FucyFuzz GUI...")
        venv_path = os.path.join(self.fucyfuzz_dir, "venv")
        
        if not os.path.exists(os.path.join(venv_path, "bin", "python")):
            print(f"ERROR: Virtual environment not found at {venv_path}")
            print("Please create the virtual environment first:")
            print(f"cd {self.fucyfuzz_dir} && python -m venv venv")
            return None
        
        # Use the virtual environment's Python directly
        return self.run_command(["test.py"], cwd=self.fucyfuzz_dir, use_venv=venv_path)
    
    def cleanup(self):
        """Cleanup processes and CAN interface"""
        print("\nCleaning up...")
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        print("Cleanup complete")
    
    def run(self):
        """Main execution"""
        print("=" * 50)
        print("    FucyFuzz System Launcher")
        print("=" * 50)
        
        # Check if directories exist
        if not os.path.exists(self.fucyfuzz_dir):
            print(f"ERROR: FucyFuzz directory not found: {self.fucyfuzz_dir}")
            return
        
        if not os.path.exists(self.simulator_dir):
            print(f"ERROR: Simulator directory not found: {self.simulator_dir}")
            return
        
        # Setup CAN interface
        self.setup_can_interface()
        print()
        
        # Start applications
        simulator_process = self.start_simulator()
        if not simulator_process:
            print("Failed to start CAN Simulator Dashboard")
            return
        
        time.sleep(2)  # Wait for simulator to start
        
        fucyfuzz_process = self.start_fucyfuzz()
        if not fucyfuzz_process:
            print("Failed to start FucyFuzz GUI")
            return
        
        print("\n" + "=" * 50)
        print("Both applications are running!")
        print("CAN Simulator Dashboard: Visual CAN bus simulator")
        print("FucyFuzz GUI: Security testing interface")
        print("Press Ctrl+C to stop both applications")
        print("=" * 50)
        
        # Wait for FucyFuzz to finish (it's the main GUI)
        try:
            fucyfuzz_process.wait()
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        finally:
            self.cleanup()

if __name__ == "__main__":
    launcher = FucyFuzzLauncher()
    
    # Set up signal handling for clean shutdown
    def signal_handler(sig, frame):
        print("\nReceived shutdown signal...")
        launcher.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    launcher.run()