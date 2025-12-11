import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import signal
import sys
import time
import random
import json
from datetime import datetime
from collections import defaultdict
import csv

# --- OPTIONAL IMPORTS ---
try:
    import cantools
except ImportError:
    cantools = None

# Import our modules
from report_generators import EnhancedPDFReport, FailureReport
from report_generators import REPORTLAB_AVAILABLE
from frame_classes import (
    ScalableFrame, ConfigFrame, ReconFrame, DemoFrame, FuzzerFrame,
    LengthAttackFrame, DCMFrame, UDSFrame, AdvancedFrame, SendFrame, MonitorFrame
)
# Add to the imports section at the top of main_app.py
from dashboard_frame import DashboardFrame
from modules import ModuleRunner
from fonts import FontConfig

class FucyfuzzApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FUCYFUZZ INTERFACE")
        self.geometry("1400x1100")
        self.minsize(1000, 700)
        # Base dimensions for scaling calculations
        self.base_width = 1400
        self.base_height = 950

        # Data Management - INITIALIZE THESE FIRST
        self.current_process = None
        self.session_history = []
        self.full_log_buffer = []
        self.pending_console_messages = []  # Store messages until console is ready
        self.failure_cases = {}  # Store failure cases by module: {module_name: [failed_entries]}
        self.raw_logs = [] 

        # GLOBAL DBC STORE
        self.dbc_db = None
        self.dbc_messages = {}

        self.load_failure_cases_from_file()
        # Initialize Module Runner
        self.module_runner = ModuleRunner(self)
        # Initialize PDF Report Generator
        self.pdf_generator = EnhancedPDFReport(self)

        # Initialize Failure Report Generator
        self.failure_report = FailureReport(self)

        # --- INITIALIZE WORKING DIRECTORY ---
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_script_dir)
        default_path = os.path.join(parent_dir, "fucyfuzz_tool")

        if os.path.exists(default_path):
            self.working_dir = default_path
            self.pending_console_messages.append(f"[INFO] Auto-detected working directory: {self.working_dir}\n")
        else:
            possible_paths = [
                default_path,
                os.path.join(current_script_dir, "fucyfuzz_tool"),
                os.path.join(parent_dir, "..", "fucyfuzz_tool"),
                os.path.join(os.getcwd(), "fucyfuzz_tool"),
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    self.working_dir = path
                    self.pending_console_messages.append(f"[INFO] Found working directory: {self.working_dir}\n")
                    break
            else:
                self.working_dir = os.getcwd()
                self.pending_console_messages.append(f"[WARNING] Using current directory as fallback: {self.working_dir}\n")
                self.pending_console_messages.append("[WARNING] Some features may not work correctly.\n")

        # Layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ===========================
        # 1) TABVIEW WITH SCALING
        # ===========================
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        tab_names = [
            "Configuration", "Recon", "Dashboard","Demo", "Fuzzer", "Length Attack",
            "DCM","UDS", "Advanced", "Send", "Monitor"
        ]
        for name in tab_names:
            self.tabs.add(name)

        # ===========================
        # 2) TAB FRAMES
        # ===========================
        self.frames = {}
        self.frames["config"] = ConfigFrame(self.tabs.tab("Configuration"), self)
        self.frames["recon"] = ReconFrame(self.tabs.tab("Recon"), self)
        self.frames["dashboard"] = DashboardFrame(self.tabs.tab("Dashboard"), self)
        self.frames["demo"] = DemoFrame(self.tabs.tab("Demo"), self)
        self.frames["fuzzer"] = FuzzerFrame(self.tabs.tab("Fuzzer"), self)
        self.frames["lenattack"] = LengthAttackFrame(self.tabs.tab("Length Attack"), self)
        self.frames["dcm"] = DCMFrame(self.tabs.tab("DCM"), self)
        self.frames["uds"] = UDSFrame(self.tabs.tab("UDS"), self)
        self.frames["advanced"] = AdvancedFrame(self.tabs.tab("Advanced"), self)
        self.frames["send"] = SendFrame(self.tabs.tab("Send"), self)
        self.frames["monitor"] = MonitorFrame(self.tabs.tab("Monitor"), self)

        for frm in self.frames.values():
            frm.pack(fill="both", expand=True, padx=15, pady=15)

        # ===========================
        # 3) CONSOLE
        # ===========================
        self.console_frame = ctk.CTkFrame(self, height=250, fg_color="#111")
        self.console_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))

        header = ctk.CTkFrame(self.console_frame, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=5)

        self.console_label = ctk.CTkLabel(header, text="SYSTEM OUTPUT", font=("Arial", 12, "bold"))
        self.console_label.pack(side="left", padx=5)

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")

        # In the console_frame section of main_app.py (around line 130-150), replace:
        # -------------------------------

        # Global Buttons - Reports / Logs
        # -------------------------------
        self.btn_dbc = ctk.CTkButton(btn_frame, text="📂 Import DBC (Global)", width=140, fg_color="#8e44ad",
                    command=self.load_global_dbc)
        self.btn_dbc.pack(side="left", padx=5)

        # Dropdown button for all report formats
        self.export_menu = ctk.CTkOptionMenu(
            btn_frame,   # ✅ CORRECT FRAME
            width=240,
            fg_color="#2980b9",
            values=[
                "Overall Report",
                "Failure Report",
                "Save Logs (.log)",
                "Export Logs (.asc)",
                "Export Logs (.mf4)"
            ],
            command=self.handle_export_selection
        )
        self.export_menu.set("Export")
        self.export_menu.pack(side="left", padx=5)


        # STOP button
        self.btn_stop = ctk.CTkButton(btn_frame, text="⛔ STOP", fg_color="#c0392b", width=100,
                    command=self.stop_process)
        self.btn_stop.pack(side="left", padx=5)

        # Debug & Failure Cases buttons
        self.btn_debug = ctk.CTkButton(btn_frame, text="🐛 Debug", width=80, fg_color="#8e44ad",
                    command=self.debug_failure_cases)
        self.btn_debug.pack(side="left", padx=5)

        self.btn_failure_cases = ctk.CTkButton(btn_frame, text="📊 View Failures", width=140, fg_color="#e74c3c",
                    command=self.show_failure_cases)
        self.btn_failure_cases.pack(side="left", padx=5)


        self.console = ctk.CTkTextbox(self.console_frame, font=("Consolas", 12), text_color="#00ff00", fg_color="#000")
        self.console.pack(fill="both", expand=True, padx=5, pady=5)

        # NEW: Flush pending console messages now that console is ready
        self._flush_pending_console_messages()

        # Bind main window resize to update all frames
        self.bind("<Configure>", self._on_main_resize)
        self._last_resize_time = 0
    
    def _flush_pending_console_messages(self):
        """Write any pending console messages that were stored before console was ready"""
        if hasattr(self, 'pending_console_messages') and self.pending_console_messages:
            for message in self.pending_console_messages:
                self.full_log_buffer.append(message)
                self.console.insert("end", message)
            self.console.see("end")
            # Clear the pending messages
            self.pending_console_messages.clear()

    def _setup_scrollable_frame(self, parent):
        """Setup a scrollable frame with mouse wheel support"""
        # Create the scrollable frame
        frame = ctk.CTkScrollableFrame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Get the canvas (it's a private attribute but we need it for mouse wheel)
        canvas = frame._parent_canvas
        
        # Function to handle mouse wheel
        def _on_mousewheel(event):
            # For Windows/MacOS with mouse wheel
            if event.num == 5 or event.delta == -120:
                canvas.yview_scroll(1, "units")
            if event.num == 4 or event.delta == 120:
                canvas.yview_scroll(-1, "units")
        
        # Function to handle mouse wheel on Linux
        def _on_mousewheel_linux(event):
            if event.num == 5:
                canvas.yview_scroll(1, "units")
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
        
        # Bind mouse wheel events
        def _bind_mousewheel(event):
            # Bind for Windows/MacOS
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            # Bind for Linux (Button-4 and Button-5)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)
        
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
        
        # Bind enter/leave events to manage mouse wheel binding
        frame._parent_canvas.bind("<Enter>", _bind_mousewheel)
        frame._parent_canvas.bind("<Leave>", _unbind_mousewheel)
    
        return frame

    def _on_main_resize(self, event=None):
        # Throttle resize events to prevent excessive updates
        current_time = time.time()
        if current_time - self._last_resize_time > 0.1:  # 100ms throttle
            self._last_resize_time = current_time

            # Check if window still exists
            if not self.winfo_exists():
                return

            try:
                # 1. Update Global Tab Scaling
                self._update_app_scaling()

                # 2. Update all frames
                for frame in self.frames.values():
                    if hasattr(frame, 'update_scaling') and frame.winfo_exists():
                        frame.update_scaling()
            except Exception as e:
                # Ignore resize errors during window destruction
                if "invalid command name" not in str(e) and "has been destroyed" not in str(e):
                    print(f"Resize error: {e}")



    # Update the _update_app_scaling method:
    def _update_app_scaling(self):
        """Scales the TabView text based on window size with increased font sizes"""
        try:
            # Check if window is being destroyed
            if not self.winfo_exists():
                return

            current_width = self.winfo_width()
            current_height = self.winfo_height()

            if current_width < 100 or current_height < 100:
                return

            # Calculate scale factor
            scale_factor = min(current_width / self.base_width, current_height / self.base_height)
            
            # Calculate Font Sizes using FontConfig
            tab_font = FontConfig.get_tab_font(scale_factor)
            console_font = FontConfig.get_console_font(scale_factor)
            console_header_font = FontConfig.get_console_header_font(scale_factor)
            
            # Apply Tab Font
            if hasattr(self.tabs, '_segmented_button') and self.tabs._segmented_button.winfo_exists():
                self.tabs._segmented_button.configure(font=tab_font)
            
            # Scale Console
            if self.console_label.winfo_exists():
                self.console_label.configure(font=console_header_font)
            
            # Update console text font
            if hasattr(self, 'console') and self.console.winfo_exists():
                self.console.configure(font=console_font)
            
            # Update UI fonts on console buttons
            self._update_ui_fonts(scale_factor)

        except Exception as e:
            if "invalid command name" in str(e) or "has been destroyed" in str(e):
                pass
            else:
                print(f"Scaling error: {e}")

    # Add this helper method if not already present:
    def _update_ui_fonts(self, scale_factor):
        """Update fonts on UI elements in console frame"""
        try:
            ui_font = FontConfig.get_button_font(scale_factor)
            small_ui_font = FontConfig.get_button_font(scale_factor * 0.9)
            
            # Update buttons in console header
            for widget in self.console_frame.winfo_children():
                if isinstance(widget, ctk.CTkFrame):
                    for child in widget.winfo_children():
                        if isinstance(child, (ctk.CTkButton, ctk.CTkOptionMenu)):
                            # Keep existing weight/style, just update size
                            current_font = child.cget("font")
                            if isinstance(current_font, tuple):
                                if len(current_font) == 3:
                                    # Has weight attribute (e.g., bold)
                                    child.configure(font=(current_font[0], ui_font[1], current_font[2]))
                                else:
                                    child.configure(font=ui_font)
        except Exception as e:
            pass  # Ignore font update errors

    def safe_destroy(self):
        """Safely destroy the application without cleanup errors"""
        try:
            # Stop any running processes first
            if self.current_process:
                self.stop_process()

            # Unbind events to prevent callbacks during destruction
            self.unbind("<Configure>")

            # Save failure cases before exiting
            self.save_failure_cases_to_file()

            # Destroy the application
            self.destroy()
        except Exception as e:
            # Force exit if there are any destruction errors
            import os
            os._exit(0)

    # =======================================
    # GLOBAL DBC LOGIC
    # =======================================
    def load_global_dbc(self):
        if not cantools:
            messagebox.showerror("Error", "Python 'cantools' library missing.\nRun: pip install cantools")
            return

        fp = filedialog.askopenfilename(filetypes=[("DBC files", "*.dbc"), ("All", "*.*")])
        if not fp: return

        try:
            self.dbc_db = cantools.database.load_file(fp)
            self.dbc_messages = {msg.name: msg.frame_id for msg in self.dbc_db.messages}

            msg_count = len(self.dbc_messages)
            self._console_write(f"[INFO] Loaded DBC: {os.path.basename(fp)} ({msg_count} messages)\n")
            self.refresh_tab_dropdowns()

        except Exception as e:
            self._console_write(f"[ERROR] Failed to load DBC: {e}\n")

            # Add these methods to the FucyfuzzApp class:

    def _save_overall_report_dialog(self):
        """Show dialog to select format for overall report"""
        format_dialog = ctk.CTkInputDialog(
            text="Select overall report format:\n1. PDF (Recommended)\n2. Text (Simple)\n\nEnter 1 or 2:",
            title="Report Format"
        )
        format_choice = format_dialog.get_input()
        
        if format_choice == "1":
            self.save_overall_report()  # This already handles PDF format
        elif format_choice == "2":
            self._save_overall_text_report()
        
        self.btn_reports_dropdown.set("📊 Export Reports")

    def _save_overall_text_report(self):
        """Save overall report as text file"""
        if not self.session_history:
            messagebox.showinfo("Info", "No history to report.")
            return

        fn = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt")],
            initialfile=f"FucyFuzz_Overall_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if fn:
            title = "FucyFuzz Overall Security Report"
            self.save_txt_report(fn, title, self.session_history)

    # Add this method to the FucyfuzzApp class in main_app.py:

    def handle_export_selection(self, choice):
        if choice == "Overall Report":
            self.show_overall_report_dialog()

        elif choice == "Failure Report":
            self.save_failure_report()

        elif choice == "Save Logs (.log)":
            self.save_full_logs()

        elif choice == "Export Logs (.asc)":
            self.export_logs_asc()

        elif choice == "Export Logs (.mf4)":
            self.export_logs_mf4()

        self.export_menu.set("Export")

    def show_overall_report_dialog(self):
        # Create modal window
        top = ctk.CTkToplevel(self)
        top.title("Overall Report Format")
        top.geometry("400x300")
        top.attributes("-topmost", True)
        top.grab_set()
        top.focus_set()

        ctk.CTkLabel(
            top,
            text="Select Overall Report Format",
            font=("Arial", 16, "bold")
        ).pack(pady=20)

        # Variable for radio selection
        format_var = ctk.StringVar(value="1")

        # Radio buttons
        radio_frame = ctk.CTkFrame(top)
        radio_frame.pack(pady=10)

        ctk.CTkRadioButton(
            radio_frame, text="📄 PDF (Professional Report)", variable=format_var, value="1"
        ).pack(anchor="w", pady=5)

        ctk.CTkRadioButton(
            radio_frame, text="📊 ASC (Vector Log)", variable=format_var, value="2"
        ).pack(anchor="w", pady=5)

        ctk.CTkRadioButton(
            radio_frame, text="📈 MDF4 (ASAM MDF)", variable=format_var, value="3"
        ).pack(anchor="w", pady=5)

        # Actions
        def on_submit():
            choice = format_var.get()
            top.destroy()

            if choice == "1":
                self.pdf_generator.generate_pdf(entries=self.session_history)

            elif choice == "2":
                self.pdf_generator.export_report_to_asc(entries=self.session_history)

            elif choice == "3":
                self.pdf_generator.export_report_to_mf4(entries=self.session_history)

        ctk.CTkButton(
            top,
            text="Generate",
            fg_color="#27ae60",
            width=120,
            command=on_submit
        ).pack(pady=15)

        ctk.CTkButton(
            top,
            text="Cancel",
            fg_color="#c0392b",
            width=120,
            command=top.destroy
        ).pack()

    
    def _export_logs_asc(self):
        # Prepare default filename via filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".asc",
            filetypes=[("Vector ASC", "*.asc")],
            initialfile=f"fucyfuzz_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.asc"
        )
        if not filename:
            return
        # Ensure exporter exists
        if not hasattr(self, 'log_exporter'):
            from report_generators import attach_report_capabilities
            attach_report_capabilities(self)
        result = self.log_exporter.export_logs_to_asc(filename=filename, logs=getattr(self, 'raw_logs', []))
        if result:
            messagebox.showinfo("Export Complete", f"ASC exported: {result}")
        self.btn_reports_dropdown.set("📊 Export Reports")

    def _export_logs_mf4(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".mf4",
            filetypes=[("MDF4 File", "*.mf4")],
            initialfile=f"fucyfuzz_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mf4"
        )
        if not filename:
            return
        if not hasattr(self, 'log_exporter'):
            from report_generators import attach_report_capabilities
            attach_report_capabilities(self)
        result = self.log_exporter.export_logs_to_mf4(filename=filename, logs=getattr(self, 'raw_logs', []))
        if result:
            messagebox.showinfo("Export Complete", f"MDF4 exported: {result}")
        self.btn_reports_dropdown.set("📊 Export Reports")

    def refresh_tab_dropdowns(self):
        msg_names = sorted(list(self.dbc_messages.keys()))
        if not msg_names: return

        for tab_name in ["fuzzer", "lenattack", "send", "uds","dcm"]:
            if hasattr(self.frames[tab_name], "update_msg_list"):
                self.frames[tab_name].update_msg_list(msg_names)

    def get_id_by_name(self, name):
        if name in self.dbc_messages:
            return hex(self.dbc_messages[name])
        return ""

    # =======================================
    # HELP MODAL LOGIC
    # =======================================
    def show_module_help(self, module_names):
        if isinstance(module_names, str):
            module_names = [module_names]

        full_output = ""

        for mod in module_names:
            full_output += f"=== HELP: {mod.upper()} ===\n"

            cmd = [sys.executable, "-m", "fucyfuzz.fucyfuzz", mod, "--help"]
            full_output += f"Command: {' '.join(cmd)}\n\n"

            try:
                env = os.environ.copy()
                env["PYTHONPATH"] = self.working_dir + os.pathsep + env.get("PYTHONPATH", "")

                output = subprocess.check_output(
                    cmd,
                    env=env,
                    stderr=subprocess.STDOUT,
                    cwd=self.working_dir,
                    text=True,
                    timeout=10
                )
                full_output += output

            except subprocess.CalledProcessError as e:
                full_output += f"Process returned error but here's the output:\n{e.output}"
            except subprocess.TimeoutExpired:
                full_output += f"Timeout: Help command took too long to execute\n"
            except FileNotFoundError:
                full_output += f"Error: Cannot find Python or fucyfuzz module\n"
            except Exception as e:
                full_output += f"Execution error: {str(e)}\n"

            full_output += "\n" + "-"*60 + "\n\n"

         # Create Modal Window
        top = ctk.CTkToplevel(self)
        top.title("Module Help")
        top.geometry("900x700")
        top.attributes("-topmost", True)
        top.focus_set()
        top.grab_set()

        ctk.CTkLabel(top, text="Module Documentation", font=("Arial", 20, "bold")).pack(pady=10)
        
        # Create a main frame
        main_frame = ctk.CTkFrame(top)
        main_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Create scrollable frame
        scroll_frame = self._setup_scrollable_frame(main_frame)
        
        # Textbox inside scrollable frame
        textbox = ctk.CTkTextbox(scroll_frame, font=("Consolas", 12))
        textbox.pack(fill="both", expand=True)
        textbox.insert("0.0", full_output)
        textbox.configure(state="disabled")
        
        # Close button outside scrollable frame
        button_frame = ctk.CTkFrame(top)
        button_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkButton(button_frame, text="Close", command=top.destroy, fg_color="#c0392b").pack(pady=5)


    # =======================================
    # MODULE EXECUTION WITH SUCCESS/FAIL TRACKING
    # =======================================
    def run_command(self, args_list, module_name="General"):
        """Run command with success/failure tracking"""
        return self.module_runner.run_command(args_list, module_name)

    def stop_process(self):
        """Stop current process"""
        if self.current_process:
            try:
                if os.name == 'nt':
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.current_process.pid)])
                else:
                    os.kill(self.current_process.pid, signal.SIGTERM)
            except: pass
            self.current_process = None
            self._console_write("\n[Process Stopped by User]\n")

    def _console_write(self, text):
        """Write to console with thread safety"""
        self.full_log_buffer.append(text)
        if hasattr(self, 'console') and self.console.winfo_exists():
            self.console.after(0, lambda: (self.console.insert("end", text), self.console.see("end")))
        else:
            if not hasattr(self, 'pending_console_messages'):
                self.pending_console_messages = []
            self.pending_console_messages.append(text)

    # =======================================
    # FAILURE CASES MANAGEMENT
    # =======================================

    def debug_failure_cases(self):
        """Debug method to check failure cases"""
        print(f"\n=== DEBUG: Failure Cases ===")
        print(f"Total modules with failures: {len(self.failure_cases)}")
        
        for module_name, failures in self.failure_cases.items():
            print(f"\nModule: {module_name}")
            print(f"  Number of failures: {len(failures)}")
            for i, failure in enumerate(failures[:3]):  # Show first 3
                print(f"  Failure {i+1}:")
                print(f"    Timestamp: {failure.get('timestamp', 'N/A')}")
                print(f"    Command: {failure.get('command', 'N/A')[:50]}...")
                print(f"    Status: {failure.get('status', 'N/A')}")
            if len(failures) > 3:
                print(f"  ... and {len(failures) - 3} more")
        
        print("=== END DEBUG ===\n")

    def add_failure_case(self, module_name, entry):
        """Add a failure case to the module's failure list"""
        if module_name not in self.failure_cases:
            self.failure_cases[module_name] = []
        
        # Check if this failure is already recorded
        for existing in self.failure_cases[module_name]:
            if (existing.get('timestamp') == entry.get('timestamp') and 
                existing.get('command') == entry.get('command')):
                print(f"[DEBUG] Duplicate failure case for {module_name}")
                return  # Already exists
        
        # Add the failure case
        self.failure_cases[module_name].append(entry)
        print(f"[DEBUG] Added failure case for {module_name}. Total: {len(self.failure_cases[module_name])}")
        
        # Save to file
        self.save_failure_cases_to_file()


        
    def get_failure_cases(self, module_name=None):
        """Get failure cases, optionally filtered by module"""
        if module_name:
            return self.failure_cases.get(module_name, [])
        else:
            # Return all failures across all modules
            all_failures = []
            for module, failures in self.failure_cases.items():
                all_failures.extend(failures)
            return all_failures

    def clear_failure_cases(self, module_name=None):
        """Clear failure cases, optionally for specific module"""
        if module_name:
            if module_name in self.failure_cases:
                self.failure_cases[module_name] = []
                self._console_write(f"[INFO] Cleared failure cases for {module_name}\n")
        else:
            self.failure_cases = {}
            self._console_write("[INFO] Cleared all failure cases\n")
        
        self.save_failure_cases_to_file()

    def save_failure_cases_to_file(self):
        """Save failure cases to JSON file"""
        try:
            failures_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failure_cases")
            if not os.path.exists(failures_dir):
                os.makedirs(failures_dir)
            
            filename = os.path.join(failures_dir, "failure_cases.json")
            
            # Convert to serializable format
            serializable_failures = {}
            for module, entries in self.failure_cases.items():
                serializable_failures[module] = entries
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_failures, f, indent=2, default=str)
            
        except Exception as e:
            print(f"Error saving failure cases: {e}")

    def load_failure_cases_from_file(self):
        """Load failure cases from JSON file"""
        try:
            filename = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                "failure_cases", 
                "failure_cases.json"
            )
            
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    self.failure_cases = json.load(f)
                self._console_write(f"[INFO] Loaded {sum(len(f) for f in self.failure_cases.values())} failure cases\n")
                return True
        except Exception as e:
            print(f"Error loading failure cases: {e}")
        return False

    def show_failure_cases(self):
        """Show dialog with failure cases"""
        print(f"[DEBUG] show_failure_cases called. Total modules: {len(self.failure_cases)}")
        
        # Count total failures
        total_failures = 0
        for module, failures in self.failure_cases.items():
            print(f"[DEBUG] Module {module}: {len(failures)} failures")
            total_failures += len(failures)
        
        if total_failures == 0:
            messagebox.showinfo("No Failures", "No failure cases recorded yet.")
            return
        
        # Create dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Failure Cases Management")
        dialog.geometry("900x700")
        dialog.attributes("-topmost", True)
        
        # ✅ Force window to be created & mapped
        dialog.update_idletasks()
        dialog.deiconify()
        
        # ✅ NOW grab works
        dialog.grab_set()
        
        # Header
        header = ctk.CTkFrame(dialog, fg_color="#c0392b")
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text="📊 FAILURE CASES MANAGEMENT", 
                    font=("Arial", 18, "bold"), text_color="white").pack(pady=5)
        
        ctk.CTkLabel(header, text=f"Total Failure Cases: {total_failures}", 
                    font=("Arial", 12), text_color="white").pack()
        
        # Content
        content = ctk.CTkFrame(dialog)
        content.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Create notebook for different modules
        tabs = ctk.CTkTabview(content)
        tabs.pack(fill="both", expand=True)
        
        # Add tabs for each module with failures
        for module_name, failures in self.failure_cases.items():
            if failures:
                tabs.add(module_name)
        
        # Now populate each tab
        for module_name, failures in self.failure_cases.items():
            if failures:
                tab = tabs.tab(module_name)  # Get the tab by name
                
                # Module header
                header_frame = ctk.CTkFrame(tab, fg_color="#2c3e50")
                header_frame.pack(fill="x", padx=5, pady=5)
                
                ctk.CTkLabel(header_frame, text=f"{module_name} - {len(failures)} failures", 
                        font=("Arial", 14, "bold"), text_color="white").pack(pady=5)
                
                # Use scrollable frame with mouse wheel support
                frame = self._setup_scrollable_frame(tab)
                
                for idx, failure in enumerate(failures):
                    failure_frame = ctk.CTkFrame(frame, fg_color="#34495e", corner_radius=8)
                    failure_frame.pack(fill="x", pady=5, padx=5)
                    
                    # Failure info
                    info_frame = ctk.CTkFrame(failure_frame, fg_color="transparent")
                    info_frame.pack(fill="x", padx=10, pady=10)
                    
                    # Show basic info
                    timestamp = failure.get('timestamp', 'Unknown time')
                    status = failure.get('status', 'Failure')
                    command_preview = failure.get('command', 'No command')
                    if len(command_preview) > 80:
                        command_preview = command_preview[:80] + "..."
                    
                    # Get case details if available
                    case_details = failure.get('case_details', {})
                    error_type = case_details.get('error_type', 'Unknown error')
                    message = case_details.get('message', 'No details')
                    
                    info_text = f"Failure {idx + 1}:\n"
                    info_text += f"  Time: {timestamp}\n"
                    info_text += f"  Status: {status}\n"
                    info_text += f"  Error: {error_type}\n"
                    info_text += f"  Details: {message[:60]}..." if len(message) > 60 else f"  Details: {message}"
                    
                    ctk.CTkLabel(info_frame, text=info_text, 
                            font=("Consolas", 10), justify="left").pack(anchor="w")
                    
                    # Action buttons
                    btn_frame = ctk.CTkFrame(failure_frame, fg_color="transparent")
                    btn_frame.pack(fill="x", padx=10, pady=(0, 10))
                    
                    # Re-run button
                    ctk.CTkButton(btn_frame, text="Re-run", width=100,
                                command=lambda f=failure, m=module_name, d=dialog: 
                                self._re_run_failure_case(f, m, d)).pack(side="left", padx=2)
                    
                    # View Details button
                    ctk.CTkButton(btn_frame, text="Details", width=100, fg_color="#3498db",
                                command=lambda f=failure, m=module_name: 
                                self._show_failure_details(f, m)).pack(side="left", padx=2)
                    
                    # Delete button
                    ctk.CTkButton(btn_frame, text="Delete", width=100, fg_color="#c0392b",
                                command=lambda f=failure, m=module_name, d=dialog: 
                                self._delete_failure_case(f, m, d)).pack(side="left", padx=2)
        
        # Global actions
        action_frame = ctk.CTkFrame(dialog)
        action_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkButton(action_frame, text="Export All to CSV", fg_color="#2980b9",
                    command=lambda: self._export_failure_cases_csv(dialog)).pack(side="left", padx=5)
        ctk.CTkButton(action_frame, text="Clear All", fg_color="#c0392b",
                    command=lambda: self._clear_all_failure_cases(dialog)).pack(side="left", padx=5)
        ctk.CTkButton(action_frame, text="Close",
                    command=dialog.destroy).pack(side="right", padx=5)
        
        # FIXED: Update the dialog to ensure tabs are visible
        dialog.update()


    def _re_run_failure_case(self, failure, module_name, dialog):
        """Re-run a specific failure case"""
        # Extract command from failure entry
        command = failure.get('command', '')
        if not command:
            messagebox.showerror("Error", "No command found in failure case")
            return
        
        # Parse command to get arguments
        parts = command.split()
        
        # Find the module executable part
        args = []
        found_module = False
        
        for i, part in enumerate(parts):
            if part in ["python", sys.executable]:
                continue
            elif part == "-m" and i + 1 < len(parts) and parts[i + 1] == "fucyfuzz.fucyfuzz":
                continue
            elif part == "fucyfuzz.fucyfuzz":
                continue
            elif part in ["lenattack", "fuzzer", "dcm", "uds", "send", "recon", "listener", "doip", "xcp"]:
                found_module = True
                args = parts[i:]  # Take everything from module name onward
                break
        
        if not args:
            # Try to extract from case_details
            if 'case_details' in failure and 'id' in failure['case_details']:
                target_id = failure['case_details']['id']
                if module_name in ["LengthAttack", "lenattack"]:
                    args = ["lenattack", target_id, "-i", "vcan0"]
                elif module_name in ["Fuzzer", "fuzzer"]:
                    args = ["fuzzer", "mutate", target_id]
        
        if args:
            self.run_command(args, module_name)
            dialog.destroy()
            messagebox.showinfo("Re-running", f"Re-running failure case for {module_name}")
        else:
            messagebox.showerror("Error", f"Could not parse command for {module_name}")
    
    def _show_failure_details(self, failure, module_name):
        """Show detailed information about a failure"""
        details_dialog = ctk.CTkToplevel(self)
        details_dialog.title(f"Failure Details - {module_name}")
        details_dialog.geometry("800x600")
        details_dialog.attributes("-topmost", True)
        
        # Wait for the window to be created before grabbing
        details_dialog.update_idletasks()
        details_dialog.deiconify()
        
        # Now it's safe to grab
        details_dialog.grab_set()
        details_dialog.focus_set()  # Ensure focus is on this dialog
        
        # Header
        header = ctk.CTkFrame(details_dialog, fg_color="#c0392b")
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text="📋 FAILURE DETAILS", 
                    font=("Arial", 16, "bold"), text_color="white").pack(pady=5)
        
        # Content frame with scroll
        content_frame = self._setup_scrollable_frame(details_dialog)
        
        # Show all failure information
        info_text = f"Module: {module_name}\n\n"
        for key, value in failure.items():
            if key == 'case_details' and isinstance(value, dict):
                info_text += f"\n📊 Case Details:\n"
                for sub_key, sub_value in value.items():
                    info_text += f"  {sub_key}: {sub_value}\n"
            elif key != 'output' and key != 'case_details':
                info_text += f"{key}: {value}\n"
        
        ctk.CTkLabel(content_frame, text=info_text, 
                    font=("Consolas", 11), justify="left").pack(anchor="w", padx=10, pady=10)
        
        # Show output if available
        if 'output' in failure and failure['output']:
            output_frame = ctk.CTkFrame(content_frame)
            output_frame.pack(fill="x", padx=10, pady=10)
            
            ctk.CTkLabel(output_frame, text="Output:", 
                        font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 5))
            
            output_text = ctk.CTkTextbox(output_frame, height=150, font=("Consolas", 10))
            output_text.pack(fill="x", padx=5, pady=5)
            output_text.insert("1.0", failure['output'][:2000])  # Limit output length
            output_text.configure(state="disabled")
        
        # Close button - placed outside the scrollable frame
        # Create a separate frame for the button
        button_frame = ctk.CTkFrame(details_dialog)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # Use lambda to ensure the dialog is properly destroyed
        close_button = ctk.CTkButton(
            button_frame, 
            text="Close", 
            command=lambda: details_dialog.destroy()
        )
        close_button.pack(pady=10)
        
        # Bind Escape key to close
        details_dialog.bind("<Escape>", lambda e: details_dialog.destroy())

    def _delete_failure_case(self, failure, module_name, dialog):
        """Delete a specific failure case"""
        # Confirm deletion
        response = messagebox.askyesno("Confirm", 
                                      "Delete this failure case?")
        if not response:
            return
        
        # Remove from failure cases
        if module_name in self.failure_cases:
            self.failure_cases[module_name] = [
                f for f in self.failure_cases[module_name] 
                if not (f.get('timestamp') == failure.get('timestamp') and 
                       f.get('command') == failure.get('command'))
            ]
            
            # Remove empty module entries
            if not self.failure_cases[module_name]:
                del self.failure_cases[module_name]
        
        # Save to file
        self.save_failure_cases_to_file()
        
        # Refresh dialog
        dialog.destroy()
        self.show_failure_cases()
    
    def _re_run_all_failures(self, dialog):
        """Re-run all failure cases"""
        all_failures = self.get_failure_cases()
        if not all_failures:
            messagebox.showinfo("Info", "No failure cases to re-run")
            return
        
        response = messagebox.askyesno("Confirm", 
                                      f"Re-run {len(all_failures)} failure cases?")
        if response:
            dialog.destroy()
            for failure in all_failures:
                module_name = failure['module']
                self._re_run_failure_case(failure, module_name, None)
                time.sleep(1)  # Small delay between runs
    
    def _export_failure_cases_csv(self, dialog):
        """Export failure cases to CSV"""
        all_failures = self.get_failure_cases()
        if not all_failures:
            messagebox.showinfo("Info", "No failure cases to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="failure_cases_export.csv"
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        'timestamp', 'module', 'status', 'command', 'output_preview'
                    ])
                    writer.writeheader()
                    
                    for failure in all_failures:
                        writer.writerow({
                            'timestamp': failure.get('timestamp', ''),
                            'module': failure.get('module', ''),
                            'status': failure.get('status', ''),
                            'command': failure.get('command', '')[:200],
                            'output_preview': failure.get('output', '')[:500].replace('\n', ' ')
                        })
                
                messagebox.showinfo("Success", f"Exported {len(all_failures)} failure cases to {filename}")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def _clear_all_failure_cases(self, dialog):
        """Clear all failure cases"""
        response = messagebox.askyesno("Confirm", 
                                      "Clear all failure cases? This cannot be undone.")
        if response:
            self.clear_failure_cases()
            dialog.destroy()
            messagebox.showinfo("Cleared", "All failure cases have been cleared")

    # =======================================
    # ENHANCED REPORTING METHODS
    # =======================================
    def generate_pdf(self, filename, title, entries):
        """Use the enhanced PDF generator - UPDATED"""
        # Check if filename was provided
        if filename and filename != filedialog.asksaveasfilename:
            # Use the pdf_generator's generate_pdf method
            return self.pdf_generator.generate_pdf(filename, title, entries)
        else:
            # User cancelled the dialog
            self.btn_reports_dropdown.set("📊 Export Reports")
            return None

    # In the EnhancedPDFReport class in report_generators.py, add this method:

    def save_txt_report(self, filename=None, title="FucyFuzz Security Report", entries=None):
        """Save overall report as text file"""
        if entries is None:
            entries = getattr(self.app, 'session_history', [])
        
        if filename is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(os.getcwd(), f"FucyFuzz_Report_{stamp}.txt")
        
        try:
            modules, status_counts, risk_scorecard, key_findings = self._analyze_entries(entries)
            
            with open(filename, 'w', encoding='utf-8') as f:
                # Header
                f.write("=" * 80 + "\n")
                f.write(f"{title.center(80)}\n")
                f.write("=" * 80 + "\n\n")
                
                # Summary
                f.write("EXECUTIVE SUMMARY\n")
                f.write("-" * 40 + "\n")
                f.write(f"Total Tests: {len(entries)}\n")
                f.write(f"Modules Tested: {len(modules)}\n")
                f.write(f"Success: {status_counts.get('success', 0)}\n")
                f.write(f"Warnings: {status_counts.get('warning', 0)}\n")
                f.write(f"Failures: {status_counts.get('failed', 0)}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Risk Scorecard
                f.write("RISK SCORECARD\n")
                f.write("-" * 40 + "\n")
                f.write(f"{'Metric':<30} {'Status':<15} {'Risk Level'}\n")
                f.write("-" * 40 + "\n")
                for metric, status, risk_level in risk_scorecard:
                    f.write(f"{metric:<30} {status:<15} {risk_level}\n")
                f.write("\n")
                
                # Key Findings
                f.write("KEY FINDINGS\n")
                f.write("-" * 40 + "\n")
                for finding in key_findings:
                    f.write(f"• {finding}\n")
                f.write("\n")
                
                # Detailed Report
                f.write("DETAILED TECHNICAL REPORT\n")
                f.write("=" * 80 + "\n\n")
                
                for module_idx, (module_name, module_entries) in enumerate(modules.items()):
                    f.write(f"MODULE {module_idx + 1}: {module_name}\n")
                    f.write("-" * 40 + "\n")
                    
                    mod_success = sum(1 for e in module_entries if 'success' in e.get('status', '').lower())
                    mod_total = len(module_entries)
                    success_rate = (mod_success / mod_total * 100) if mod_total else 0
                    f.write(f"Success Rate: {mod_success}/{mod_total} ({success_rate:.1f}%)\n\n")
                    
                    for test_idx, entry in enumerate(module_entries, start=1):
                        f.write(f"Test {test_idx}:\n")
                        f.write(f"  Timestamp: {entry.get('timestamp', 'N/A')}\n")
                        f.write(f"  Status: {entry.get('status', 'N/A')}\n")
                        f.write(f"  Command: {entry.get('command', 'N/A')}\n")
                        
                        output_text = entry.get('output', '') or ''
                        if output_text:
                            f.write(f"  Output (truncated):\n")
                            lines = output_text.split('\n')
                            for line in lines[:10]:  # Show first 10 lines
                                f.write(f"    {line}\n")
                            if len(lines) > 10:
                                f.write(f"    ... [output truncated, {len(lines) - 10} more lines]\n")
                        f.write("\n")
                    
                    f.write("\n")
            
            messagebox.showinfo("Text Report", f"Text report saved to:\n{filename}")
            return filename
            
        except Exception as e:
            messagebox.showerror("Text Report Error", f"Failed to save text report:\n{str(e)}")
            return None

        # Replace the existing save_overall_report method with this:

        # In the main_app.py file, replace the save_overall_report method:

    def save_overall_report(self):
        """Save overall report with multiple format options (PDF, Text, ASC, MDF4)"""
        if not self.session_history:
            messagebox.showinfo("Info", "No history to report.")
            self.btn_reports_dropdown.set("📊 Export Reports")
            return
        
        # Create format selection dialog
        top = ctk.CTkToplevel(self)
        top.title("Select Report Format")
        top.geometry("400x350")
        top.attributes("-topmost", True)
        # Wait then grab
        top.update_idletasks()
        top.deiconify()
        top.grab_set()
        
        # Make the dialog focus
        top.focus_set()
        
        # Main container
        main_container = ctk.CTkFrame(top)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_container, 
            text="Select Overall Report Format", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Format buttons frame
        btn_frame = ctk.CTkFrame(main_container)
        btn_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        def on_format_selected(format_type):
            top.destroy()
            
            if format_type == "pdf":
                self._save_overall_pdf()
            elif format_type == "text":
                self._save_overall_text()
            elif format_type == "asc":
                self._save_overall_asc()
            elif format_type == "mf4":
                self._save_overall_mf4()
            
            # Reset dropdown
            self.btn_reports_dropdown.set("📊 Export Reports")

        
        # PDF Button
        btn_pdf_format = ctk.CTkButton(
            btn_frame, 
            text="📄 PDF Report", 
            width=150, 
            height=40,
            fg_color="#2980b9",
            font=("Arial", 12),
            command=lambda: on_format_selected("pdf")
        )
        btn_pdf_format.pack(pady=8, padx=20)
        
        # Text Button
        btn_text_format = ctk.CTkButton(
            btn_frame, 
            text="📝 Text Report", 
            width=150, 
            height=40,
            fg_color="#16a085",
            font=("Arial", 12),
            command=lambda: on_format_selected("text")
        )
        btn_text_format.pack(pady=8, padx=20)
        
        # ASC Button
        btn_asc_format = ctk.CTkButton(
            btn_frame, 
            text="📊 ASC Report", 
            width=150, 
            height=40,
            fg_color="#8e44ad",
            font=("Arial", 12),
            command=lambda: on_format_selected("asc")
        )
        btn_asc_format.pack(pady=8, padx=20)
        
        # MDF4 Button
        btn_mf4_format = ctk.CTkButton(
            btn_frame, 
            text="📈 MDF4 Report", 
            width=150, 
            height=40,
            fg_color="#d35400",
            font=("Arial", 12),
            command=lambda: on_format_selected("mf4")
        )
        btn_mf4_format.pack(pady=8, padx=20)
        
        # Cancel Button Frame
        cancel_frame = ctk.CTkFrame(main_container)
        cancel_frame.pack(fill="x", pady=(10, 0))
        
        btn_cancel = ctk.CTkButton(
            cancel_frame, 
            text="Cancel", 
            width=100,
            height=30,
            command=lambda: [top.destroy(), self.btn_reports_dropdown.set("📊 Export Reports")]
        )
        btn_cancel.pack(pady=5)
        
        # Force update to ensure everything is visible
        top.update()


    def _save_overall_pdf(self):
        """Save overall report as PDF"""
        if REPORTLAB_AVAILABLE:
            # Get default filename
            default_name = f"FucyFuzz_Overall_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            # Ask for save location
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF Document", "*.pdf"), ("All files", "*.*")],
                initialfile=default_name
            )
            
            if filename:
                self.generate_pdf(filename, "FucyFuzz Overall Security Report", self.session_history)
        else:
            # Fallback to text if PDF not available
            messagebox.showwarning("PDF Unavailable", 
                                "ReportLab not installed. Generating text report instead.")
            self._save_overall_text()

    def _save_overall_text(self):
        """Save overall report as text file"""
        if not self.session_history:
            messagebox.showinfo("Info", "No history to report.")
            return
        
        # Ensure pdf_generator has the text report method
        if not hasattr(self.pdf_generator, 'save_txt_report'):
            from report_generators import EnhancedPDFReport
            self.pdf_generator = EnhancedPDFReport(self)
        
        # Get default filename
        default_name = f"FucyFuzz_Overall_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Ask for save location
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt")],
            initialfile=default_name
        )
        
        if filename:
            try:
                result = self.pdf_generator.save_txt_report(
                    filename=filename,
                    title="FucyFuzz Overall Security Report",
                    entries=self.session_history
                )
                if result:
                    messagebox.showinfo("Success", f"Overall text report saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save text report:\n{str(e)}")

    def _save_overall_asc(self):
        """Save overall report as ASC format"""
        if not self.session_history:
            messagebox.showinfo("Info", "No history to report.")
            self.btn_reports_dropdown.set("📊 Export Reports")
            return
        
        # Ensure pdf_generator has the export methods
        if not hasattr(self.pdf_generator, 'export_report_to_asc'):
            from report_generators import EnhancedPDFReport
            self.pdf_generator = EnhancedPDFReport(self)
        
        # Get default filename
        default_name = f"FucyFuzz_Overall_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.asc"
        
        # Ask for save location
        filename = filedialog.asksaveasfilename(
            defaultextension=".asc",
            filetypes=[("ASC Files", "*.asc"), ("All files", "*.*")],
            initialfile=default_name
        )
        
        if filename:
            try:
                result = self.pdf_generator.export_report_to_asc(
                    filename=filename,
                    title="FucyFuzz Overall Security Report",
                    entries=self.session_history
                )
                if result:
                    messagebox.showinfo("Success", f"Overall ASC report saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save ASC report:\n{str(e)}")

    def _save_overall_mf4(self):
        """Save overall report as MDF4 format"""
        if not self.session_history:
            messagebox.showinfo("Info", "No history to report.")
            self.btn_reports_dropdown.set("📊 Export Reports")
            return
        
        # Ensure pdf_generator has the export methods
        if not hasattr(self.pdf_generator, 'export_report_to_mf4'):
            from report_generators import EnhancedPDFReport
            self.pdf_generator = EnhancedPDFReport(self)
        
        # Get default filename
        default_name = f"FucyFuzz_Overall_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mf4"
        
        # Ask for save location
        filename = filedialog.asksaveasfilename(
            defaultextension=".mf4",
            filetypes=[("MDF4 Files", "*.mf4"), ("All files", "*.*")],
            initialfile=default_name
        )
        
        if filename:
            try:
                result = self.pdf_generator.export_report_to_mf4(
                    filename=filename,
                    title="FucyFuzz Overall Security Report",
                    entries=self.session_history
                )
                if result:
                    messagebox.showinfo("Success", f"Overall MDF4 report saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save MDF4 report:\n{str(e)}")

    def _save_overall_asc_report(self):
        """Save overall report as ASC format"""
        if not self.session_history:
            messagebox.showinfo("Info", "No history to report.")
            self.btn_reports_dropdown.set("📊 Export Reports")
            return
        
        # Ensure pdf_generator has the export methods
        if not hasattr(self.pdf_generator, 'export_report_to_asc'):
            from report_generators import EnhancedPDFReport
            self.pdf_generator = EnhancedPDFReport(self)
        
        # Get default filename
        default_name = f"FucyFuzz_Overall_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.asc"
        
        # Ask for save location
        filename = filedialog.asksaveasfilename(
            defaultextension=".asc",
            filetypes=[("ASC Files", "*.asc"), ("All files", "*.*")],
            initialfile=default_name
        )
        
        if filename:
            try:
                result = self.pdf_generator.export_report_to_asc(
                    filename=filename,
                    title="FucyFuzz Overall Security Report",
                    entries=self.session_history
                )
                if result:
                    messagebox.showinfo("Success", f"Overall ASC report saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save ASC report:\n{str(e)}")
        
        self.btn_reports_dropdown.set("📊 Export Reports")

    def _save_overall_mf4_report(self):
        """Save overall report as MDF4 format"""
        if not self.session_history:
            messagebox.showinfo("Info", "No history to report.")
            self.btn_reports_dropdown.set("📊 Export Reports")
            return
        
        # Ensure pdf_generator has the export methods
        if not hasattr(self.pdf_generator, 'export_report_to_mf4'):
            from report_generators import EnhancedPDFReport
            self.pdf_generator = EnhancedPDFReport(self)
        
        # Get default filename
        default_name = f"FucyFuzz_Overall_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mf4"
        
        # Ask for save location
        filename = filedialog.asksaveasfilename(
            defaultextension=".mf4",
            filetypes=[("MDF4 Files", "*.mf4"), ("All files", "*.*")],
            initialfile=default_name
        )
        
        if filename:
            try:
                result = self.pdf_generator.export_report_to_mf4(
                    filename=filename,
                    title="FucyFuzz Overall Security Report",
                    entries=self.session_history
                )
                if result:
                    messagebox.showinfo("Success", f"Overall MDF4 report saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save MDF4 report:\n{str(e)}")
        
        self.btn_reports_dropdown.set("📊 Export Reports")

    def save_module_report(self, mod):
        entries = [e for e in self.session_history if e['module'] == mod]
        if not entries:
            messagebox.showinfo("Info", f"No history for {mod}.")
            return

        if REPORTLAB_AVAILABLE:
            ext = ".pdf"
            ftypes = [("PDF Document", "*.pdf")]
        else:
            ext = ".txt"
            ftypes = [("Text File", "*.txt")]

        fn = filedialog.asksaveasfilename(
            initialfile=f"{mod}_Report{ext}",
            defaultextension=ext,
            filetypes=ftypes
        )

        if fn:
            title = f"{mod} Module Report"
            if ext == ".pdf":
                self.generate_pdf(fn, title, entries)
            else:
                self.save_txt_report(fn, title, entries)

    def save_full_logs(self):
        fn = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log File", "*.log"), ("Text File", "*.txt")]
        )
        if fn:
            try:
                with open(fn, "w", encoding='utf-8') as f:
                    f.writelines(self.full_log_buffer)
                messagebox.showinfo("Success", f"Logs saved to:\n{fn}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save logs: {str(e)}")
        self.btn_reports_dropdown.set("📊 Export Reports")

    # =======================================
    # FAILURE REPORT METHODS
    # =======================================
    # Modify the save_failure_report method in main_app.py to be simpler:

    def save_failure_report(self):
        """Generate and save failure analysis report with format selection"""
        if not self.session_history:
            messagebox.showinfo("Info", "No test history available.")
            return

        # Check if there are any failures
        failed_entries = self.failure_report.get_failure_entries()
        if not failed_entries:
            messagebox.showinfo("No Failures", "No failed test cases found in current session.")
            return

        # Create simple format selection dialog
        top = ctk.CTkToplevel(self)
        top.title("Select Failure Report Format")
        top.geometry("400x300")
        top.attributes("-topmost", True)
        top.update_idletasks()
        top.deiconify()
        top.grab_set()
        
        ctk.CTkLabel(top, text="Select Report Format", 
                    font=("Arial", 16, "bold")).pack(pady=20)
        
        # Format buttons
        btn_frame = ctk.CTkFrame(top)
        btn_frame.pack(expand=True, padx=20, pady=10)
        
        def on_format_selected(format_type):
            top.destroy()
            if format_type == "pdf":
                if REPORTLAB_AVAILABLE:
                    fn = filedialog.asksaveasfilename(
                        defaultextension=".pdf",
                        filetypes=[("PDF Document", "*.pdf")],
                        initialfile=f"Failure_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    )
                    if fn:
                        self.failure_report.generate_failure_report(fn, "Failure Analysis Report")
                else:
                    messagebox.showwarning("PDF Unavailable", 
                                        "ReportLab not installed. Generating text report instead.")
                    self._save_failure_text_report()
            
            elif format_type == "text":
                self._save_failure_text_report()
            
            elif format_type == "csv":
                self.failure_report.export_failures_csv()
            
            self.btn_reports_dropdown.set("📊 Export Reports")
        
        ctk.CTkButton(btn_frame, text="📄 PDF Report", width=150, fg_color="#2980b9",
                    command=lambda: on_format_selected("pdf")).pack(pady=10, padx=20)
        
        ctk.CTkButton(btn_frame, text="📝 Text Report", width=150, fg_color="#16a085",
                    command=lambda: on_format_selected("text")).pack(pady=10, padx=20)
        
        ctk.CTkButton(btn_frame, text="📊 CSV Export", width=150, fg_color="#8e44ad",
                    command=lambda: on_format_selected("csv")).pack(pady=10, padx=20)
        
        ctk.CTkButton(top, text="Cancel", width=100,
                    command=top.destroy).pack(pady=10)
        
    def _save_failure_text_report(self):
        """Save failure report as text file"""
        fn = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt")],
            initialfile=f"Failure_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if fn:
            self.failure_report.generate_failure_report(fn, "Failure Analysis Report")

    def show_failure_summary(self):
        """Show a quick summary of failures in a dialog"""
        failed_entries = self.failure_report.get_failure_entries()

        if not failed_entries:
            messagebox.showinfo("Failure Summary", "✅ No failures detected in current session.")
            return

        # Create summary dialog
        summary_dialog = ctk.CTkToplevel(self)
        summary_dialog.title("Failure Summary")
        summary_dialog.geometry("600x400")
        summary_dialog.attributes("-topmost", True)

        # Summary header
        header = ctk.CTkFrame(summary_dialog, fg_color="#c0392b")
        header.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(header, text="⚠️ FAILURE SUMMARY", font=("Arial", 18, "bold"),
                    text_color="white").pack(pady=10)

        # Summary content
        content_frame = ctk.CTkFrame(summary_dialog)
        content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Statistics
        stats_text = f"""
        Total Tests: {len(self.session_history)}
        Total Failures: {len(failed_entries)}
        Failure Rate: {(len(failed_entries)/len(self.session_history)*100):.1f}%

        Failed Modules:"""

        # Group by module
        modules = {}
        for entry in failed_entries:
            modules[entry['module']] = modules.get(entry['module'], 0) + 1

        for module, count in modules.items():
            stats_text += f"\n  • {module}: {count} failures"

        stats_label = ctk.CTkLabel(content_frame, text=stats_text, font=("Arial", 12),
                                 justify="left")
        stats_label.pack(pady=20, padx=20)

        # Action buttons
        btn_frame = ctk.CTkFrame(content_frame)
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="Generate Full Report", fg_color="#c0392b",
                     command=lambda: [summary_dialog.destroy(), self.save_failure_report()]).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="Export CSV", fg_color="#2980b9",
                     command=lambda: [summary_dialog.destroy(), self.failure_report.export_failures_csv()]).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="Close",
                     command=summary_dialog.destroy).pack(side="left", padx=5)

    def clear_failure_history(self):
        """Clear failure history from session"""
        self.failure_report.clear_failure_history()


if __name__ == "__main__":
    app = FucyfuzzApp()
    app.load_failure_cases_from_file()  # Load saved failure cases
    app.mainloop()