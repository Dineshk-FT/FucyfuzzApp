import subprocess
import threading
import os
import signal
import sys
import time
from datetime import datetime
import re
from tkinter import messagebox


class ModuleRunner:
    """Enhanced module runner with success/failure tracking"""
    
    def __init__(self, app):
        self.app = app
        self.current_process = None
        
    def run_command(self, args_list, module_name="General"):
        """Run command with success/failure tracking and automatic case collection"""
        if self.app.current_process:
            messagebox.showwarning("Busy", "Process running. Stop first.")
            return

        working_dir = self.app.working_dir

        cmd = [sys.executable, "-m", "fucyfuzz.fucyfuzz"] + [str(a) for a in args_list]

        env = os.environ.copy()
        env["PYTHONPATH"] = working_dir + os.pathsep + env.get("PYTHONPATH", "")

        self.app._console_write(f"\n>>> [{module_name}] START: {' '.join(cmd)}\n")
        self.app._console_write(f">>> CWD: {working_dir}\n")

        current_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "module": module_name,
            "command": " ".join(cmd),
            "output": "", 
            "status": "Running",
            "success_cases": [],
            "failure_cases": []
        }

        def target():
            out_buf = []
            success_cases = []
            failure_cases = []
            
            try:
                # REMOVE OR MODIFY THE MODULE CHECK - it's causing timeout
                # Just try to run the command directly
                
                # Create process
                cflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                self.app.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=working_dir,
                    env=env,
                    creationflags=cflags,
                    universal_newlines=True
                )

                # Process output in real-time
                while True:
                    line = self.app.current_process.stdout.readline()
                    if not line and self.app.current_process.poll() is not None:
                        break
                    if line:
                        self.app._console_write(line)
                        out_buf.append(line)
                        
                        # Parse for success/failure cases
                        case = self._parse_case_line(line, module_name)
                        if case:
                            if case["type"] == "SUCCESS":
                                success_cases.append(case)
                            elif case["type"] == "FAILURE":
                                failure_cases.append(case)
                                # Create and store failure entry
                                failure_entry = self._create_failure_entry(module_name, case, current_entry)
                                # Use the app's method to add failure case
                                self.app.add_failure_case(module_name, failure_entry)

                rc = self.app.current_process.poll()
                
                # Determine overall status
                if rc == 0:
                    if failure_cases:
                        status = f"Completed with {len(failure_cases)} failures"
                    else:
                        status = "Success"
                else:
                    status = f"Failed ({rc})"
                
                self.app._console_write(f"\n<<< FINISHED (Code: {rc}) - Status: {status}\n")
                
                # Update entry with cases
                current_entry["output"] = "".join(out_buf)
                current_entry["status"] = status
                current_entry["success_cases"] = success_cases
                current_entry["failure_cases"] = failure_cases
                
                # Add to session history
                self.app.session_history.append(current_entry)
                
                # Show minimal success message
                if failure_cases:
                    self.app._console_write(f"[INFO] {len(failure_cases)} failure cases stored for review\n")
                    self.app._console_write(f"💡 Use 'View Failures' button to review and re-run them\n")

            except Exception as e:
                error_msg = f"\nERROR: {e}\n"
                self.app._console_write(error_msg)
                current_entry["output"] = "".join(out_buf) + f"\nError: {e}"
                current_entry["status"] = "Error"
                
                # Create error failure case
                error_case = {
                    "type": "Execution Error",
                    "message": str(e),
                    "details": error_msg,
                    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
                }
                failure_cases.append(error_case)
                
                # Store error failure case
                failure_entry = self._create_failure_entry(module_name, error_case, current_entry)
                self.app.add_failure_case(module_name, failure_entry)
                
                self.app.session_history.append(current_entry)
                
            finally:
                self.app.current_process = None

        # Start in background thread
        threading.Thread(target=target, daemon=True).start()

    def _create_failure_entry(self, module_name, case, current_entry):
        """Create a failure entry from a case"""
        return {
            "timestamp": current_entry['timestamp'],
            "module": module_name,
            "command": current_entry['command'],
            "output": case.get('details', case.get('message', '')),
            "status": "Failure",
            "case_details": case
        }
        
    def _parse_case_line(self, line, module_name):
        """Parse a line of output for success/failure cases"""
        line = line.strip()
        
        # Skip empty lines
        if not line:
            return None
            
        # Check for FAIL or ERROR markers first (simpler check)
        if '[FAIL]' in line or '[ERROR]' in line:
            # For LengthAttack specifically
            if module_name in ["LengthAttack", "lenattack"]:
                # Extract details with simpler regex
                id_match = re.search(r'ID=([0-9A-Fx]+)', line, re.IGNORECASE)
                dlc_match = re.search(r'DLC=(\d+)', line, re.IGNORECASE)
                len_match = re.search(r'LEN=(\d+)', line, re.IGNORECASE)
                error_match = re.search(r'\(([^)]+)\)', line)
                
                return {
                    "type": "FAILURE",
                    "timestamp": self._extract_timestamp(line),
                    "message": line,
                    "details": line,
                    "id": id_match.group(1) if id_match else "Unknown",
                    "dlc": dlc_match.group(1) if dlc_match else "Unknown",
                    "len": len_match.group(1) if len_match else "Unknown",
                    "error_type": error_match.group(1) if error_match else "Socket/Bus Error"
                }
            else:
                # Generic failure
                return {
                    "type": "FAILURE",
                    "timestamp": self._extract_timestamp(line),
                    "message": line,
                    "details": line,
                    "error_type": "Module Error"
                }
        
        # Check for SUCCESS markers
        elif '[SUCCESS]' in line:
            if module_name in ["LengthAttack", "lenattack"]:
                id_match = re.search(r'ID=([0-9A-Fx]+)', line, re.IGNORECASE)
                dlc_match = re.search(r'DLC=(\d+)', line, re.IGNORECASE)
                len_match = re.search(r'LEN=(\d+)', line, re.IGNORECASE)
                
                return {
                    "type": "SUCCESS",
                    "timestamp": self._extract_timestamp(line),
                    "message": line,
                    "details": line,
                    "id": id_match.group(1) if id_match else "Unknown",
                    "dlc": dlc_match.group(1) if dlc_match else "Unknown",
                    "len": len_match.group(1) if len_match else "Unknown"
                }
            else:
                return {
                    "type": "SUCCESS",
                    "timestamp": self._extract_timestamp(line),
                    "message": line,
                    "details": line
                }
        
        return None
    
    def _extract_timestamp(self, line):
        """Extract timestamp from a log line"""
        # Try to extract ISO timestamp
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)', line)
        if timestamp_match:
            return timestamp_match.group(1)
        
        # Return current time as fallback
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]