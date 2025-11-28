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

# --- OPTIONAL IMPORTS ---
try:
    import cantools
except ImportError:
    cantools = None

# PDF Generation Import
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# ==============================================================================
#   MAIN APP
# ==============================================================================

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
        self.pending_console_messages = []  # NEW: Store messages until console is ready
        
        # GLOBAL DBC STORE
        self.dbc_db = None
        self.dbc_messages = {}

        # --- INITIALIZE WORKING DIRECTORY ---
        # Automatically detect the correct path relative to current script location
        current_script_dir = os.path.dirname(os.path.abspath(__file__))

        # Navigate to the parent directory (FucyFuzz) then to fucyfuzz_tool
        parent_dir = os.path.dirname(current_script_dir)  # This goes up to FucyFuzz
        default_path = os.path.join(parent_dir, "fucyfuzz_tool")

        if os.path.exists(default_path):
            self.working_dir = default_path
            # Don't call _console_write yet - store the message
            self.pending_console_messages.append(f"[INFO] Auto-detected working directory: {self.working_dir}\n")
        else:
            # Fallback: try to find fucyfuzz_tool in various possible locations
            possible_paths = [
                default_path,  # ../fucyfuzz_tool from current script
                os.path.join(current_script_dir, "fucyfuzz_tool"),  # ./fucyfuzz_tool
                os.path.join(parent_dir, "..", "fucyfuzz_tool"),  # ../../fucyfuzz_tool
                os.path.join(os.getcwd(), "fucyfuzz_tool"),  # Current working directory
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    self.working_dir = path
                    self.pending_console_messages.append(f"[INFO] Found working directory: {self.working_dir}\n")
                    break
            else:
                # Final fallback
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
            "Configuration", "Recon","Demo", "Fuzzer", "Length Attack",
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

        # Global Buttons
        self.btn_dbc = ctk.CTkButton(btn_frame, text="📂 Import DBC (Global)", width=140, fg_color="#8e44ad",
                      command=self.load_global_dbc)
        self.btn_dbc.pack(side="left", padx=5)

        self.btn_pdf = ctk.CTkButton(btn_frame, text="📄 Overall PDF Report", width=140, fg_color="#2980b9",
                      command=self.save_overall_report)
        self.btn_pdf.pack(side="left", padx=5)
        
        self.btn_log = ctk.CTkButton(btn_frame, text="📜 Save Logs", width=100, fg_color="#7f8c8d",
                      command=self.save_full_logs)
        self.btn_log.pack(side="left", padx=5)

        self.btn_stop = ctk.CTkButton(btn_frame, text="⛔ STOP", fg_color="#c0392b", width=100,
                      command=self.stop_process)
        self.btn_stop.pack(side="left", padx=5)

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

    def _update_app_scaling(self):
        """Scales the TabView text based on window size"""
        try:
            # Check if window is being destroyed
            if not self.winfo_exists():
                return
                
            current_width = self.winfo_width()
            current_height = self.winfo_height()
            
            if current_width < 100 or current_height < 100: 
                return

            scale_factor = min(current_width / self.base_width, current_height / self.base_height)
            
            # Calculate Tab Font Size
            tab_font_size = max(11, min(18, int(14 * scale_factor)))
            font_cfg = ("Arial", tab_font_size, "bold")
            
            # Apply to Tabview Segmented Button (The tabs themselves)
            # Check if the segmented button still exists
            if hasattr(self.tabs, '_segmented_button') and self.tabs._segmented_button.winfo_exists():
                self.tabs._segmented_button.configure(font=font_cfg)

            # Scale Console Header
            console_font = max(10, min(16, int(12 * scale_factor)))
            if self.console_label.winfo_exists():
                self.console_label.configure(font=("Arial", console_font, "bold"))
                
        except Exception as e:
            # Silently ignore errors during window cleanup
            if "invalid command name" in str(e) or "has been destroyed" in str(e):
                pass
            else:
                # Only log non-cleanup errors for debugging
                print(f"Scaling error: {e}")

    def safe_destroy(self):
        """Safely destroy the application without cleanup errors"""
        try:
            # Stop any running processes first
            if self.current_process:
                self.stop_process()
            
            # Unbind events to prevent callbacks during destruction
            self.unbind("<Configure>")
            
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
            
            # FIX: Use the correct command structure - all modules are subcommands of fucyfuzz.fucyfuzz
            cmd = [sys.executable, "-m", "fucyfuzz.fucyfuzz", mod, "--help"]
            full_output += f"Command: {' '.join(cmd)}\n\n"
            
            try:
                # Use Dynamic Working Directory
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
                # Even if process returns error, we might still get help output
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
        
        textbox = ctk.CTkTextbox(top, font=("Consolas", 12))
        textbox.pack(fill="both", expand=True, padx=15, pady=10)
        textbox.insert("0.0", full_output)
        textbox.configure(state="disabled")

        ctk.CTkButton(top, text="Close", command=top.destroy, fg_color="#c0392b").pack(pady=10)
        
    
    # =======================================
    # PROCESS EXECUTION
    # =======================================
    def run_command(self, args_list, module_name="General"):
        if self.current_process:
            messagebox.showwarning("Busy", "Process running. Stop first.")
            return

        # FIX: Check if we're accidentally pointing to the binary instead of the module
        working_dir = self.working_dir
        
        # Debug: Show what we're about to run
        print(f"DEBUG: Working directory: {working_dir}")
        print(f"DEBUG: Args list: {args_list}")
        
        # Build the command properly
        cmd = [sys.executable, "-m", "fucyfuzz.fucyfuzz"] + [str(a) for a in args_list]
        
        # Use Dynamic Working Directory
        env = os.environ.copy()
        env["PYTHONPATH"] = working_dir + os.pathsep + env.get("PYTHONPATH", "")

        self._console_write(f"\n>>> [{module_name}] START: {' '.join(cmd)}\n")
        self._console_write(f">>> CWD: {working_dir}\n")
        self._console_write(f">>> PYTHONPATH: {env['PYTHONPATH']}\n")
        
        current_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "module": module_name,
            "command": " ".join(cmd),
            "output": "", "status": "Running"
        }

        def target():
            out_buf = []
            try:
                # FIX: First, let's check if the module exists
                module_check_cmd = [sys.executable, "-c", "import fucyfuzz.fucyfuzz; print('Module found')"]
                check_result = subprocess.run(
                    module_check_cmd, 
                    cwd=working_dir, 
                    env=env, 
                    capture_output=True, 
                    text=True,
                    timeout=5
                )
                
                if check_result.returncode != 0:
                    self._console_write(f"ERROR: Cannot import fucyfuzz module from {working_dir}\n")
                    self._console_write(f"Error details: {check_result.stderr}\n")
                    return

                # If module check passes, run the actual command
                cflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                self.current_process = subprocess.Popen(
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

                while True:
                    line = self.current_process.stdout.readline()
                    if not line and self.current_process.poll() is not None: 
                        break
                    if line:
                        self._console_write(line)
                        out_buf.append(line)

                rc = self.current_process.poll()
                self._console_write(f"\n<<< FINISHED (Code: {rc})\n")
                
                current_entry["output"] = "".join(out_buf)
                current_entry["status"] = "Success" if rc == 0 else f"Failed ({rc})"
                self.session_history.append(current_entry)

            except Exception as e:
                self._console_write(f"\nERROR: {e}\n")
                current_entry["output"] = "".join(out_buf) + f"\nError: {e}"
                current_entry["status"] = "Error"
                self.session_history.append(current_entry)
            finally:
                self.current_process = None

        threading.Thread(target=target, daemon=True).start()


    def stop_process(self):
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
        self.full_log_buffer.append(text)
        # Only try to update the console if it exists
        if hasattr(self, 'console') and self.console.winfo_exists():
            self.console.after(0, lambda: (self.console.insert("end", text), self.console.see("end")))
        else:
            # Store in pending messages if console isn't ready yet
            if not hasattr(self, 'pending_console_messages'):
                self.pending_console_messages = []
            self.pending_console_messages.append(text)

    # =======================================
    # REPORTING
    # =======================================
    def generate_pdf(self, filename, title, entries):
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("Error", "ReportLab not installed. Saving as .txt instead.")
            return self.save_txt_report(filename.replace(".pdf", ".txt"), title, entries)

        try:
            doc = SimpleDocTemplate(filename, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            story.append(Paragraph(title, styles['Title']))
            story.append(Spacer(1, 12))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            story.append(Spacer(1, 24))

            for idx, e in enumerate(entries):
                story.append(Paragraph(f"Action #{idx+1}: {e['module']}", styles['Heading2']))
                story.append(Paragraph(f"<b>Time:</b> {e['timestamp']}", styles['Normal']))
                story.append(Paragraph(f"<b>Command:</b> {e['command']}", styles['Normal']))
                status_color = "green" if "Success" in e['status'] else "red"
                story.append(Paragraph(f"<b>Status:</b> <font color={status_color}>{e['status']}</font>", styles['Normal']))
                story.append(Spacer(1, 6))
                out_text = e['output']
                if len(out_text) > 5000: out_text = out_text[:5000] + "\n... [TRUNCATED IN PDF] ..."
                style_code = styles['Code']
                style_code.fontSize = 8
                story.append(Preformatted(out_text, style_code))
                story.append(Spacer(1, 24))

            doc.build(story)
            messagebox.showinfo("Success", f"PDF Report Saved:\n{filename}")
        except Exception as e:
            messagebox.showerror("PDF Error", str(e))

    def save_txt_report(self, filename, title, entries):
        try:
            with open(filename, "w") as f:
                f.write(f"{title}\nGenerated: {datetime.now()}\n{'='*60}\n\n")
                for e in entries:
                    f.write(f"MODULE: {e['module']}\nTIME: {e['timestamp']}\nCMD: {e['command']}\nSTATUS: {e['status']}\nOUTPUT:\n{e['output']}\n{'-'*60}\n\n")
            messagebox.showinfo("Success", f"Text Report Saved:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_overall_report(self):
        if not self.session_history: return messagebox.showinfo("Info", "No history to report.")
        ext = ".pdf" if REPORTLAB_AVAILABLE else ".txt"
        ftypes = [("PDF Document", "*.pdf")] if REPORTLAB_AVAILABLE else [("Text File", "*.txt")]
        fn = filedialog.asksaveasfilename(defaultextension=ext, filetypes=ftypes)
        if fn: self.generate_pdf(fn, "FucyFuzz Overall Security Report", self.session_history)

    def save_module_report(self, mod):
        entries = [e for e in self.session_history if e['module'] == mod]
        if not entries: return messagebox.showinfo("Info", f"No history for {mod}.")
        ext = ".pdf" if REPORTLAB_AVAILABLE else ".txt"
        ftypes = [("PDF Document", "*.pdf")] if REPORTLAB_AVAILABLE else [("Text File", "*.txt")]
        fn = filedialog.asksaveasfilename(initialfile=f"{mod}_Report{ext}", defaultextension=ext, filetypes=ftypes)
        if fn: self.generate_pdf(fn, f"{mod} Module Report", entries)

    def save_full_logs(self):
        fn = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Log File", "*.log")])
        if fn:
            with open(fn, "w") as f: f.writelines(self.full_log_buffer)
            messagebox.showinfo("Success", "Logs saved.")


# ==============================================================================
#  BASE FRAME WITH SCALING AND TRANSITIONS
# ==============================================================================

class ScalableFrame(ctk.CTkFrame):
    """Base frame with responsive scaling capabilities and smooth transitions"""
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.base_width = 1400
        self.base_height = 800
        self._current_scale = 1.0
        self._transition_in_progress = False
        self._last_scale_update = 0
        
    def vw(self, percentage):
        """Convert percentage to width relative to base width (like CSS vw)"""
        return int((percentage / 100) * self.base_width)
    
    def vh(self, percentage):
        """Convert percentage to height relative to base height (like CSS vh)"""
        return int((percentage / 100) * self.base_height)
    
    def update_scaling(self):
        """Update scaling based on current frame size"""
        current_width = self.winfo_width()
        current_height = self.winfo_height()
        
        if current_width > 100 and current_height > 100:
            scale_factor = min(current_width / self.base_width, current_height / self.base_height)
            self._apply_scaling_with_transition(scale_factor)
    
    def _apply_scaling_with_transition(self, scale_factor):
        """Apply scaling with smooth transition effect"""
        current_time = time.time()
        if (self._transition_in_progress or 
            abs(scale_factor - self._current_scale) < 0.05 or
            current_time - self._last_scale_update < 0.05):
            return
            
        self._transition_in_progress = True
        self._last_scale_update = current_time
        self._current_scale = scale_factor
        
        # Apply scaling immediately
        self._apply_scaling(scale_factor)
        
        # Reset transition flag after a short delay for smooth effect
        self.after(50, lambda: setattr(self, '_transition_in_progress', False))
    
    def _apply_scaling(self, scale_factor):
        """Apply scaling to widgets - to be implemented by subclasses"""
        pass

# ==============================================================================
#  FRAMES
# ==============================================================================

class ConfigFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        self.title_label = ctk.CTkLabel(self, text="System Configuration", font=("Arial", 24, "bold"))
        self.title_label.pack(anchor="w", pady=(0, 20))
        
        # Grid for options
        self.grid_frame = ctk.CTkFrame(self)
        self.grid_frame.pack(fill="x", pady=20)
        
        # Working Directory Section
        ctk.CTkLabel(self.grid_frame, text="Fucyfuzz Path:").grid(row=0, column=0, padx=20, pady=20)
        
        self.wd_entry = ctk.CTkEntry(self.grid_frame, placeholder_text="/path/to/fucyfuzz")
        self.wd_entry.grid(row=0, column=1, padx=(20, 5), pady=20, sticky="ew")
        self.wd_entry.insert(0, app.working_dir)
        
        self.browse_btn = ctk.CTkButton(self.grid_frame, text="Browse", command=self.browse_wd)
        self.browse_btn.grid(row=0, column=2, padx=20, pady=20)

        # Interface Section
        ctk.CTkLabel(self.grid_frame, text="Interface:").grid(row=1, column=0, padx=20, pady=20)

        # CHANGE: Added fg_color and button_color to match
        self.driver = ctk.CTkOptionMenu(self.grid_frame, values=["socketcan", "vector", "pcan"],
                                        fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.driver.grid(row=1, column=1, padx=20, pady=20, sticky="ew")

        ctk.CTkLabel(self.grid_frame, text="Channel:").grid(row=2, column=0, padx=20, pady=20)
        self.channel = ctk.CTkEntry(self.grid_frame, placeholder_text="vcan0")
        self.channel.grid(row=2, column=1, padx=20, pady=20, sticky="ew")

        self.grid_frame.grid_columnconfigure(1, weight=1)

        self.save_btn = ctk.CTkButton(self, text="Save Config", command=self.save)
        self.save_btn.pack(pady=20)

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes with smooth scaling
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(12, min(18, int(14 * scale_factor)))
        button_font_size = max(12, min(18, int(14 * scale_factor)))
        
        # Update fonts with smooth transition
        self.title_label.configure(font=("Arial", title_font_size, "bold"))
        
        # Update padding and element sizes
        base_pad = int(20 * scale_factor)
        btn_height = max(35, min(55, int(45 * scale_factor)))
        entry_height = max(35, min(50, int(40 * scale_factor)))
        btn_width = max(100, min(180, int(140 * scale_factor)))
        
        font_cfg = ("Arial", label_font_size)
        
        # Update widget sizes with improved padding
        self.save_btn.configure(height=btn_height, font=("Arial", button_font_size), width=btn_width)
        self.browse_btn.configure(height=btn_height, font=("Arial", button_font_size), width=btn_width)
        self.wd_entry.configure(height=entry_height, font=font_cfg)
        self.channel.configure(height=entry_height, font=font_cfg)
        
        # FIX: Added dropdown_font scaling
        self.driver.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg)

    def browse_wd(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.wd_entry.delete(0, "end")
            self.wd_entry.insert(0, dir_path)

    def save(self):
        # Update App Working Directory
        new_wd = self.wd_entry.get().strip()
        if os.path.exists(new_wd):
            self.app.working_dir = new_wd
            self.app._console_write(f"[CONFIG] Working Directory updated to: {new_wd}\n")
        else:
            messagebox.showwarning("Warning", "Path does not exist. Working directory not updated.")

        try:
            with open(os.path.expanduser("~/.canrc"), "w") as f:
                f.write(f"[default]\ninterface={self.driver.get()}\nchannel={self.channel.get()}\n")
            self.app._console_write("[CONFIG] ~/.canrc Config Saved.\n")
        except Exception as e: messagebox.showerror("Error", str(e))

class ReconFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")
        
        self.title_label = ctk.CTkLabel(self.head_frame, text="Reconnaissance", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")
        
        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white", 
                      command=lambda: app.show_module_help("listener"))
        self.help_btn.pack(side="right", padx=10)
        
        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)", 
                      command=lambda: app.save_module_report("Recon"))
        self.report_btn.pack(side="right", padx=10)
        
        # Center the main button with better padding
        self.button_container = ctk.CTkFrame(self, fg_color="transparent")
        self.button_container.pack(expand=True, fill="both", pady=40)
        
        # ADDED: Interface checkbox
        self.interface_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.interface_frame.pack(pady=(0, 20))
        
        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(self.interface_frame, text="Use -i vcan0 interface", 
                                             variable=self.use_interface)
        self.interface_check.pack()
        
        self.start_btn = ctk.CTkButton(self.button_container, text="▶ Start Listener", 
                      command=self.run_listener)
        self.start_btn.pack(expand=True)

    def run_listener(self):
        """Run listener with optional interface parameter"""
        cmd = ["listener","-r"]
        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])
        self.app.run_command(cmd, "Recon")

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        button_font_size = max(14, min(22, int(16 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))
        
        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))
        
        # Update button sizes with better padding
        btn_height = max(50, min(90, int(70 * scale_factor)))
        btn_width = max(200, min(350, int(280 * scale_factor)))
        small_btn_size = max(40, min(70, int(55 * scale_factor)))
        small_btn_width = max(140, min(220, int(180 * scale_factor)))
        
        self.start_btn.configure(height=btn_height, font=("Arial", button_font_size, "bold"), 
                               width=btn_width, corner_radius=12)
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-1), 
                                width=small_btn_width, corner_radius=10)
        self.help_btn.configure(height=small_btn_size, width=small_btn_size, 
                              font=("Arial", button_font_size), corner_radius=10)
        self.interface_check.configure(font=("Arial", checkbox_font_size))

class DemoFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")
        
        self.title_label = ctk.CTkLabel(self.head_frame, text="Demo commands", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")
        
        # Main container for all buttons
        self.button_container = ctk.CTkFrame(self, fg_color="transparent")
        self.button_container.pack(expand=True, fill="both", pady=20)
        
        # Speed control buttons
        self.speed_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.speed_frame.pack(pady=10)
        
        self.start_speeding_btn = ctk.CTkButton(self.speed_frame, text="Start Speeding", 
                                              command=self.start_speeding)
        self.start_speeding_btn.pack(side="left", padx=5)
        
        self.stop_speeding_btn = ctk.CTkButton(self.speed_frame, text="Stop Speeding", 
                                             command=self.stop_speeding)
        self.stop_speeding_btn.pack(side="left", padx=5)
        
        self.reset_speed_btn = ctk.CTkButton(self.speed_frame, text="Reset Speed", 
                                           command=self.reset_speed)
        self.reset_speed_btn.pack(side="left", padx=5)
        
        # Indicator buttons
        self.indicator_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.indicator_frame.pack(pady=10)
        
        self.left_indicator_btn = ctk.CTkButton(self.indicator_frame, text="Left Indicator ON", 
                                              command=self.left_indicator_on)
        self.left_indicator_btn.pack(side="left", padx=5)
        
        self.right_indicator_btn = ctk.CTkButton(self.indicator_frame, text="Right Indicator ON", 
                                               command=self.right_indicator_on)
        self.right_indicator_btn.pack(side="left", padx=5)
        
        self.indicators_off_btn = ctk.CTkButton(self.indicator_frame, text="Indicators OFF", 
                                              command=self.indicators_off)
        self.indicators_off_btn.pack(side="left", padx=5)
        
        # Door control buttons
        self.doors_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.doors_frame.pack(pady=10)
        
        self.front_doors_open_btn = ctk.CTkButton(self.doors_frame, text="Front Doors Open", 
                                                command=self.front_doors_open)
        self.front_doors_open_btn.pack(side="left", padx=5)
        
        self.front_doors_close_btn = ctk.CTkButton(self.doors_frame, text="Front Doors Close", 
                                                 command=self.front_doors_close)
        self.front_doors_close_btn.pack(side="left", padx=5)
        
        self.back_doors_open_btn = ctk.CTkButton(self.doors_frame, text="Back Doors Open", 
                                               command=self.back_doors_open)
        self.back_doors_open_btn.pack(side="left", padx=5)
        
        self.back_doors_close_btn = ctk.CTkButton(self.doors_frame, text="Back Doors Close", 
                                                command=self.back_doors_close)
        self.back_doors_close_btn.pack(side="left", padx=5)
        
        # State variables
        self.speeding_active = False
        self.speed_job = None

    def run_demo_command(self, cmd_args, description):
        """Run demo commands without blocking the main process"""
        try:
            # Use subprocess directly without going through app.run_command
            working_dir = self.app.working_dir
            env = os.environ.copy()
            env["PYTHONPATH"] = working_dir + os.pathsep + env.get("PYTHONPATH", "")
            
            # Build the full command
            cmd = [sys.executable, "-m", "fucyfuzz.fucyfuzz"] + cmd_args
            
            # Run in background without waiting for completion
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=working_dir,
                env=env
            )
            
            # Just log that we sent the command
            self.app._console_write(f"[DEMO] Sent: {description}\n")
            
        except Exception as e:
            self.app._console_write(f"[DEMO ERROR] {description}: {e}\n")

    def start_speeding(self):
        """Start sending random speed data"""
        if not self.speeding_active:
            self.speeding_active = True
            self.start_speeding_btn.configure(fg_color="#c0392b", text="Speeding...")
            self.send_random_speeds()
            self.app._console_write("[DEMO] Started speed simulation\n")
        
    def stop_speeding(self):
        """Stop sending speed data"""
        self.speeding_active = False
        if self.speed_job:
            self.after_cancel(self.speed_job)
            self.speed_job = None
        self.start_speeding_btn.configure(fg_color="#1f538d", text="Start Speeding")
        self.app._console_write("[DEMO] Stopped speed simulation\n")
    
    def reset_speed(self):
        """Reset speed to 0"""
        self.stop_speeding()  # Stop any ongoing speed generation
        cmd = ["send", "message", "0x244#00"]
        self.run_demo_command(cmd, "Reset Speed to 0")
    
    def send_random_speeds(self):
        """Send random speed data with 0.5s delay"""
        if self.speeding_active:
            import random
            speed = random.randint(0, 200)  # Random speed between 0-200
            # Use proper hex format with 2 digits
            cmd = ["send", "message", f"0x244#{speed:02X}"]
            self.run_demo_command(cmd, f"Speed: {speed} km/h")
            
            # Schedule next speed update after 500ms
            self.speed_job = self.after(500, self.send_random_speeds)
    
    def left_indicator_on(self):
        """Turn left indicator on"""
        cmd = ["send", "message", "0x188#01"]
        self.run_demo_command(cmd, "Left Indicator ON")
    
    def right_indicator_on(self):
        """Turn right indicator on"""
        cmd = ["send", "message", "0x188#02"]
        self.run_demo_command(cmd, "Right Indicator ON")
    
    def indicators_off(self):
        """Turn all indicators off"""
        cmd = ["send", "message", "0x188#00"]
        self.run_demo_command(cmd, "Indicators OFF")
    
    def front_doors_open(self):
        """Open front doors"""
        cmd = ["send", "message", "0x19B#01.01.00.00"]
        self.run_demo_command(cmd, "Front Doors Open")
    
    def front_doors_close(self):
        """Close front doors"""
        cmd = ["send", "message", "0x19B#00.00.00.00"]
        self.run_demo_command(cmd, "Front Doors Close")
    
    def back_doors_open(self):
        """Open back doors"""
        cmd = ["send", "message", "0x19B#00.00.01.01"]
        self.run_demo_command(cmd, "Back Doors Open")
    
    def back_doors_close(self):
        """Close back doors"""
        cmd = ["send", "message", "0x19B#00.00.00.00"]
        self.run_demo_command(cmd, "Back Doors Close")

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        button_font_size = max(14, min(22, int(16 * scale_factor)))
        
        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))
        
        # Update button sizes
        btn_height = max(40, min(70, int(50 * scale_factor)))
        btn_width = max(120, min(200, int(150 * scale_factor)))
        
        # Apply scaling to all buttons
        buttons = [
            self.start_speeding_btn, self.stop_speeding_btn, self.reset_speed_btn,
            self.left_indicator_btn, self.right_indicator_btn, self.indicators_off_btn,
            self.front_doors_open_btn, self.front_doors_close_btn,
            self.back_doors_open_btn, self.back_doors_close_btn
        ]
        
        for button in buttons:
            button.configure(height=btn_height, font=("Arial", button_font_size), 
                           width=btn_width, corner_radius=8)
                           
class FuzzerFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        # Header
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")
        
        self.title_label = ctk.CTkLabel(self.head_frame, text="Signal Fuzzer", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")
        
        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("fuzzer"))
        self.help_btn.pack(side="right", padx=10)
        
        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)", 
                      command=lambda: app.save_module_report("Fuzzer"))
        self.report_btn.pack(side="right", padx=10)

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, pady=20)

        # Targeted Fuzz
        self.smart_tab = self.tabs.add("Targeted")

        ctk.CTkLabel(self.smart_tab, text="Select Message (Optional):").pack(pady=(20, 10))

        # CHANGE: Unified colors
        self.msg_select = ctk.CTkOptionMenu(self.smart_tab, values=["No DBC Loaded"], command=self.on_msg_select,
                                            fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.msg_select.pack(pady=10, fill="x", padx=20)

        # ADDED: Manual ID entry that's always enabled
        ctk.CTkLabel(self.smart_tab, text="OR Enter Manual ID:").pack(pady=(10, 5))
        self.tid = ctk.CTkEntry(self.smart_tab, placeholder_text="Target ID (e.g., 0x123)")
        self.tid.pack(pady=5, fill="x", padx=20)
        
        # CHANGED: Made data field optional with better placeholder
        self.data = ctk.CTkEntry(self.smart_tab, placeholder_text="Data Pattern (Optional - e.g., 1122..44)")
        self.data.pack(pady=10, fill="x", padx=20)

        # CHANGE: Unified colors
        self.mode = ctk.CTkOptionMenu(self.smart_tab, values=["brute", "mutate"],
                                    fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.mode.pack(pady=20, fill="x", padx=20)

        # ADDED: Interface checkbox for targeted fuzzing
        self.interface_frame = ctk.CTkFrame(self.smart_tab, fg_color="transparent")
        self.interface_frame.pack(pady=10, fill="x", padx=20)
        
        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(self.interface_frame, text="Use -i vcan0 interface", 
                                             variable=self.use_interface)
        self.interface_check.pack()

        # Add launch button for targeted fuzzing
        self.launch_btn = ctk.CTkButton(self.smart_tab, text="Start Targeted Fuzzing", 
                                      command=self.run_smart, fg_color="#27ae60")
        self.launch_btn.pack(pady=20, fill="x", padx=20)

        # Random
        self.rnd_tab = self.tabs.add("Random")
        
        # ADDED: Interface checkbox for random fuzzing
        self.random_interface_frame = ctk.CTkFrame(self.rnd_tab, fg_color="transparent")
        self.random_interface_frame.pack(pady=(20, 10), fill="x", padx=20)
        
        self.random_use_interface = ctk.BooleanVar(value=True)
        self.random_interface_check = ctk.CTkCheckBox(self.random_interface_frame, text="Use -i vcan0 interface", 
                                                    variable=self.random_use_interface)
        self.random_interface_check.pack()
        
        self.random_btn = ctk.CTkButton(self.rnd_tab, text="Start Random Noise", fg_color="#c0392b", 
                                      command=self.run_random)
        self.random_btn.pack(pady=10, fill="x", padx=20)

    def run_smart(self):
        """Run targeted fuzzing with optional interface"""
        tid = self.tid.get().strip()
        
        # CHANGED: Only require ID, data is optional
        if not tid:
            messagebox.showerror("Error", "Please enter a Target ID")
            return
        
        data = self.data.get().strip()
        mode = self.mode.get()
        
        # Build command with optional interface
        cmd = ["fuzzer", mode]
        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])
        cmd.extend([tid])
        
        # ADDED: Only add data if provided
        if data:
            cmd.extend([data])
        
        # Run the command
        self.app.run_command(cmd, "Fuzzer")

    def run_random(self):
        """Run random fuzzing with optional interface"""
        cmd = ["fuzzer", "random"]
        if self.random_use_interface.get():
            cmd.extend(["-i", "vcan0"])
        self.app.run_command(cmd, "Fuzzer")

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(13, min(19, int(15 * scale_factor)))
        button_font_size = max(13, min(19, int(15 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))
        
        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))
        
        # Update button and entry sizes with better padding
        btn_height = max(40, min(65, int(50 * scale_factor)))
        entry_height = max(38, min(55, int(45 * scale_factor)))
        small_btn_size = max(40, min(65, int(50 * scale_factor)))
        btn_width = max(160, min(260, int(200 * scale_factor)))
        
        font_cfg = ("Arial", label_font_size)

        # Configure all buttons that exist
        self.launch_btn.configure(height=btn_height, font=("Arial", button_font_size, "bold"), 
                                corner_radius=10)
        self.random_btn.configure(height=btn_height, font=("Arial", button_font_size, "bold"), 
                                corner_radius=10)
        self.help_btn.configure(height=small_btn_size, width=small_btn_size, 
                              font=("Arial", button_font_size), corner_radius=10)
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-1), 
                                width=btn_width, corner_radius=10)
        
        # Update entry and dropdown sizes
        # FIX: Added dropdown_font
        self.msg_select.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg, corner_radius=8)
        self.tid.configure(height=entry_height, font=font_cfg, corner_radius=8)
        self.data.configure(height=entry_height, font=font_cfg, corner_radius=8)
        self.mode.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg, corner_radius=8)
        
        # Update checkbox fonts
        self.interface_check.configure(font=("Arial", checkbox_font_size))
        self.random_interface_check.configure(font=("Arial", checkbox_font_size))

        # Scale inner Tabview fonts as well
        self.tabs._segmented_button.configure(font=("Arial", label_font_size))

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")

    def on_msg_select(self, selection):
        hex_id = self.app.get_id_by_name(selection)
        if hex_id:
            self.tid.delete(0, "end")
            self.tid.insert(0, hex_id)


class LengthAttackFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")
        
        self.title_label = ctk.CTkLabel(self.head_frame, text="Length Attack", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")
        
        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("lenattack"))
        self.help_btn.pack(side="right", padx=10)
        
        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)", 
                      command=lambda: app.save_module_report("LengthAttack"))
        self.report_btn.pack(side="right", padx=10)

        self.card = ctk.CTkFrame(self, corner_radius=12)
        self.card.pack(fill="x", padx=30, pady=30)
        
        # Row 0: DBC Select (Optional)
        ctk.CTkLabel(self.card, text="DBC Message (Optional):").grid(row=0, column=0, padx=20, pady=15)

        # CHANGE: Unified colors
        self.msg_select = ctk.CTkOptionMenu(self.card, values=["No DBC Loaded"], command=self.on_msg_select,
                                            fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.msg_select.grid(row=0, column=1, padx=20, pady=15, sticky="ew")

        # Row 1: Target ID (Manual entry - always available)
        ctk.CTkLabel(self.card, text="OR Enter Target ID (Hex):").grid(row=1, column=0, padx=20, pady=15)
        self.lid = ctk.CTkEntry(self.card, placeholder_text="0x123")
        self.lid.grid(row=1, column=1, padx=20, pady=15, sticky="ew")

        # Row 2: Extra Args
        ctk.CTkLabel(self.card, text="Extra Args:").grid(row=2, column=0, padx=20, pady=15)
        self.largs = ctk.CTkEntry(self.card, placeholder_text="Optional (e.g. -v)")
        self.largs.grid(row=2, column=1, padx=20, pady=15, sticky="ew")
        
        # Row 3: Interface checkbox
        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(self.card, text="Use -i vcan0 interface", 
                                             variable=self.use_interface)
        self.interface_check.grid(row=3, column=0, columnspan=2, padx=20, pady=15, sticky="w")
        
        self.card.grid_columnconfigure(1, weight=1)

        self.start_btn = ctk.CTkButton(self, text="START ATTACK", fg_color="#8e44ad", command=self.run_attack)
        self.start_btn.pack(fill="x", padx=50, pady=30)

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(13, min(19, int(15 * scale_factor)))
        button_font_size = max(14, min(22, int(16 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))
        
        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))
        
        # Update button and entry sizes with better padding
        btn_height = max(45, min(75, int(55 * scale_factor)))
        entry_height = max(38, min(55, int(45 * scale_factor)))
        small_btn_size = max(40, min(65, int(50 * scale_factor)))
        btn_width = max(160, min(260, int(200 * scale_factor)))
        
        self.start_btn.configure(height=btn_height, font=("Arial", button_font_size, "bold"), corner_radius=12)
        self.help_btn.configure(height=small_btn_size, width=small_btn_size, 
                              font=("Arial", button_font_size), corner_radius=10)
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-1), 
                                width=btn_width, corner_radius=10)
        
        font_cfg = ("Arial", label_font_size)

        # Update entry and dropdown sizes
        # FIX: Added dropdown_font
        self.msg_select.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg, corner_radius=8)
        self.lid.configure(height=entry_height, font=font_cfg, corner_radius=8)
        self.largs.configure(height=entry_height, font=font_cfg, corner_radius=8)
        self.interface_check.configure(font=("Arial", checkbox_font_size))

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")

    def on_msg_select(self, selection):
        hex_id = self.app.get_id_by_name(selection)
        if hex_id:
            self.lid.delete(0, "end")
            self.lid.insert(0, hex_id)

    def run_attack(self):
        tid = self.lid.get().strip()
        if not tid: 
            messagebox.showerror("Error", "Please enter a Target ID")
            return
            
        if not tid.startswith("0x") and not tid.isdigit(): 
            tid = "0x" + tid
        
        cmd = ["lenattack", tid]
        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])
        if self.largs.get().strip():
            cmd.extend(self.largs.get().strip().split())
            
        self.app.run_command(cmd, "LengthAttack")

class DCMFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")
        
        self.title_label = ctk.CTkLabel(self.head_frame, text="DCM Diagnostics", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")
        
        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("dcm"))
        self.help_btn.pack(side="right", padx=5)
        
        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)", 
                      command=lambda: app.save_module_report("DCM"))
        self.report_btn.pack(side="right", padx=5)

        # DCM Action Selection
        ctk.CTkLabel(self, text="DCM Action:").pack(pady=(20, 10))
        
        self.dcm_act = ctk.CTkOptionMenu(self, 
                                       values=["discovery", "services", "subfunc", "dtc", "testerpresent"],
                                       fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e",
                                       command=self.on_dcm_action_change)
        self.dcm_act.pack(pady=10, fill="x", padx=20)
        self.dcm_act.set("discovery")

        # DBC Message Selection (Optional)
        ctk.CTkLabel(self, text="DBC Message (Optional):").pack(pady=(10, 5))
        
        self.msg_select = ctk.CTkOptionMenu(self, values=["No DBC Loaded"], command=self.on_msg_select,
                                            fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.msg_select.pack(pady=5, fill="x", padx=20)

        # DCM Parameters Frame
        self.dcm_params_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dcm_params_frame.pack(fill="x", pady=10, padx=20)

        # Target ID (for most DCM commands)
        ctk.CTkLabel(self.dcm_params_frame, text="Target ID:").pack(anchor="w")
        self.dcm_tid = ctk.CTkEntry(self.dcm_params_frame, placeholder_text="e.g., 0x733")
        self.dcm_tid.pack(fill="x", pady=5)

        # Response ID (for services, subfunc, dtc)
        self.dcm_rid_label = ctk.CTkLabel(self.dcm_params_frame, text="Response ID:")
        self.dcm_rid = ctk.CTkEntry(self.dcm_params_frame, placeholder_text="e.g., 0x633")

        # Additional parameters for subfunc
        self.subfunc_frame = ctk.CTkFrame(self.dcm_params_frame, fg_color="transparent")
        
        self.subfunc_label = ctk.CTkLabel(self.subfunc_frame, text="Subfunction Parameters:")
        
        self.subfunc_params_frame = ctk.CTkFrame(self.subfunc_frame, fg_color="transparent")
        
        ctk.CTkLabel(self.subfunc_params_frame, text="Service:").grid(row=0, column=0, padx=(0, 5))
        self.dcm_service = ctk.CTkEntry(self.subfunc_params_frame, placeholder_text="0x22", width=80)
        self.dcm_service.grid(row=0, column=1, padx=5)
        
        ctk.CTkLabel(self.subfunc_params_frame, text="Subfunc:").grid(row=0, column=2, padx=(10, 5))
        self.dcm_subfunc = ctk.CTkEntry(self.subfunc_params_frame, placeholder_text="2", width=60)
        self.dcm_subfunc.grid(row=0, column=3, padx=5)
        
        ctk.CTkLabel(self.subfunc_params_frame, text="Data:").grid(row=0, column=4, padx=(10, 5))
        self.dcm_data = ctk.CTkEntry(self.subfunc_params_frame, placeholder_text="3", width=60)
        self.dcm_data.grid(row=0, column=5, padx=5)
        
        self.subfunc_params_frame.grid_columnconfigure(5, weight=1)

        # DCM Options Frame
        self.dcm_options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dcm_options_frame.pack(fill="x", pady=10, padx=20)

        # Blacklist options
        self.blacklist_label = ctk.CTkLabel(self.dcm_options_frame, text="Blacklist IDs (space separated):")
        self.dcm_blacklist = ctk.CTkEntry(self.dcm_options_frame, placeholder_text="0x123 0x456")

        # Auto blacklist
        self.autoblacklist_frame = ctk.CTkFrame(self.dcm_options_frame, fg_color="transparent")
        
        self.autoblacklist_label = ctk.CTkLabel(self.autoblacklist_frame, text="Auto Blacklist Count:")
        self.dcm_autoblacklist = ctk.CTkEntry(self.autoblacklist_frame, placeholder_text="10", width=80)

        # Extra Args
        ctk.CTkLabel(self, text="Extra Args:").pack(pady=(10, 5))
        self.dcm_extra_args = ctk.CTkEntry(self, placeholder_text="Additional arguments")
        self.dcm_extra_args.pack(fill="x", pady=5, padx=20)

        # DCM Interface checkbox
        self.dcm_use_interface = ctk.BooleanVar(value=True)
        self.dcm_interface_check = ctk.CTkCheckBox(self, text="Use -i vcan0 interface", 
                                                 variable=self.dcm_use_interface)
        self.dcm_interface_check.pack(pady=10, padx=20)

        # DCM Execute Button
        self.dcm_execute_btn = ctk.CTkButton(self, text="Execute DCM", command=self.run_dcm, fg_color="#8e44ad")
        self.dcm_execute_btn.pack(pady=20, fill="x", padx=20)

        # Initialize UI based on default action
        self.on_dcm_action_change("discovery")

    def on_dcm_action_change(self, selection):
        """Update DCM UI based on selected action"""
        # Hide all optional elements first
        self.dcm_rid_label.pack_forget()
        self.dcm_rid.pack_forget()
        self.subfunc_label.pack_forget()
        self.subfunc_frame.pack_forget()
        self.subfunc_params_frame.pack_forget()
        self.blacklist_label.pack_forget()
        self.dcm_blacklist.pack_forget()
        self.autoblacklist_label.pack_forget()
        self.autoblacklist_frame.pack_forget()
        self.dcm_autoblacklist.pack_forget()

        # Show common elements
        self.dcm_tid.pack(fill="x", pady=5)
        
        # Action-specific configurations
        if selection == "discovery":
            # Show blacklist options for discovery
            self.blacklist_label.pack(anchor="w")
            self.dcm_blacklist.pack(fill="x", pady=5)
            
            self.autoblacklist_label.pack(side="left")
            self.dcm_autoblacklist.pack(side="left", padx=10)
            self.autoblacklist_frame.pack(fill="x", pady=5)
            
        elif selection in ["services", "dtc"]:
            # Show response ID for services and dtc
            self.dcm_rid_label.pack(anchor="w")
            self.dcm_rid.pack(fill="x", pady=5)
            
        elif selection == "subfunc":
            # Show response ID and subfunction parameters
            self.dcm_rid_label.pack(anchor="w")
            self.dcm_rid.pack(fill="x", pady=5)
            
            self.subfunc_label.pack(anchor="w", pady=(10, 0))
            self.subfunc_params_frame.pack(fill="x", pady=5)
            self.subfunc_frame.pack(fill="x", pady=10)
            
        elif selection == "testerpresent":
            # Only target ID needed for testerpresent
            pass

    def run_dcm(self):
        """Execute DCM command"""
        action = self.dcm_act.get()
        cmd = ["dcm", action]
        
        # Add target ID if provided
        tid = self.dcm_tid.get().strip()
        if tid:
            cmd.append(tid)
        elif action != "discovery":  # discovery can work without target ID
            messagebox.showerror("Error", "Target ID is required for this action")
            return
        
        # Action-specific parameters
        if action in ["services", "subfunc", "dtc"]:
            rid = self.dcm_rid.get().strip()
            if rid:
                cmd.append(rid)
            else:
                messagebox.showerror("Error", "Response ID is required for this action")
                return
                
        if action == "subfunc":
            # Add subfunction parameters
            service = self.dcm_service.get().strip()
            subfunc = self.dcm_subfunc.get().strip()
            data = self.dcm_data.get().strip()
            
            if service:
                cmd.append(service)
            else:
                messagebox.showerror("Error", "Service parameter is required for subfunc")
                return
                
            if subfunc:
                cmd.append(subfunc)
            if data:
                cmd.append(data)
                
        # Add blacklist options for discovery
        if action == "discovery":
            blacklist = self.dcm_blacklist.get().strip()
            if blacklist:
                cmd.extend(["-blacklist"] + blacklist.split())
                
            autoblacklist = self.dcm_autoblacklist.get().strip()
            if autoblacklist:
                cmd.extend(["-autoblacklist", autoblacklist])
        
        # Add extra arguments if provided
        extra_args = self.dcm_extra_args.get().strip()
        if extra_args:
            cmd.extend(extra_args.split())
        
        # Add interface if checkbox is checked
        if self.dcm_use_interface.get():
            cmd.extend(["-i", "vcan0"])
                
        self.app.run_command(cmd, "DCM")

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")

    def on_msg_select(self, selection):
        hex_id = self.app.get_id_by_name(selection)
        if hex_id:
            self.dcm_tid.delete(0, "end")
            self.dcm_tid.insert(0, hex_id)

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(12, min(18, int(14 * scale_factor)))
        button_font_size = max(12, min(18, int(14 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))
        
        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))
        
        # Update button and entry sizes
        btn_height = max(35, min(55, int(45 * scale_factor)))
        entry_height = max(30, min(45, int(35 * scale_factor)))
        small_btn_size = max(35, min(60, int(45 * scale_factor)))
        btn_width = max(120, min(200, int(150 * scale_factor)))
        
        self.dcm_execute_btn.configure(height=btn_height, font=("Arial", button_font_size), width=btn_width)
        self.help_btn.configure(height=small_btn_size, width=small_btn_size, font=("Arial", button_font_size))
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-2), width=btn_width)
        
        font_cfg = ("Arial", label_font_size)

        # Update entry and dropdown sizes
        self.dcm_act.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg)
        self.msg_select.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg)
        self.dcm_tid.configure(height=entry_height, font=font_cfg)
        self.dcm_rid.configure(height=entry_height, font=font_cfg)
        self.dcm_service.configure(height=entry_height, font=font_cfg)
        self.dcm_subfunc.configure(height=entry_height, font=font_cfg)
        self.dcm_data.configure(height=entry_height, font=font_cfg)
        self.dcm_blacklist.configure(height=entry_height, font=font_cfg)
        self.dcm_autoblacklist.configure(height=entry_height, font=font_cfg)
        self.dcm_extra_args.configure(height=entry_height, font=font_cfg)
        self.dcm_interface_check.configure(font=("Arial", checkbox_font_size))

class UDSFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")
        
        self.title_label = ctk.CTkLabel(self.head_frame, text="UDS Diagnostics", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")
        
        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("uds"))
        self.help_btn.pack(side="right", padx=5)
        
        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)", 
                      command=lambda: app.save_module_report("UDS"))
        self.report_btn.pack(side="right", padx=5)

        # CHANGE: Unified colors
        self.act = ctk.CTkOptionMenu(self, values=["discovery", "services", "subservices", "dump_dids", "read_mem", "security_seed"],
                                    fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.act.pack(pady=10)

        # ADDED DBC SELECTION
        ctk.CTkLabel(self, text="DBC Message (Optional):").pack(pady=(10, 0))

        # CHANGE: Unified colors
        self.msg_select = ctk.CTkOptionMenu(self, values=["No DBC Loaded"], command=self.on_msg_select,
                                            fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.msg_select.pack(pady=5)

        # ==========================================================
        #  FIXED LAYOUT: Checkbox above Entry for Perfect Alignment
        # ==========================================================
        
        # 1. Checkbox acts as label
        self.use_id_var = ctk.BooleanVar(value=True)
        self.id_chk = ctk.CTkCheckBox(self, text="Use Target ID:", variable=self.use_id_var, 
                                      command=self.toggle_id_entry)
        self.id_chk.pack(pady=(10, 5), anchor="w", padx=5)

        # 2. Entry uses fill="x" to match other fields exactly
        self.tid = ctk.CTkEntry(self, placeholder_text="Target ID (0x7E0)")
        self.tid.pack(fill="x", pady=5)

        self.args = ctk.CTkEntry(self, placeholder_text="Extra Args")
        self.args.pack(fill="x", pady=5) # Matches width of tid above
        
        # ADDED: Interface checkbox
        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(self, text="Use -i vcan0 interface", 
                                             variable=self.use_interface)
        self.interface_check.pack(pady=10)
        
        self.execute_btn = ctk.CTkButton(self, text="Execute UDS", command=self.run)
        self.execute_btn.pack(pady=20)

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(12, min(18, int(14 * scale_factor)))
        button_font_size = max(12, min(18, int(14 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))
        
        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))
        
        # Update button and entry sizes
        btn_height = max(35, min(55, int(45 * scale_factor)))
        entry_height = max(30, min(45, int(35 * scale_factor)))
        small_btn_size = max(35, min(60, int(45 * scale_factor)))
        btn_width = max(120, min(200, int(150 * scale_factor)))
        
        self.execute_btn.configure(height=btn_height, font=("Arial", button_font_size), width=btn_width)
        self.help_btn.configure(height=small_btn_size, width=small_btn_size, font=("Arial", button_font_size))
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-2), width=btn_width)
        
        font_cfg = ("Arial", label_font_size)

        # Update entry and dropdown sizes
        # FIX: Added dropdown_font
        self.act.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg)
        self.msg_select.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg)
        self.tid.configure(height=entry_height, font=font_cfg)
        self.args.configure(height=entry_height, font=font_cfg)
        self.id_chk.configure(font=font_cfg)
        self.interface_check.configure(font=("Arial", checkbox_font_size))

    def toggle_id_entry(self):
        # Gray out the entry if checkbox is unchecked
        state = "normal" if self.use_id_var.get() else "disabled"
        self.tid.configure(state=state)

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")

    def on_msg_select(self, selection):
        hex_id = self.app.get_id_by_name(selection)
        if hex_id:
            self.use_id_var.set(True) # Auto-enable
            self.toggle_id_entry()
            self.tid.delete(0, "end")
            self.tid.insert(0, hex_id)

    def run(self):
        cmd = ["uds", self.act.get()]
        
        # Only add ID if checkbox is True AND entry is not empty
        if self.use_id_var.get():
            val = self.tid.get().strip()
            if val:
                cmd.append(val)
        
        # Add interface if checkbox is checked
        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])
                
        if self.args.get(): cmd.extend(self.args.get().split())
        self.app.run_command(cmd, "UDS")

class AdvancedFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")
        
        self.title_label = ctk.CTkLabel(self.head_frame, text="Advanced", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")
        
        # Buttons (Show help for both advanced modules)
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help(["doip", "xcp"]))
        self.help_btn.pack(side="right", padx=5)
        
        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)", 
                      command=lambda: app.save_module_report("Advanced"))
        self.report_btn.pack(side="right", padx=5)
        
        # DoIP Section with interface checkbox
        self.doip_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.doip_frame.pack(fill="x", pady=10)
        
        self.doip_use_interface = ctk.BooleanVar(value=True)
        self.doip_interface_check = ctk.CTkCheckBox(self.doip_frame, text="Use -i vcan0 interface for DoIP", 
                                                  variable=self.doip_use_interface)
        self.doip_interface_check.pack(pady=5)
        
        self.doip_btn = ctk.CTkButton(self.doip_frame, text="DoIP Discovery", 
                                    command=self.run_doip)
        self.doip_btn.pack(fill="x", pady=5)
        
        # XCP Section with interface checkbox
        self.xcp_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.xcp_frame.pack(fill="x", pady=10)
        
        self.xcp_use_interface = ctk.BooleanVar(value=True)
        self.xcp_interface_check = ctk.CTkCheckBox(self.xcp_frame, text="Use -i vcan0 interface for XCP", 
                                                 variable=self.xcp_use_interface)
        self.xcp_interface_check.pack(pady=5)
        
        self.xcp_id = ctk.CTkEntry(self.xcp_frame, placeholder_text="XCP ID")
        self.xcp_id.pack(pady=5)
        
        self.xcp_btn = ctk.CTkButton(self.xcp_frame, text="XCP Info", 
                                   command=self.run_xcp)
        self.xcp_btn.pack(pady=5)

    def run_doip(self):
        """Run DoIP with optional interface"""
        cmd = ["doip", "discovery"]
        if self.doip_use_interface.get():
            cmd.extend(["-i", "vcan0"])
        self.app.run_command(cmd, "Advanced")

    def run_xcp(self):
        """Run XCP with optional interface"""
        cmd = ["xcp", "info", self.xcp_id.get()]
        if self.xcp_use_interface.get():
            cmd.extend(["-i", "vcan0"])
        self.app.run_command(cmd, "Advanced")

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(12, min(18, int(14 * scale_factor)))
        button_font_size = max(12, min(18, int(14 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))
        
        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))
        
        # Update button and entry sizes
        btn_height = max(35, min(55, int(45 * scale_factor)))
        entry_height = max(30, min(45, int(35 * scale_factor)))
        small_btn_size = max(35, min(60, int(45 * scale_factor)))
        btn_width = max(120, min(200, int(150 * scale_factor)))
        
        self.doip_btn.configure(height=btn_height, font=("Arial", button_font_size))
        self.xcp_btn.configure(height=btn_height, font=("Arial", button_font_size), width=btn_width)
        self.help_btn.configure(height=small_btn_size, width=small_btn_size, font=("Arial", button_font_size))
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-2), width=btn_width)
        self.xcp_id.configure(height=entry_height, font=("Arial", label_font_size))
        self.doip_interface_check.configure(font=("Arial", checkbox_font_size))
        self.xcp_interface_check.configure(font=("Arial", checkbox_font_size))

class SendFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")
        
        self.title_label = ctk.CTkLabel(self.head_frame, text="Send & Replay", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")
        
        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("send"))
        self.help_btn.pack(side="right", padx=5)
        
        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)", 
                      command=lambda: app.save_module_report("SendReplay"))
        self.report_btn.pack(side="right", padx=5)

        # Main container
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, pady=10)

        # Send Type Selection
        ctk.CTkLabel(self.main_container, text="Send Type:").pack(pady=(10, 5))
        
        # CHANGE: Unified colors
        self.send_type = ctk.CTkOptionMenu(self.main_container, 
                                         values=["message", "file"],
                                         command=self.on_send_type_change,
                                         fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.send_type.pack(pady=5, fill="x", padx=20)
        self.send_type.set("message")

        # Message Frame
        self.message_frame = ctk.CTkFrame(self.main_container)
        self.message_frame.pack(fill="x", pady=10, padx=20)

        # DBC Message Selection (for message type)
        ctk.CTkLabel(self.message_frame, text="DBC Message (Optional):").pack(pady=(10, 5))
        self.msg_select = ctk.CTkOptionMenu(self.message_frame, 
                                          values=["No DBC Loaded"], 
                                          command=self.on_msg_select,
                                          fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.msg_select.pack(pady=5, fill="x")

        # Manual ID and Data Entry
        ctk.CTkLabel(self.message_frame, text="Manual CAN Frame (ID#DATA):").pack(pady=(10, 5))
        self.manual_frame = ctk.CTkEntry(self.message_frame, 
                                       placeholder_text="e.g., 0x7a0#c0.ff.ee.00.11.22.33.44 or 123#de.ad.be.ef")
        self.manual_frame.pack(pady=5, fill="x")

        # Additional Options for message
        self.message_options_frame = ctk.CTkFrame(self.message_frame, fg_color="transparent")
        self.message_options_frame.pack(fill="x", pady=5)

        # Delay option
        ctk.CTkLabel(self.message_options_frame, text="Delay (seconds):").grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.delay_entry = ctk.CTkEntry(self.message_options_frame, placeholder_text="0.5", width=80)
        self.delay_entry.grid(row=0, column=1, padx=(0, 20), sticky="w")

        # Periodic option
        self.periodic_var = ctk.BooleanVar()
        self.periodic_check = ctk.CTkCheckBox(self.message_options_frame, text="Periodic send", 
                                            variable=self.periodic_var)
        self.periodic_check.grid(row=0, column=2, padx=20, sticky="w")

        self.message_options_frame.grid_columnconfigure(2, weight=1)

        # File Frame (initially hidden)
        self.file_frame = ctk.CTkFrame(self.main_container)
        
        ctk.CTkLabel(self.file_frame, text="CAN Dump File:").pack(pady=(10, 5))
        
        self.file_selection_frame = ctk.CTkFrame(self.file_frame, fg_color="transparent")
        self.file_selection_frame.pack(fill="x", pady=5)
        
        self.file_path_entry = ctk.CTkEntry(self.file_selection_frame, placeholder_text="Select CAN dump file...")
        self.file_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.browse_file_btn = ctk.CTkButton(self.file_selection_frame, text="Browse", 
                                           command=self.browse_file, width=80)
        self.browse_file_btn.pack(side="right")

        # File options
        ctk.CTkLabel(self.file_frame, text="File Send Delay (seconds):").pack(pady=(10, 5))
        self.file_delay_entry = ctk.CTkEntry(self.file_frame, placeholder_text="0.2")
        self.file_delay_entry.pack(pady=5, fill="x")

        # Interface checkbox (common for both)
        self.interface_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.interface_frame.pack(fill="x", pady=10, padx=20)
        
        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(self.interface_frame, text="Use -i vcan0 interface", 
                                             variable=self.use_interface)
        self.interface_check.pack()

        # Send Button
        self.send_btn = ctk.CTkButton(self.main_container, text="Send", 
                                    command=self.run_send, fg_color="#27ae60")
        self.send_btn.pack(pady=20, fill="x", padx=20)

        # Initialize UI state
        self.on_send_type_change("message")

    def on_send_type_change(self, selection):
        """Show/hide appropriate frames based on send type selection"""
        if selection == "message":
            self.message_frame.pack(fill="x", pady=10, padx=20)
            self.file_frame.pack_forget()
            self.send_btn.configure(text="Send Message")
        else:  # file
            self.message_frame.pack_forget()
            self.file_frame.pack(fill="x", pady=10, padx=20)
            self.send_btn.configure(text="Send File")

    def on_msg_select(self, selection):
        """When DBC message is selected, populate manual field with ID"""
        hex_id = self.app.get_id_by_name(selection)
        if hex_id:
            # Keep existing data if any, just update ID
            current_text = self.manual_frame.get()
            if "#" in current_text:
                # Replace ID part
                data_part = current_text.split("#")[1]
                self.manual_frame.delete(0, "end")
                self.manual_frame.insert(0, f"{hex_id}#{data_part}")
            else:
                # Just set ID
                self.manual_frame.delete(0, "end")
                self.manual_frame.insert(0, f"{hex_id}#")

    def browse_file(self):
        """Browse for CAN dump file"""
        filename = filedialog.askopenfilename(
            title="Select CAN Dump File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.file_path_entry.delete(0, "end")
            self.file_path_entry.insert(0, filename)

    def run_send(self):
        """Execute send command based on selected type and options"""
        send_type = self.send_type.get()
        cmd = ["send"]

        # Add interface if selected
        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])

        if send_type == "message":
            # Build message command
            manual_input = self.manual_frame.get().strip()
            if not manual_input:
                messagebox.showerror("Error", "Please enter CAN frame in format: ID#DATA")
                return

            # Add delay if specified
            delay = self.delay_entry.get().strip()
            if delay:
                try:
                    float(delay)  # Validate it's a number
                    cmd.extend(["-d", delay])
                except ValueError:
                    messagebox.showerror("Error", "Delay must be a valid number")
                    return

            # Add periodic flag if selected
            if self.periodic_var.get():
                cmd.extend(["-p"])

            # Add the message
            cmd.extend(["message", manual_input])

        else:  # file type
            file_path = self.file_path_entry.get().strip()
            if not file_path:
                messagebox.showerror("Error", "Please select a CAN dump file")
                return

            if not os.path.exists(file_path):
                messagebox.showerror("Error", "Selected file does not exist")
                return

            # Add file delay if specified
            file_delay = self.file_delay_entry.get().strip()
            if file_delay:
                try:
                    float(file_delay)  # Validate it's a number
                    cmd.extend(["-d", file_delay])
                except ValueError:
                    messagebox.showerror("Error", "File delay must be a valid number")
                    return

            # Add file command
            cmd.extend(["file", file_path])

        self.app.run_command(cmd, "SendReplay")

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(12, min(18, int(14 * scale_factor)))
        button_font_size = max(12, min(18, int(14 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))
        
        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))
        
        # Update button and entry sizes
        btn_height = max(35, min(55, int(45 * scale_factor)))
        entry_height = max(30, min(45, int(35 * scale_factor)))
        small_btn_size = max(35, min(60, int(45 * scale_factor)))
        btn_width = max(120, min(200, int(150 * scale_factor)))
        
        self.send_btn.configure(height=btn_height, font=("Arial", button_font_size), corner_radius=8)
        self.browse_file_btn.configure(height=btn_height, font=("Arial", button_font_size-1), width=btn_width)
        self.help_btn.configure(height=small_btn_size, width=small_btn_size, font=("Arial", button_font_size))
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-2), width=btn_width)
        
        font_cfg = ("Arial", label_font_size)

        # Update entry and dropdown sizes
        self.send_type.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg)
        self.msg_select.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg)
        self.manual_frame.configure(height=entry_height, font=font_cfg)
        self.delay_entry.configure(height=entry_height, font=font_cfg)
        self.file_path_entry.configure(height=entry_height, font=font_cfg)
        self.file_delay_entry.configure(height=entry_height, font=font_cfg)
        self.interface_check.configure(font=("Arial", checkbox_font_size))
        self.periodic_check.configure(font=("Arial", checkbox_font_size))

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")

class MonitorFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.is_monitoring = False
        
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x", pady=10)
        
        self.title_label = ctk.CTkLabel(self.head_frame, text="Traffic Monitor", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")
        
        self.save_btn = ctk.CTkButton(self.head_frame, text="📥 Save CSV", command=self.save_monitor)
        self.save_btn.pack(side="right")

        self.ctl_frame = ctk.CTkFrame(self)
        self.ctl_frame.pack(fill="x", pady=5)
        
        self.sim_btn = ctk.CTkButton(self.ctl_frame, text="▶ Simulate", command=self.toggle_sim, fg_color="#27ae60")
        self.sim_btn.pack(side="left", padx=5)
        
        self.clear_btn = ctk.CTkButton(self.ctl_frame, text="🗑 Clear", command=self.clear, fg_color="gray30")
        self.clear_btn.pack(side="right")

        self.cols = ["Time", "ID", "Name", "Signals", "Raw"]
        self.header = ctk.CTkFrame(self, fg_color="#111")
        self.header.pack(fill="x")
        for i, c in enumerate(self.cols):
            lbl = ctk.CTkLabel(self.header, text=c, font=("Arial", 11, "bold"))
            lbl.grid(row=0, column=i, sticky="ew", padx=2)
            self.header.grid_columnconfigure(i, weight=1)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a")
        self.scroll.pack(fill="both", expand=True)

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        button_font_size = max(12, min(18, int(14 * scale_factor)))
        header_font_size = max(10, min(16, int(12 * scale_factor)))
        
        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))
        
        # Update button sizes
        btn_height = max(30, min(50, int(40 * scale_factor)))
        btn_width = max(100, min(160, int(120 * scale_factor)))
        small_btn_width = max(60, min(100, int(80 * scale_factor)))
        
        self.save_btn.configure(height=btn_height, font=("Arial", button_font_size), width=btn_width)
        self.sim_btn.configure(height=btn_height, font=("Arial", button_font_size), width=btn_width)
        self.clear_btn.configure(height=btn_height, font=("Arial", button_font_size), width=small_btn_width)
        
        # Update header font
        for widget in self.header.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(font=("Arial", header_font_size, "bold"))
        
        # Update header height
        header_height = max(25, min(40, int(30 * scale_factor)))
        self.header.configure(height=header_height)

    def add_row(self, aid, data):
        if len(self.scroll.winfo_children()) > 60: self.scroll.winfo_children()[0].destroy()
        vals = [time.strftime("%H:%M:%S"), hex(aid), "Unknown", "---", " ".join(f"{b:02X}" for b in data)]
        
        if self.app.dbc_db:
            try:
                m = self.app.dbc_db.get_message_by_frame_id(aid)
                if m:
                    vals[2] = m.name
                    vals[3] = str(m.decode(data))
            except: pass
            
        row = ctk.CTkFrame(self.scroll, fg_color=("gray20", "gray15"))
        row.pack(fill="x", pady=1)
        for i, v in enumerate(vals):
            ctk.CTkLabel(row, text=v, font=("Consolas", 10), anchor="w").grid(row=0, column=i, sticky="ew", padx=2)
            row.grid_columnconfigure(i, weight=1)

    def save_monitor(self):
        fn = filedialog.asksaveasfilename(defaultextension=".csv")
        if fn:
            with open(fn, "w") as f:
                f.write("Time,ID,Name,Signals,Raw\n")
                for row in self.scroll.winfo_children():
                    cols = [w.cget("text") for w in row.winfo_children() if isinstance(w, ctk.CTkLabel)]
                    f.write(",".join(cols) + "\n")
    
    def clear(self):
        for w in self.scroll.winfo_children(): w.destroy()

    def toggle_sim(self):
        if not self.is_monitoring:
            self.is_monitoring = True
            threading.Thread(target=self._sim, daemon=True).start()
        else: self.is_monitoring = False

    def _sim(self):
        while self.is_monitoring:
            if self.app.dbc_db and self.app.dbc_db.messages:
                m = random.choice(self.app.dbc_db.messages)
                b = bytes([random.getrandbits(8) for _ in range(m.length)])
                self.after(0, lambda i=m.frame_id, d=b: self.add_row(i, d))
            else:
                b = bytes([random.getrandbits(8) for _ in range(8)])
                self.after(0, lambda i=random.randint(0x100, 0x500), d=b: self.add_row(i, d))
            time.sleep(0.2)

if __name__ == "__main__":
    app = FucyfuzzApp()
    app.mainloop()