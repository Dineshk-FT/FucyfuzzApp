# frame_classes.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import os
import sys
import time
import random
import threading

# Import font configuration and scaling utilities
from fonts import FontConfig
from ui_scaling import UIScaling


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
        self._widget_registry = []  # Track widgets for scaling
        
    def register_widget(self, widget, widget_type="button"):
        """Register a widget for automatic scaling"""
        self._widget_registry.append((widget, widget_type))
    
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

        # Apply scaling to all registered widgets
        self._apply_scaling(scale_factor)

        # Reset transition flag after a short delay for smooth effect
        self.after(50, lambda: setattr(self, '_transition_in_progress', False))

    def _apply_scaling(self, scale_factor):
        """Apply scaling to all registered widgets - to be overridden by subclasses"""
        # Scale registered widgets
        for widget, widget_type in self._widget_registry:
            if widget.winfo_exists():
                UIScaling.scale_widget(widget, widget_type, scale_factor)
        
        # Also scale all children recursively
        UIScaling.scale_frame_children(self, scale_factor, exclude_types=["CTkTabview"])


# ==============================================================================
#  FRAME CLASSES
# ==============================================================================

class ConfigFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.app = app

        # ─────────────────────────────────────────────
        # Header (About + Title)
        # ─────────────────────────────────────────────
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 20))

        self.about_btn = ctk.CTkButton(
            self.header_frame,
            text="About",
            width=70,
            command=self.show_about,
            fg_color="#34495e",
            hover_color="#2c3e50"
        )
        self.about_btn.pack(side="left")
        self.register_widget(self.about_btn, "button_small")

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="System Configuration",
            font=FontConfig.get_title_font(1.0)
        )
        self.title_label.pack(side="left", padx=20)
        self.register_widget(self.title_label, "title")

        # ─────────────────────────────────────────────
        # Main Grid
        # ─────────────────────────────────────────────
        self.grid_frame = ctk.CTkFrame(self)
        self.grid_frame.pack(fill="x", pady=20)

        # Working Directory
        wd_label = ctk.CTkLabel(self.grid_frame, text="Fucyfuzz Path:")
        wd_label.grid(row=0, column=0, padx=20, pady=20)
        self.register_widget(wd_label, "label")

        self.wd_entry = ctk.CTkEntry(self.grid_frame, placeholder_text="/path/to/fucyfuzz")
        self.wd_entry.grid(row=0, column=1, padx=(20, 5), pady=20, sticky="ew")
        self.wd_entry.insert(0, app.working_dir)
        self.register_widget(self.wd_entry, "entry")

        self.browse_btn = ctk.CTkButton(
            self.grid_frame, text="Browse", command=self.browse_wd
        )
        self.browse_btn.grid(row=0, column=2, padx=20, pady=20)
        self.register_widget(self.browse_btn, "button")

        # Interface
        interface_label = ctk.CTkLabel(self.grid_frame, text="Interface:")
        interface_label.grid(row=1, column=0, padx=20, pady=20)
        self.register_widget(interface_label, "label")

        self.driver = ctk.CTkOptionMenu(
            self.grid_frame,
            values=["socketcan", "vector", "pcan"],
            fg_color="#1f538d",
            button_color="#1f538d",
            button_hover_color="#14375e"
        )
        self.driver.grid(row=1, column=1, padx=20, pady=20, sticky="ew")
        self.register_widget(self.driver, "dropdown")

        channel_label = ctk.CTkLabel(self.grid_frame, text="Channel:")
        channel_label.grid(row=2, column=0, padx=20, pady=20)
        self.register_widget(channel_label, "label")

        self.channel = ctk.CTkEntry(self.grid_frame, placeholder_text="vcan0")
        self.channel.grid(row=2, column=1, padx=20, pady=20, sticky="ew")
        self.register_widget(self.channel, "entry")

        # DBC
        dbc_label = ctk.CTkLabel(self.grid_frame, text="DBC File:")
        dbc_label.grid(row=3, column=0, padx=20, pady=20)
        self.register_widget(dbc_label, "label")

        self.dbc_entry = ctk.CTkEntry(self.grid_frame, placeholder_text="Select DBC file...")
        self.dbc_entry.grid(row=3, column=1, padx=(20, 5), pady=20, sticky="ew")
        self.register_widget(self.dbc_entry, "entry")

        self.dbc_browse_btn = ctk.CTkButton(
            self.grid_frame, text="Browse DBC", command=self.browse_dbc
        )
        self.dbc_browse_btn.grid(row=3, column=2, padx=20, pady=20)
        self.register_widget(self.dbc_browse_btn, "button")

        self.load_dbc_btn = ctk.CTkButton(
            self.grid_frame,
            text="Load DBC",
            command=self.load_dbc,
            fg_color="#8e44ad"
        )
        self.load_dbc_btn.grid(row=3, column=3, padx=20, pady=20)
        self.register_widget(self.load_dbc_btn, "button")

        # DBC Status
        self.dbc_status_frame = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
        self.dbc_status_frame.grid(row=4, column=0, columnspan=4, padx=20, pady=(0, 20), sticky="ew")

        self.dbc_status_label = ctk.CTkLabel(
            self.dbc_status_frame,
            text="No DBC loaded",
            font=FontConfig.get_label_font(0.9),
            text_color="#95a5a6"
        )
        self.dbc_status_label.pack(side="left")
        self.register_widget(self.dbc_status_label, "label")

        self.clear_dbc_btn = ctk.CTkButton(
            self.dbc_status_frame,
            text="Clear DBC",
            width=100,
            command=self.clear_dbc,
            fg_color="#7f8c8d"
        )
        self.clear_dbc_btn.pack(side="right")
        self.register_widget(self.clear_dbc_btn, "button_small")

        self.grid_frame.grid_columnconfigure(1, weight=1)

        self.save_btn = ctk.CTkButton(self, text="Save Config", command=self.save)
        self.save_btn.pack(pady=20)
        self.register_widget(self.save_btn, "button_large")

        self.update_dbc_status()

    # ─────────────────────────────────────────────
    # Scaling
    # ─────────────────────────────────────────────
    def _apply_scaling(self, scale_factor):
        super()._apply_scaling(scale_factor)
        padding = FontConfig.get_padding(scale_factor)
        self.grid_frame.configure(padx=padding, pady=padding)

    # ─────────────────────────────────────────────
    # Browse Handlers
    # ─────────────────────────────────────────────
    def browse_wd(self):
        path = filedialog.askdirectory(title="Select FucyFuzz Directory")
        if path:
            self.wd_entry.delete(0, "end")
            self.wd_entry.insert(0, path)

    def browse_dbc(self):
        fp = filedialog.askopenfilename(
            title="Select DBC File",
            filetypes=[("DBC files", "*.dbc"), ("All files", "*.*")]
        )
        if fp:
            self.dbc_entry.delete(0, "end")
            self.dbc_entry.insert(0, fp)

    # ─────────────────────────────────────────────
    # DBC Logic
    # ─────────────────────────────────────────────
    def load_dbc(self):
        dbc_path = self.dbc_entry.get().strip()

        if not dbc_path or not os.path.exists(dbc_path):
            messagebox.showerror("Error", "Invalid DBC file path")
            return

        try:
            import cantools
            self.app.dbc_db = cantools.database.load_file(dbc_path)
            self.app.dbc_messages = {
                msg.name: msg.frame_id for msg in self.app.dbc_db.messages
            }

            self.update_dbc_status()
            self.app.refresh_tab_dropdowns()
            self.app._console_write(
                f"[CONFIG] Loaded DBC: {os.path.basename(dbc_path)}\n"
            )

            messagebox.showinfo(
                "DBC Loaded",
                f"{len(self.app.dbc_messages)} messages loaded"
            )

        except Exception as e:
            self.app.dbc_db = None
            self.app.dbc_messages = {}
            self.update_dbc_status()
            messagebox.showerror("Error", str(e))

    def clear_dbc(self):
        if not self.app.dbc_db:
            return

        self.app.dbc_db = None
        self.app.dbc_messages = {}
        self.update_dbc_status()
        self.app.refresh_tab_dropdowns()
        self.app._console_write("[CONFIG] DBC cleared\n")

    def update_dbc_status(self):
        if self.app.dbc_db:
            self.dbc_status_label.configure(
                text=f"Loaded ({len(self.app.dbc_messages)} messages)",
                text_color="#27ae60"
            )
            self.clear_dbc_btn.configure(state="normal")
        else:
            self.dbc_status_label.configure(
                text="No DBC loaded",
                text_color="#95a5a6"
            )
            self.clear_dbc_btn.configure(state="disabled")

    # ─────────────────────────────────────────────
    # Save Config
    # ─────────────────────────────────────────────
    def save(self):
        wd = self.wd_entry.get().strip()
        if os.path.exists(wd):
            self.app.working_dir = wd

        try:
            with open(os.path.expanduser("~/.canrc"), "w") as f:
                f.write(
                    "[default]\n"
                    f"interface={self.driver.get()}\n"
                    f"channel={self.channel.get()}\n"
                )
            self.app._console_write("[CONFIG] ~/.canrc saved\n")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ─────────────────────────────────────────────
    # About Modal
    # ─────────────────────────────────────────────
    def show_about(self):
        win = ctk.CTkToplevel(self)
        win.title("About FucyFuzz")
        win.geometry("420x260")
        win.resizable(False, False)

        # Ensure window appears above parent
        win.transient(self.winfo_toplevel())

        frame = ctk.CTkFrame(win, corner_radius=12)
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        ctk.CTkLabel(
            frame,
            text="FucyFuzz",
            font=FontConfig.get_title_font(1.2)
        ).pack(pady=(10, 5))

        ctk.CTkLabel(
            frame,
            text="Version 1.0.0",
            text_color="#bdc3c7"
        ).pack()

        ctk.CTkLabel(
            frame,
            text=(
                "Automotive CAN Fuzzing & Diagnostics Tool\n\n"
                "• CAN interface configuration\n"
                "• DBC decoding support\n"
                "• Diagnostics & fuzzing modules"
            ),
            wraplength=340,
            justify="left"
        ).pack(pady=15)

        ctk.CTkLabel(
            frame,
            text="© 2026 • Dinesh Ravikumar",
            text_color="#95a5a6"
        ).pack(pady=(10, 0))

        ctk.CTkButton(
            frame,
            text="Close",
            width=100,
            command=win.destroy
        ).pack(pady=15)

        # ✅ SAFE modal behavior (Linux / Wayland friendly)
        win.after(10, win.grab_set)


class ReconFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="Reconnaissance", font=FontConfig.get_title_font(1.0))
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("listener"))
        self.help_btn.pack(side="right", padx=10)
        self.register_widget(self.help_btn, "button_small")

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("Recon"))
        self.report_btn.pack(side="right", padx=10)
        self.register_widget(self.report_btn, "button_small")

        # Center the main button with better padding
        self.button_container = ctk.CTkFrame(self, fg_color="transparent")
        self.button_container.pack(expand=True, fill="both", pady=20)

        # ADDED: Interface checkbox
        self.interface_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.interface_frame.pack(pady=(0, 20))

        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(self.interface_frame, text="Use -i vcan0 interface",
                                             variable=self.use_interface)
        self.interface_check.pack()
        self.register_widget(self.interface_check, "checkbox")

        # Original Start Listener button
        self.start_btn = ctk.CTkButton(self.button_container, text="▶ Start Listener",
                      command=self.run_listener)
        self.start_btn.pack(expand=True)
        self.register_widget(self.start_btn, "button_large")

        # NEW: Master Demo Button
        self.master_demo_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.master_demo_frame.pack(pady=(30, 0), fill="x")

        self.master_demo_btn = ctk.CTkButton(
            self.master_demo_frame,
            text="🚀 Master Demo (Run All Tests)",
            command=self.toggle_master_demo,
            font=FontConfig.get_button_font(1.0),
            width=200,
            height=40,
            anchor="center",
            fg_color="#9b59b6",  # Purple color for distinction
            corner_radius=20  # Semi-circle level rounding
        )
        self.master_demo_btn.pack(pady=10)
        self.register_widget(self.master_demo_btn, "button_large")

        # NEW: Progress label
        self.progress_label = ctk.CTkLabel(
            self.master_demo_frame,
            text="Ready to run master demo",
            font=FontConfig.get_label_font(0.9),
            text_color="#7f8c8d"
        )
        self.progress_label.pack()
        self.register_widget(self.progress_label, "label")

        # ================= STATE =================
        self.master_demo_active = False
        self.master_demo_process = None
        self.current_command_index = 0
        self.commands_queue = []

    def run_listener(self):
        """Run listener with correct FucyFuzz interface handling"""
        cmd = []
        
        # Add interface BEFORE the module name
        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])
        
        # Module name and arguments
        cmd.extend(["listener", "-r"])
        
        # Run the command through the app's system
        self.app.run_command(cmd, "Recon")

    # ======================================================
    # MASTER DEMO COMMANDS QUEUE
    # ======================================================
    def _setup_master_commands(self):
        """Setup all commands for the master demo"""
        commands = []
        
        # Interface parameter (if selected)
        interface_param = ["-i", "vcan0"] if self.use_interface.get() else []
        
        # Fuzzer commands
        commands.append(["fuzzer", "random"] + interface_param)
        commands.append(["fuzzer", "random", "-min", "4", "-seed", "0xabc123", "-f", "log.txt"] + interface_param)
        commands.append(["fuzzer", "brute", "0x123", "12ab..78"] + interface_param)
        commands.append(["fuzzer", "mutate", "7f..", "12ab...."] + interface_param)
        commands.append(["fuzzer", "replay", "log.txt"] + interface_param)
        commands.append(["fuzzer", "identify", "log.txt"] + interface_param)
        
        # Length Attack commands
        commands.append(["lenattack", "0x123"] + interface_param)
        commands.append(["lenattack", "0x123", "--min-dlc", "0", "--max-dlc", "8", "--pattern", "rand"] + interface_param)
        
        # DCM commands
        commands.append(["dcm", "discovery"] + interface_param)
        commands.append(["dcm", "discovery", "-blacklist", "0x123", "0x456"] + interface_param)
        commands.append(["dcm", "discovery", "-autoblacklist", "10"] + interface_param)
        commands.append(["dcm", "services", "0x733", "0x633"] + interface_param)
        commands.append(["dcm", "subfunc", "0x733", "0x633", "0x22", "2", "3"] + interface_param)
        commands.append(["dcm", "dtc", "0x7df", "0x7e8"] + interface_param)
        commands.append(["dcm", "testerpresent", "0x733"] + interface_param)
        
        # UDS commands
        commands.append(["uds", "discovery"] + interface_param)
        commands.append(["uds", "discovery", "-blacklist", "0x123", "0x456"] + interface_param)
        commands.append(["uds", "discovery", "-autoblacklist", "10"] + interface_param)
        commands.append(["uds", "services", "0x733", "0x633"] + interface_param)
        commands.append(["uds", "ecu_reset", "1", "0x733", "0x633"] + interface_param)
        commands.append(["uds", "testerpresent", "0x733"] + interface_param)
        commands.append(["uds", "security_seed", "0x3", "0x1", "0x733", "0x633", "-r", "1", "-d", "0.5"] + interface_param)
        commands.append(["uds", "dump_dids", "0x733", "0x633"] + interface_param)
        commands.append(["uds", "dump_dids", "0x733", "0x633", "--min_did", "0x6300", "--max_did", "0x6fff", "-t", "0.1"] + interface_param)
        commands.append(["uds", "read_mem", "0x733", "0x633", "--start_addr", "0x0200", "--mem_length", "0x10000"] + interface_param)
        
        return commands

    # ======================================================
    # MASTER DEMO TOGGLE
    # ======================================================
    def toggle_master_demo(self):
        if not self.master_demo_active:
            # Start master demo
            self._start_master_demo()
        else:
            # Stop master demo
            self._stop_master_demo()

    def _start_master_demo(self):
        """Start the master demo sequence"""
        self.master_demo_active = True
        self.master_demo_btn.configure(
            text="⏹ Stop Master Demo",
            fg_color="#c0392b"  # Red color when active
        )
        
        # Setup commands queue
        self.commands_queue = self._setup_master_commands()
        self.current_command_index = 0
        
        # Update progress label
        self.progress_label.configure(
            text=f"Running command 1 of {len(self.commands_queue)}",
            text_color="#3498db"
        )
        
        # Start executing commands
        self._execute_next_command()

    def _execute_next_command(self):
        """Execute the next command in the queue"""
        if not self.master_demo_active or self.current_command_index >= len(self.commands_queue):
            self._complete_master_demo()
            return
        
        # Get current command
        command = self.commands_queue[self.current_command_index]
        
        # Update progress label
        self.progress_label.configure(
            text=f"Running command {self.current_command_index + 1} of {len(self.commands_queue)}: {' '.join(command)}",
            text_color="#3498db"
        )
        
        # Log the command
        self.app._console_write(f"\n[MASTER DEMO] Executing: fucyfuzz {' '.join(command)}\n")
        
        # Determine module name for tracking
        module_name = self._get_module_from_command(command)
        
        # Use a thread to run the command and monitor completion
        threading.Thread(
            target=self._run_command_with_timeout,
            args=(command, module_name, self.current_command_index),
            daemon=True
        ).start()

    def _run_command_with_timeout(self, command, module_name, cmd_idx):
        """Run a command with timeout using the app's infrastructure"""
        try:
            # ALWAYS use the venv Python approach
            venv_python = os.path.join(self.app.working_dir, "venv", "bin", "python")
            
            # Check if venv Python exists
            if not os.path.exists(venv_python):
                self.app._console_write(f"[MASTER DEMO ERROR] Venv Python not found at {venv_python}\n")
                self.app._console_write(f"[MASTER DEMO] Using system Python instead...\n")
                python_executable = sys.executable
            else:
                python_executable = venv_python
            
            # Build the command
            full_cmd = [python_executable, "-m", "fucyfuzz.fucyfuzz"] + command
            
            # Log the command
            self.app._console_write(f"[DEBUG] Full command: {' '.join(full_cmd)}\n")
            
            # Run the command with a timeout and capture real-time output
            self.app._console_write(f"[DEBUG] Starting execution...\n")
            
            # Use Popen to capture real-time output
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr with stdout
                text=True,
                bufsize=1,
                cwd=self.app.working_dir,
                env=os.environ.copy(),
                universal_newlines=True
            )
            
            # Read output line by line in real-time
            output_lines = []
            try:
                # Read all output in real-time
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        output_lines.append(line)
                        # Write to console immediately
                        self.app._console_write(f"  {line}")
                
                # Get the return code
                return_code = process.wait(timeout=30)
                
            except subprocess.TimeoutExpired:
                # Command timed out
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                self.app._console_write(f"[MASTER DEMO] ⏰ Command {cmd_idx + 1} timed out after 30 seconds\n")
                raise  # Re-raise to be caught by outer except
            
            # Check exit code
            if return_code == 0:
                self.app._console_write(f"[MASTER DEMO] ✓ Command {cmd_idx + 1} completed successfully\n")
            else:
                self.app._console_write(f"[MASTER DEMO] ✗ Command {cmd_idx + 1} failed with code {return_code}\n")
            
        except subprocess.TimeoutExpired:
            # Already handled above, just continue
            pass
        
        except FileNotFoundError as e:
            self.app._console_write(f"[MASTER DEMO ERROR] File not found: {e}\n")
        
        except Exception as e:
            self.app._console_write(f"[MASTER DEMO ERROR] {type(e).__name__}: {e}\n")
        
        finally:
            # Only advance if we're still at the same command and demo is active
            if (self.master_demo_active and 
                self.current_command_index == cmd_idx):
                
                # Move to next command index
                self.current_command_index += 1
                
                # Schedule next command execution
                self.after(2000, self._execute_next_command)

    def _get_module_from_command(self, command):
        """Extract module name from command list"""
        if not command:
            return "General"
        
        # The module name is usually the first argument
        module_map = {
            "fuzzer": "Fuzzer",
            "lenattack": "LengthAttack",
            "dcm": "DCM",
            "uds": "UDS",
            "listener": "Recon"
        }
        
        return module_map.get(command[0], "General")

    def _stop_master_demo(self):
        """Stop the master demo sequence"""
        self.master_demo_active = False
        
        # Stop current process if running
        if self.master_demo_process:
            try:
                self.master_demo_process.terminate()
                self.master_demo_process = None
            except:
                pass
        
        # Reset button
        self.master_demo_btn.configure(
            text="🚀 Master Demo (Run All Tests)",
            fg_color="#9b59b6"  # Purple color when inactive
        )
        
        # Update progress label
        if self.current_command_index > 0:
            self.progress_label.configure(
                text=f"Stopped after {self.current_command_index} of {len(self.commands_queue)} commands",
                text_color="#e74c3c"
            )
        else:
            self.progress_label.configure(
                text="Master demo stopped",
                text_color="#e74c3c"
            )
        
        self.app._console_write("[MASTER DEMO] Demo sequence stopped by user\n")
        
        # Clear queue
        self.commands_queue = []
        self.current_command_index = 0

    def _complete_master_demo(self):
        """Complete the master demo sequence"""
        self.master_demo_active = False
        
        # Reset button
        self.master_demo_btn.configure(
            text="🚀 Master Demo (Run All Tests)",
            fg_color="#9b59b6"
        )
        
        # Update progress label
        self.progress_label.configure(
            text=f"✅ All {len(self.commands_queue)} commands completed successfully!",
            text_color="#27ae60"
        )
        
        self.app._console_write("\n" + "="*60 + "\n")
        self.app._console_write("[MASTER DEMO] All commands completed successfully!\n")
        self.app._console_write("="*60 + "\n")
        
        # Clear queue
        self.commands_queue = []
        self.current_command_index = 0

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        super()._apply_scaling(scale_factor)
        
        # Scale master demo button
        if hasattr(self, 'master_demo_btn'):
            font = FontConfig.get_button_font(scale_factor)
            width = max(180, int(200 * scale_factor))
            height = max(36, int(40 * scale_factor))
            
            # Maintain semi-circle rounding
            corner_radius = height // 2
            
            self.master_demo_btn.configure(
                font=font,
                width=width,
                height=height,
                corner_radius=corner_radius
            )
        
        # Scale progress label
        if hasattr(self, 'progress_label'):
            font = FontConfig.get_label_font(scale_factor * 0.9)
            self.progress_label.configure(font=font)


class DemoFrame(ScalableFrame):  # Make sure ScalableFrame is properly imported
    def __init__(self, parent, app):
        super().__init__(parent, app)

        # ================= HEADER =================
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(
            self.head_frame,
            text="Demo commands",
            font=FontConfig.get_title_font(1.0)
        )
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        self.help_btn = ctk.CTkButton(
            self.head_frame,
            text="❓",
            fg_color="#f39c12",
            text_color="white",
            command=lambda: app.show_module_help(["demo", "fuzzer", "send"])
        )
        self.help_btn.pack(side="right", padx=5)
        self.register_widget(self.help_btn, "button_small")

        self.report_btn = ctk.CTkButton(
            self.head_frame,
            text="📥 Report (PDF)",
            command=lambda: app.save_module_report("Demo")
        )
        self.report_btn.pack(side="right", padx=5)
        self.register_widget(self.report_btn, "button_small")

        # ================= MAIN CONTAINER =================
        self.button_container = ctk.CTkFrame(self, fg_color="transparent")
        self.button_container.pack(expand=True, fill="both", pady=20)

        # ================= SPEED FUZZ =================
        self.speed_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.speed_frame.pack(pady=10)

        # Store original dimensions for scaling
        self.speed_btn_width = 200  # Original width
        self.speed_btn_height = 45  # Original height
        
        self.speed_btn = ctk.CTkButton(
            self.speed_frame,
            text="▶ Start Speed Fuzz",
            command=self.toggle_speed_fuzz,
            font=FontConfig.get_button_font(1.0),
            width=self.speed_btn_width,
            height=self.speed_btn_height,
            anchor="center",
            fg_color="#1f538d",
            corner_radius=self.speed_btn_height // 2  # Semi-circle (half of height)
        )
        self.speed_btn.pack(side="left", padx=5)
        self.register_widget(self.speed_btn, "button")

        # ================= INDICATOR FUZZ =================
        self.indicator_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.indicator_frame.pack(pady=10)

        self.indicator_btn_width = 200  # Original width
        self.indicator_btn_height = 45  # Original height
        
        self.indicator_btn = ctk.CTkButton(
            self.indicator_frame,
            text="▶ Start Indicator Fuzz",
            command=self.toggle_indicator_fuzz,
            font=FontConfig.get_button_font(1.0),
            width=self.indicator_btn_width,
            height=self.indicator_btn_height,
            anchor="center",
            fg_color="#1f538d",
            corner_radius=self.indicator_btn_height // 2  # Semi-circle
        )
        self.indicator_btn.pack(side="left", padx=5)
        self.register_widget(self.indicator_btn, "button")

        # ================= DOOR FUZZ =================
        self.doors_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.doors_frame.pack(pady=10)

        self.door_btn_width = 200  # Original width
        self.door_btn_height = 45  # Original height
        
        self.door_btn = ctk.CTkButton(
            self.doors_frame,
            text="▶ Start Door Fuzz",
            command=self.toggle_door_fuzz,
            font=FontConfig.get_button_font(1.0),
            width=self.door_btn_width,
            height=self.door_btn_height,
            anchor="center",
            fg_color="#1f538d",
            corner_radius=self.door_btn_height // 2  # Semi-circle
        )
        self.door_btn.pack(side="left", padx=5)
        self.register_widget(self.door_btn, "button")

        # ================= STATE =================
        self.fuzzing_speed_active = False
        self.fuzzing_indicator_active = False
        self.fuzzing_door_active = False

        self.speed_process = None
        self.indicator_process = None
        self.door_process = None

    # ======================================================
    # PROCESS RUNNER
    # ======================================================
    def run_demo_command(self, cmd_args, description):
        try:
            working_dir = self.app.working_dir
            env = os.environ.copy()
            env["PYTHONPATH"] = working_dir + os.pathsep + env.get("PYTHONPATH", "")

            cmd = [sys.executable, "-m", "fucyfuzz.fucyfuzz"] + cmd_args

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=working_dir,
                env=env
            )

            self.app._console_write(f"[DEMO] {description}\n")
            return proc

        except Exception as e:
            self.app._console_write(f"[DEMO ERROR] {e}\n")
            return None

    # ======================================================
    # SPEED FUZZ TOGGLE
    # ======================================================
    def toggle_speed_fuzz(self):
        if not self.fuzzing_speed_active:
            # Start speed fuzzing
            self.fuzzing_speed_active = True
            self.speed_btn.configure(
                text="⏹ Stop Speed Fuzz (Reset to 0)",
                fg_color="#c0392b"
            )
            
            self.speed_process = self.run_demo_command(
                ["fuzzer", "mutate", "244", "..", "-d", "0.5"],
                "Speed fuzz started"
            )
        else:
            # Stop speed fuzzing and reset to 0
            self._stop_speed_fuzz(reset=True)

    def _stop_speed_fuzz(self, reset=True):
        """Stop speed fuzzing and optionally reset"""
        if self.speed_process:
            self.speed_process.terminate()
            self.speed_process = None

        self.fuzzing_speed_active = False
        self.speed_btn.configure(
            text="▶ Start Speed Fuzz",
            fg_color="#1f538d"
        )
        
        if reset:
            self.app._console_write("[DEMO] Speed fuzz stopped and reset to 0\n")
            # Reset speed to 0
            self.run_demo_command(
                ["send", "message", "0x244#00"],
                "Speed reset to 0"
            )
        else:
            self.app._console_write("[DEMO] Speed fuzz stopped\n")

    # ======================================================
    # INDICATOR FUZZ TOGGLE
    # ======================================================
    def toggle_indicator_fuzz(self):
        if not self.fuzzing_indicator_active:
            # Start indicator fuzzing
            self.fuzzing_indicator_active = True
            self.indicator_btn.configure(
                text="⏹ Stop Indicator Fuzz (Reset OFF)",
                fg_color="#c0392b"
            )
            
            self.indicator_process = self.run_demo_command(
                ["fuzzer", "mutate", "188", ".", "-d", "0.5"],
                "Indicator fuzz started"
            )
        else:
            # Stop indicator fuzzing and reset OFF
            self._stop_indicator_fuzz(reset=True)

    def _stop_indicator_fuzz(self, reset=True):
        """Stop indicator fuzzing and optionally reset"""
        if self.indicator_process:
            self.indicator_process.terminate()
            self.indicator_process = None

        self.fuzzing_indicator_active = False
        self.indicator_btn.configure(
            text="▶ Start Indicator Fuzz",
            fg_color="#1f538d"
        )
        
        if reset:
            self.app._console_write("[DEMO] Indicator fuzz stopped and reset OFF\n")
            # Reset indicators OFF
            self.run_demo_command(
                ["send", "message", "0x188#00"],
                "Indicators reset OFF"
            )
        else:
            self.app._console_write("[DEMO] Indicator fuzz stopped\n")

    # ======================================================
    # DOOR FUZZ TOGGLE
    # ======================================================
    def toggle_door_fuzz(self):
        if not self.fuzzing_door_active:
            # Start door fuzzing
            self.fuzzing_door_active = True
            self.door_btn.configure(
                text="⏹ Stop Door Fuzz (Reset Closed)",
                fg_color="#c0392b"
            )
            
            self.door_process = self.run_demo_command(
                ["fuzzer", "mutate", "19B", "........", "-d", "0.5"],
                "Door fuzz started"
            )
        else:
            # Stop door fuzzing and reset closed
            self._stop_door_fuzz(reset=True)

    def _stop_door_fuzz(self, reset=True):
        """Stop door fuzzing and optionally reset"""
        if self.door_process:
            self.door_process.terminate()
            self.door_process = None

        self.fuzzing_door_active = False
        self.door_btn.configure(
            text="▶ Start Door Fuzz",
            fg_color="#1f538d"
        )
        
        if reset:
            self.app._console_write("[DEMO] Door fuzz stopped and reset closed\n")
            # Reset doors to closed
            self.run_demo_command(
                ["send", "message", "0x19B#00.00.00.00"],
                "Doors reset closed"
            )
        else:
            self.app._console_write("[DEMO] Door fuzz stopped\n")

    # ======================================================
    # SCALING
    # ======================================================
    def _apply_scaling(self, scale_factor):
        super()._apply_scaling(scale_factor)

        font = FontConfig.get_button_font(scale_factor)
        
        # Calculate scaled dimensions for each button individually
        speed_width = max(140, int(self.speed_btn_width * scale_factor))
        speed_height = max(40, int(self.speed_btn_height * scale_factor))
        speed_corner_radius = speed_height // 2
        
        indicator_width = max(120, int(self.indicator_btn_width * scale_factor))
        indicator_height = max(32, int(self.indicator_btn_height * scale_factor))
        indicator_corner_radius = indicator_height // 2
        
        door_width = max(120, int(self.door_btn_width * scale_factor))
        door_height = max(32, int(self.door_btn_height * scale_factor))
        door_corner_radius = door_height // 2
        
        # Apply different dimensions to each button
        if self.speed_btn.winfo_exists():
            self.speed_btn.configure(
                font=font, 
                width=speed_width, 
                height=speed_height, 
                corner_radius=speed_corner_radius
            )
        
        if self.indicator_btn.winfo_exists():
            self.indicator_btn.configure(
                font=font, 
                width=indicator_width, 
                height=indicator_height, 
                corner_radius=indicator_corner_radius
            )
        
        if self.door_btn.winfo_exists():
            self.door_btn.configure(
                font=font, 
                width=door_width, 
                height=door_height, 
                corner_radius=door_corner_radius
            )

class FuzzerFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        # Header - SAME AS SENDFRAME
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="Signal Fuzzer", font=FontConfig.get_title_font(1.0))
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        # Header Buttons - EXACT SAME AS SENDFRAME
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("fuzzer"))
        self.help_btn.pack(side="right", padx=(0, 10))
        self.register_widget(self.help_btn, "button_small")

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("Fuzzer"))
        self.report_btn.pack(side="right", padx=(10, 0))
        self.register_widget(self.report_btn, "button_small")

        # Main container - EXACT SAME AS SENDFRAME
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ========== TOP SECTION: 3 Columns ==========
        self.top_section = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.top_section.pack(fill="x", pady=(0, 15))  # SENDFRAME uses pady=(0, 15)
        
        # Column 1: DBC Message
        col1 = ctk.CTkFrame(self.top_section, fg_color="transparent")
        col1.pack(side="left", padx=(0, 15))
        
        dbc_label = ctk.CTkLabel(col1, text="DBC Message:", font=FontConfig.get_label_font(0.9))
        dbc_label.pack(anchor="w")
        self.register_widget(dbc_label, "label")
        
        self.msg_select = ctk.CTkOptionMenu(col1, values=["No DBC Loaded"], 
                                           command=self.on_msg_select,
                                           fg_color="#1f538d", button_color="#1f538d", 
                                           button_hover_color="#14375e", width=180)
        self.msg_select.pack(pady=(2, 0))  # SENDFRAME uses pady=(2, 0)
        self.register_widget(self.msg_select, "dropdown")
        
        # Column 2: Fuzzing Mode
        col2 = ctk.CTkFrame(self.top_section, fg_color="transparent")
        col2.pack(side="left", padx=15)
        
        mode_label = ctk.CTkLabel(col2, text="Fuzzing Mode:", font=FontConfig.get_label_font(0.9))
        mode_label.pack(anchor="w")
        self.register_widget(mode_label, "label")
        
        self.mode = ctk.CTkOptionMenu(col2,
                                     values=["brute", "mutate", "random"],
                                     fg_color="#1f538d", button_color="#1f538d", 
                                     button_hover_color="#14375e", width=180,
                                     command=self.on_mode_change)
        self.mode.pack(pady=(2, 0))
        self.mode.set("brute")
        self.register_widget(self.mode, "dropdown")
        
        # Column 3: Target ID
        col3 = ctk.CTkFrame(self.top_section, fg_color="transparent")
        col3.pack(side="left", padx=(15, 0))
        
        target_label = ctk.CTkLabel(col3, text="Target ID:", font=FontConfig.get_label_font(0.9))
        target_label.pack(anchor="w")
        self.register_widget(target_label, "label")
        
        self.tid = ctk.CTkEntry(col3, placeholder_text="0x123", width=150)
        self.tid.pack(pady=(2, 0))
        self.register_widget(self.tid, "entry")
        
        # ========== MIDDLE SECTION: Data/Random Options ==========
        self.middle_section = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.middle_section.pack(fill="x", pady=(0, 15))  # SENDFRAME uses pady=(0, 15)
        
        # Data Pattern Column - STORE AS INSTANCE ATTRIBUTE
        self.data_col = ctk.CTkFrame(self.middle_section, fg_color="transparent")
        self.data_col.pack(side="left", padx=(0, 15))
        
        data_label = ctk.CTkLabel(self.data_col, text="Data Pattern:", font=FontConfig.get_label_font(0.9))
        data_label.pack(anchor="w")
        self.register_widget(data_label, "label")
        
        self.data = ctk.CTkEntry(self.data_col, placeholder_text="1122..44", width=150)
        self.data.pack(pady=(2, 0))
        self.register_widget(self.data, "entry")
        
        # Random Options Column (initially hidden)
        self.random_col = ctk.CTkFrame(self.middle_section, fg_color="transparent")
        
        random_label = ctk.CTkLabel(self.random_col, text="Random Options:", font=FontConfig.get_label_font(0.9))
        random_label.pack(anchor="w")
        
        # Random options in one row
        random_row = ctk.CTkFrame(self.random_col, fg_color="transparent")
        random_row.pack(fill="x", pady=(2, 0))
        
        min_label = ctk.CTkLabel(random_row, text="Min DLC:", width=60)
        min_label.pack(side="left", padx=(0, 5))
        self.register_widget(min_label, "label")

        self.random_min = ctk.CTkEntry(random_row, placeholder_text="4", width=80)
        self.random_min.pack(side="left", padx=(0, 15))
        self.register_widget(self.random_min, "entry")

        seed_label = ctk.CTkLabel(random_row, text="Seed:", width=40)
        seed_label.pack(side="left", padx=(0, 5))
        self.register_widget(seed_label, "label")

        self.random_seed = ctk.CTkEntry(random_row, placeholder_text="0xabc", width=100)
        self.random_seed.pack(side="left")
        self.register_widget(self.random_seed, "entry")
        
        # Empty column for spacing
        empty_col = ctk.CTkFrame(self.middle_section, fg_color="transparent")
        empty_col.pack(side="left", padx=(15, 0))
        
        # ========== BOTTOM SECTION: Options & Execute ==========
        self.bottom_section = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.bottom_section.pack(fill="x")
        
        # Extra Args Column
        extra_col = ctk.CTkFrame(self.bottom_section, fg_color="transparent")
        extra_col.pack(side="left", padx=(0, 15))
        
        extra_label = ctk.CTkLabel(extra_col, text="Extra Args:", font=FontConfig.get_label_font(0.9))
        extra_label.pack(anchor="w")
        self.register_widget(extra_label, "label")
        
        self.extra_args = ctk.CTkEntry(extra_col, placeholder_text="Optional", width=150)
        self.extra_args.pack(pady=(2, 0))
        self.register_widget(self.extra_args, "entry")
        
        # Interface Checkbox Column
        interface_col = ctk.CTkFrame(self.bottom_section, fg_color="transparent")
        interface_col.pack(side="left", padx=15)
        
        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(interface_col, text="Use -i vcan0",
                                             variable=self.use_interface,
                                             font=FontConfig.get_label_font(0.9))
        self.interface_check.pack(anchor="w", pady=5)
        self.register_widget(self.interface_check, "checkbox")
        
        # Execute Button Column
        button_col = ctk.CTkFrame(self.bottom_section, fg_color="transparent")
        button_col.pack(side="left", padx=(15, 0))
        
        self.execute_btn = ctk.CTkButton(
            button_col,
            text="Execute Fuzzer",
            width=120,
            height=30,
            command=self.run_fuzzer,
            fg_color="#27ae60"  # Green like SendFrame's send button
        )
        self.execute_btn.pack(anchor="w", pady=5)
        self.register_widget(self.execute_btn, "button_large")

        # Initialize UI based on default mode
        self.on_mode_change("brute")

    def on_mode_change(self, selection):
        """Update UI based on fuzzing mode selection"""
        if selection == "random":
            # Hide data pattern, show random options
            self.data_col.pack_forget()
            self.random_col.pack(side="left", padx=15)
        else:
            # Show data pattern, hide random options
            self.data_col.pack(side="left", padx=(0, 15))
            self.random_col.pack_forget()

    def run_fuzzer(self):
        """Execute fuzzer command"""
        mode = self.mode.get()
        tid = self.tid.get().strip()

        if mode != "random" and not tid:
            messagebox.showerror("Error", "Please enter a Target ID")
            return

        cmd = ["fuzzer", mode]

        # Add interface if selected
        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])

        if mode != "random":
            # Add target ID for brute/mutate
            cmd.append(tid)

            # Add data pattern if provided
            data = self.data.get().strip()
            if data:
                cmd.append(data)
        else:
            # For random mode, add random options
            min_val = self.random_min.get().strip()
            if min_val:
                cmd.extend(["-min", min_val])
                
            seed = self.random_seed.get().strip()
            if seed:
                cmd.extend(["-seed", seed])

        # Add extra arguments if provided
        extra_args = self.extra_args.get().strip()
        if extra_args:
            cmd.extend(extra_args.split())

        self.app.run_command(cmd, "Fuzzer")

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")

    def on_msg_select(self, selection):
        hex_id = self.app.get_id_by_name(selection)
        if hex_id:
            self.tid.delete(0, "end")
            self.tid.insert(0, hex_id)

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements - SAME AS SENDFRAME"""
        super()._apply_scaling(scale_factor)
        
        # Scale button - EXACT SAME AS SENDFRAME
        if self.execute_btn.winfo_exists():
            self.execute_btn.configure(
                width=int(120 * scale_factor),
                height=int(30 * scale_factor)
            )
        
        # Scale header buttons - EXACT SAME AS SENDFRAME
        if self.help_btn.winfo_exists():
            self.help_btn.configure(width=FontConfig.get_width("button_small", scale_factor))
        
        if self.report_btn.winfo_exists():
            self.report_btn.configure(width=FontConfig.get_width("button_small", scale_factor))
        
        # Scale dropdowns - SIMILAR TO SENDFRAME
        for dropdown in [self.msg_select, self.mode]:
            if dropdown.winfo_exists():
                dropdown.configure(
                    width=int(180 * scale_factor),
                    font=FontConfig.get_entry_font(scale_factor),
                    dropdown_font=FontConfig.get_entry_font(scale_factor * 0.9)
                )
        
        # Scale entry widths - SIMILAR TO SENDFRAME
        entry_widths = {
            'tid': 150,
            'data': 150,
            'random_min': 80,
            'random_seed': 100,
            'extra_args': 150
        }
        
        for entry_name, base_width in entry_widths.items():
            entry = getattr(self, entry_name, None)
            if entry and entry.winfo_exists():
                entry.configure(width=int(base_width * scale_factor))

class LengthAttackFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="Length Attack", font=FontConfig.get_title_font(1.0))
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        # Header Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("lenattack"))
        self.help_btn.pack(side="right", padx=(0, 10))
        self.register_widget(self.help_btn, "button_small")

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("LengthAttack"))
        self.report_btn.pack(side="right", padx=(10, 0))
        self.register_widget(self.report_btn, "button_small")

        # Main container - Compact
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ========== TOP SECTION: Basic Controls ==========
        self.top_section = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.top_section.pack(fill="x", pady=(0, 15))
        
        # DBC Message selection
        dbc_frame = ctk.CTkFrame(self.top_section, fg_color="transparent")
        dbc_frame.pack(side="left", padx=(0, 15))
        
        dbc_label = ctk.CTkLabel(dbc_frame, text="DBC Message:", font=FontConfig.get_label_font(0.9))
        dbc_label.pack(anchor="w")
        
        self.msg_select = ctk.CTkOptionMenu(dbc_frame, values=["No DBC Loaded"], 
                                           command=self.on_msg_select,
                                           fg_color="#1f538d", button_color="#1f538d", 
                                           button_hover_color="#14375e", width=180)
        self.msg_select.pack(pady=(2, 0))
        self.register_widget(self.msg_select, "dropdown")
        
        # Target ID
        tid_frame = ctk.CTkFrame(self.top_section, fg_color="transparent")
        tid_frame.pack(side="left", padx=15)
        
        target_label = ctk.CTkLabel(tid_frame, text="Target ID:", font=FontConfig.get_label_font(0.9))
        target_label.pack(anchor="w")
        
        self.lid = ctk.CTkEntry(tid_frame, placeholder_text="0x123", width=120)
        self.lid.pack(pady=(2, 0))
        self.register_widget(self.lid, "entry")
        
        # Extra Args
        extra_frame = ctk.CTkFrame(self.top_section, fg_color="transparent")
        extra_frame.pack(side="left", padx=(15, 0))
        
        extra_label = ctk.CTkLabel(extra_frame, text="Extra Args:", font=FontConfig.get_label_font(0.9))
        extra_label.pack(anchor="w")
        
        self.largs = ctk.CTkEntry(extra_frame, placeholder_text="Optional", width=150)
        self.largs.pack(pady=(2, 0))
        self.register_widget(self.largs, "entry")
        
        # ========== MIDDLE SECTION: Attack Options ==========
        self.middle_section = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.middle_section.pack(fill="x", pady=(0, 15))
        
        # Min DLC
        min_dlc_frame = ctk.CTkFrame(self.middle_section, fg_color="transparent")
        min_dlc_frame.pack(side="left", padx=(0, 15))
        
        min_dlc_label = ctk.CTkLabel(min_dlc_frame, text="Min DLC:", font=FontConfig.get_label_font(0.9))
        min_dlc_label.pack(anchor="w")
        
        self.min_dlc_entry = ctk.CTkEntry(min_dlc_frame, placeholder_text="0", width=80)
        self.min_dlc_entry.pack(pady=(2, 0))
        self.register_widget(self.min_dlc_entry, "entry")
        
        # Max DLC
        max_dlc_frame = ctk.CTkFrame(self.middle_section, fg_color="transparent")
        max_dlc_frame.pack(side="left", padx=15)
        
        max_dlc_label = ctk.CTkLabel(max_dlc_frame, text="Max DLC:", font=FontConfig.get_label_font(0.9))
        max_dlc_label.pack(anchor="w")
        
        self.max_dlc_entry = ctk.CTkEntry(max_dlc_frame, placeholder_text="8", width=80)
        self.max_dlc_entry.pack(pady=(2, 0))
        self.register_widget(self.max_dlc_entry, "entry")
        
        # Pattern
        pattern_frame = ctk.CTkFrame(self.middle_section, fg_color="transparent")
        pattern_frame.pack(side="left", padx=(15, 0))
        
        pattern_label = ctk.CTkLabel(pattern_frame, text="Pattern:", font=FontConfig.get_label_font(0.9))
        pattern_label.pack(anchor="w")
        
        self.pattern_entry = ctk.CTkEntry(pattern_frame, placeholder_text="rand", width=100)
        self.pattern_entry.pack(pady=(2, 0))
        self.register_widget(self.pattern_entry, "entry")
        
        # ========== BOTTOM SECTION: Execute Controls ==========
        self.bottom_section = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.bottom_section.pack(fill="x")
        
        # Interface Checkbox
        interface_frame = ctk.CTkFrame(self.bottom_section, fg_color="transparent")
        interface_frame.pack(side="left", padx=(0, 15))
        
        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(interface_frame, text="Use -i vcan0",
                                             variable=self.use_interface,
                                             font=FontConfig.get_label_font(0.9))
        self.interface_check.pack(anchor="w", pady=5)
        self.register_widget(self.interface_check, "checkbox")
        
        # Execute Button
        execute_frame = ctk.CTkFrame(self.bottom_section, fg_color="transparent")
        execute_frame.pack(side="left", padx=(15, 0))
        
        self.start_btn = ctk.CTkButton(
            execute_frame,
            text="START ATTACK",
            width=120,
            height=30,
            command=self.run_attack,
            fg_color="#8e44ad"
        )
        self.start_btn.pack(anchor="w", pady=5)
        self.register_widget(self.start_btn, "button_large")

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        super()._apply_scaling(scale_factor)
        
        # Scale button
        if self.start_btn.winfo_exists():
            self.start_btn.configure(
                width=int(120 * scale_factor),
                height=int(30 * scale_factor)
            )
        
        # Scale header buttons
        if self.help_btn.winfo_exists():
            self.help_btn.configure(width=FontConfig.get_width("button_small", scale_factor))
        
        if self.report_btn.winfo_exists():
            self.report_btn.configure(width=FontConfig.get_width("button_small", scale_factor))
        
        # Scale dropdown
        if self.msg_select.winfo_exists():
            self.msg_select.configure(
                width=int(180 * scale_factor),
                font=FontConfig.get_entry_font(scale_factor),
                dropdown_font=FontConfig.get_entry_font(scale_factor * 0.9)
            )
        
        # Scale entry widths
        entry_widths = {
            'lid': 120,
            'largs': 150,
            'min_dlc_entry': 80,
            'max_dlc_entry': 80,
            'pattern_entry': 100
        }
        
        for entry_name, base_width in entry_widths.items():
            entry = getattr(self, entry_name, None)
            if entry and entry.winfo_exists():
                entry.configure(width=int(base_width * scale_factor))

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")

    def on_msg_select(self, selection):
        """Handle DBC message selection"""
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
        
        # Add common options if specified
        min_dlc = self.min_dlc_entry.get().strip()
        max_dlc = self.max_dlc_entry.get().strip()
        pattern = self.pattern_entry.get().strip()
        
        if min_dlc:
            cmd.extend(["--min-dlc", min_dlc])
        if max_dlc:
            cmd.extend(["--max-dlc", max_dlc])
        if pattern:
            cmd.extend(["--pattern", pattern])
        
        # Add extra args from largs field
        if self.largs.get().strip():
            cmd.extend(self.largs.get().strip().split())
        
        # Add interface if selected
        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])

        self.app.run_command(cmd, "LengthAttack")

class DCMFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="DCM Diagnostics", font=FontConfig.get_title_font(1.0))
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        # Header Buttons - SAME AS LENGTHATTACKFRAME
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("dcm"))
        self.help_btn.pack(side="right", padx=10)
        self.register_widget(self.help_btn, "button_small")

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("DCM"))
        self.report_btn.pack(side="right", padx=10)
        self.register_widget(self.report_btn, "button_small")

        # Main container - COMPACT
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ========== ROW 1: 3 COLUMNS ==========
        self.row1_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.row1_frame.pack(fill="x", pady=(0, 10))
        
        # Column 1: DBC Message
        self.col1_row1 = ctk.CTkFrame(self.row1_frame, fg_color="transparent")
        self.col1_row1.pack(side="left", padx=(0, 10))
        
        dbc_label = ctk.CTkLabel(self.col1_row1, text="DBC:", font=FontConfig.get_label_font(0.9))
        dbc_label.pack(anchor="w")
        self.register_widget(dbc_label, "label")
        
        self.msg_select = ctk.CTkOptionMenu(self.col1_row1, values=["No DBC Loaded"], 
                                           command=self.on_msg_select,
                                           fg_color="#1f538d", button_color="#1f538d", 
                                           button_hover_color="#14375e", width=150)
        self.msg_select.pack(pady=2)
        self.register_widget(self.msg_select, "dropdown")
        
        # Column 2: DCM Action
        self.col2_row1 = ctk.CTkFrame(self.row1_frame, fg_color="transparent")
        self.col2_row1.pack(side="left", padx=10)
        
        action_label = ctk.CTkLabel(self.col2_row1, text="Action:", font=FontConfig.get_label_font(0.9))
        action_label.pack(anchor="w")
        self.register_widget(action_label, "label")
        
        self.dcm_act = ctk.CTkOptionMenu(self.col2_row1,
                                       values=["discovery", "services", "subfunc", "dtc", "testerpresent"],
                                       fg_color="#1f538d", button_color="#1f538d", 
                                       button_hover_color="#14375e", width=150,
                                       command=self.on_dcm_action_change)
        self.dcm_act.pack(pady=2)
        self.dcm_act.set("discovery")
        self.register_widget(self.dcm_act, "dropdown")
        
        # Column 3: Target ID
        self.col3_row1 = ctk.CTkFrame(self.row1_frame, fg_color="transparent")
        self.col3_row1.pack(side="left", padx=(10, 0))
        
        target_label = ctk.CTkLabel(self.col3_row1, text="Target ID:", font=FontConfig.get_label_font(0.9))
        target_label.pack(anchor="w")
        self.register_widget(target_label, "label")
        
        self.dcm_tid = ctk.CTkEntry(self.col3_row1, placeholder_text="0x733", width=120)
        self.dcm_tid.pack(pady=2)
        self.register_widget(self.dcm_tid, "entry")
        
        # ========== ROW 2: 3 COLUMNS ==========
        self.row2_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.row2_frame.pack(fill="x", pady=10)
        
        # Column 1: Response ID
        self.col1_row2 = ctk.CTkFrame(self.row2_frame, fg_color="transparent")
        self.col1_row2.pack(side="left", padx=(0, 10))
        
        self.rid_label = ctk.CTkLabel(self.col1_row2, text="Response ID:", font=FontConfig.get_label_font(0.9))
        self.rid_label.pack(anchor="w")
        self.register_widget(self.rid_label, "label")
        
        self.dcm_rid = ctk.CTkEntry(self.col1_row2, placeholder_text="0x633", width=120)
        self.dcm_rid.pack(pady=2)
        self.register_widget(self.dcm_rid, "entry")
        
        # Column 2: Subfunction Parameters
        self.col2_row2 = ctk.CTkFrame(self.row2_frame, fg_color="transparent")
        self.col2_row2.pack(side="left", padx=10)
        
        self.subfunc_label = ctk.CTkLabel(self.col2_row2, text="Subfunc:", font=FontConfig.get_label_font(0.9))
        self.subfunc_label.pack(anchor="w")
        self.register_widget(self.subfunc_label, "label")
        
        # Subfunction grid inside column 2
        self.subfunc_grid = ctk.CTkFrame(self.col2_row2, fg_color="transparent")
        self.subfunc_grid.pack(pady=2)
        
        service_label = ctk.CTkLabel(self.subfunc_grid, text="Svc:", width=40)
        service_label.grid(row=0, column=0, padx=(0, 2), sticky="w")
        self.register_widget(service_label, "label")

        self.dcm_service = ctk.CTkEntry(self.subfunc_grid, placeholder_text="0x22", width=60)
        self.dcm_service.grid(row=0, column=1, padx=2, sticky="w")
        self.register_widget(self.dcm_service, "entry")

        subfunc_label = ctk.CTkLabel(self.subfunc_grid, text="Sub:", width=30)
        subfunc_label.grid(row=0, column=2, padx=(5, 2), sticky="w")
        self.register_widget(subfunc_label, "label")

        self.dcm_subfunc = ctk.CTkEntry(self.subfunc_grid, placeholder_text="2", width=50)
        self.dcm_subfunc.grid(row=0, column=3, padx=2, sticky="w")
        self.register_widget(self.dcm_subfunc, "entry")

        data_label = ctk.CTkLabel(self.subfunc_grid, text="Data:", width=30)
        data_label.grid(row=0, column=4, padx=(5, 2), sticky="w")
        self.register_widget(data_label, "label")

        self.dcm_data = ctk.CTkEntry(self.subfunc_grid, placeholder_text="3", width=50)
        self.dcm_data.grid(row=0, column=5, padx=2, sticky="w")
        self.register_widget(self.dcm_data, "entry")
        
        # Column 3: Discovery Options
        self.col3_row2 = ctk.CTkFrame(self.row2_frame, fg_color="transparent")
        self.col3_row2.pack(side="left", padx=(10, 0))
        
        # Blacklist
        self.blacklist_label = ctk.CTkLabel(self.col3_row2, text="Blacklist:", font=FontConfig.get_label_font(0.9))
        self.blacklist_label.pack(anchor="w")
        self.register_widget(self.blacklist_label, "label")

        self.dcm_blacklist = ctk.CTkEntry(self.col3_row2, placeholder_text="0x123 0x456", width=120)
        self.dcm_blacklist.pack(pady=2)
        self.register_widget(self.dcm_blacklist, "entry")
        
        # Auto blacklist
        self.autoblacklist_frame = ctk.CTkFrame(self.col3_row2, fg_color="transparent")
        self.autoblacklist_frame.pack(pady=2)

        self.autoblacklist_label = ctk.CTkLabel(self.autoblacklist_frame, text="Auto:", width=40)
        self.autoblacklist_label.pack(side="left", padx=(0, 5))
        self.register_widget(self.autoblacklist_label, "label")

        self.dcm_autoblacklist = ctk.CTkEntry(self.autoblacklist_frame, placeholder_text="10", width=60)
        self.dcm_autoblacklist.pack(side="left")
        self.register_widget(self.dcm_autoblacklist, "entry")
        
        # ========== ROW 3: 3 COLUMNS ==========
        self.row3_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.row3_frame.pack(fill="x", pady=(10, 0))
        
        # Column 1: Extra Args
        self.col1_row3 = ctk.CTkFrame(self.row3_frame, fg_color="transparent")
        self.col1_row3.pack(side="left", padx=(0, 10))
        
        extra_label = ctk.CTkLabel(self.col1_row3, text="Extra Args:", font=FontConfig.get_label_font(0.9))
        extra_label.pack(anchor="w")
        self.register_widget(extra_label, "label")
        
        self.dcm_extra_args = ctk.CTkEntry(self.col1_row3, placeholder_text="Optional", width=120)
        self.dcm_extra_args.pack(pady=2)
        self.register_widget(self.dcm_extra_args, "entry")
        
        # Column 2: Interface Checkbox
        self.col2_row3 = ctk.CTkFrame(self.row3_frame, fg_color="transparent")
        self.col2_row3.pack(side="left", padx=10)
        
        self.dcm_use_interface = ctk.BooleanVar(value=True)
        self.dcm_interface_check = ctk.CTkCheckBox(self.col2_row3, text="-i vcan0",
                                                 variable=self.dcm_use_interface,
                                                 font=FontConfig.get_label_font(0.9))
        self.dcm_interface_check.pack(anchor="w", pady=10)
        self.register_widget(self.dcm_interface_check, "checkbox")
        
        # Column 3: Execute Button
        self.col3_row3 = ctk.CTkFrame(self.row3_frame, fg_color="transparent")
        self.col3_row3.pack(side="left", padx=(5, 0))
        
        self.dcm_execute_btn = ctk.CTkButton(
            self.col3_row3,
            text="Execute DCM",
            width=120,
            height=30,
            command=self.run_dcm,
            fg_color="#8e44ad"
        )
        self.dcm_execute_btn.pack(anchor="w", pady=10)
        self.register_widget(self.dcm_execute_btn, "button_large")

        # Initialize UI based on default action
        self.on_dcm_action_change("discovery")

    def on_dcm_action_change(self, selection):
        """Update DCM UI based on selected action"""
        # Hide/show columns based on action
        
        # For ROW 2: Show/hide columns based on selection
        if selection == "discovery":
            self.col1_row2.pack_forget()
            self.col2_row2.pack_forget()
            self.col3_row2.pack(side="left", padx=(5, 0))
        elif selection in ["services", "dtc"]:
            self.col1_row2.pack(side="left", padx=(0, 5))
            self.col2_row2.pack_forget()
            self.col3_row2.pack_forget()
        elif selection == "subfunc":
            self.col1_row2.pack(side="left", padx=(0, 5))
            self.col2_row2.pack(side="left", padx=5)
            self.col3_row2.pack_forget()
        elif selection == "testerpresent":
            self.col1_row2.pack_forget()
            self.col2_row2.pack_forget()
            self.col3_row2.pack_forget()

    def run_dcm(self):
        """Execute DCM command"""
        action = self.dcm_act.get()
        cmd = ["dcm", action]

        # Add target ID if provided
        tid = self.dcm_tid.get().strip()
        if tid:
            cmd.append(tid)
        elif action != "discovery":
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
        super()._apply_scaling(scale_factor)
        
        # Scale button width
        if self.dcm_execute_btn.winfo_exists():
            self.dcm_execute_btn.configure(
                width=int(120 * scale_factor),
                height=int(30 * scale_factor)
            )
        
        # Scale header buttons - SAME AS LENGTHATTACKFRAME
        if self.help_btn.winfo_exists():
            self.help_btn.configure(width=FontConfig.get_width("button_small", scale_factor))
        
        if self.report_btn.winfo_exists():
            self.report_btn.configure(width=FontConfig.get_width("button_small", scale_factor))
        
        # Scale dropdown widths
        for dropdown in [self.msg_select, self.dcm_act]:
            if dropdown.winfo_exists():
                dropdown.configure(
                    width=int(150 * scale_factor),
                    font=FontConfig.get_entry_font(scale_factor),
                    dropdown_font=FontConfig.get_entry_font(scale_factor * 0.9)
                )
        
        # Scale entry widths
        entry_widths = {
            'dcm_tid': 120,
            'dcm_rid': 120,
            'dcm_service': 60,
            'dcm_subfunc': 50,
            'dcm_data': 50,
            'dcm_blacklist': 120,
            'dcm_autoblacklist': 60,
            'dcm_extra_args': 120
        }
        
        for entry_name, base_width in entry_widths.items():
            entry = getattr(self, entry_name, None)
            if entry and entry.winfo_exists():
                entry.configure(width=int(base_width * scale_factor))

class UDSFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="UDS Diagnostics", font=FontConfig.get_title_font(1.0))
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        # Header Buttons - SAME AS DCMFRAME
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("uds"))
        self.help_btn.pack(side="right", padx=10)
        self.register_widget(self.help_btn, "button_small")

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("UDS"))
        self.report_btn.pack(side="right", padx=10)
        self.register_widget(self.report_btn, "button_small")

        # Main container - COMPACT (SAME AS DCMFRAME)
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ========== ROW 1: 3 COLUMNS ==========
        self.row1_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.row1_frame.pack(fill="x", pady=(0, 10))
        
        # Column 1: DBC Message
        self.col1_row1 = ctk.CTkFrame(self.row1_frame, fg_color="transparent")
        self.col1_row1.pack(side="left", padx=(0, 10))
        
        dbc_label = ctk.CTkLabel(self.col1_row1, text="DBC:", font=FontConfig.get_label_font(0.9))
        dbc_label.pack(anchor="w")
        self.register_widget(dbc_label, "label")
        
        self.msg_select = ctk.CTkOptionMenu(self.col1_row1, values=["No DBC Loaded"], 
                                           command=self.on_msg_select,
                                           fg_color="#1f538d", button_color="#1f538d", 
                                           button_hover_color="#14375e", width=150)
        self.msg_select.pack(pady=2)
        self.register_widget(self.msg_select, "dropdown")
        
        # Column 2: UDS Action
        self.col2_row1 = ctk.CTkFrame(self.row1_frame, fg_color="transparent")
        self.col2_row1.pack(side="left", padx=10)
        
        action_label = ctk.CTkLabel(self.col2_row1, text="Action:", font=FontConfig.get_label_font(0.9))
        action_label.pack(anchor="w")
        self.register_widget(action_label, "label")
        
        self.uds_act = ctk.CTkOptionMenu(self.col2_row1,
                                       values=["discovery", "services", "ecu_reset", "testerpresent", 
                                               "security_seed", "dump_dids", "read_mem"],
                                       fg_color="#1f538d", button_color="#1f538d", 
                                       button_hover_color="#14375e", width=150,
                                       command=self.on_uds_action_change)
        self.uds_act.pack(pady=2)
        self.uds_act.set("discovery")
        self.register_widget(self.uds_act, "dropdown")
        
        # Column 3: Target ID
        self.col3_row1 = ctk.CTkFrame(self.row1_frame, fg_color="transparent")
        self.col3_row1.pack(side="left", padx=(10, 0))
        
        target_label = ctk.CTkLabel(self.col3_row1, text="Target ID:", font=FontConfig.get_label_font(0.9))
        target_label.pack(anchor="w")
        self.register_widget(target_label, "label")
        
        self.uds_tid = ctk.CTkEntry(self.col3_row1, placeholder_text="0x733", width=120)
        self.uds_tid.pack(pady=2)
        self.register_widget(self.uds_tid, "entry")
        
        # ========== ROW 2: 3 COLUMNS ==========
        self.row2_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.row2_frame.pack(fill="x", pady=10)
        
        # Column 1: Response ID
        self.col1_row2 = ctk.CTkFrame(self.row2_frame, fg_color="transparent")
        self.col1_row2.pack(side="left", padx=(0, 10))
        
        self.rid_label = ctk.CTkLabel(self.col1_row2, text="Response ID:", font=FontConfig.get_label_font(0.9))
        self.rid_label.pack(anchor="w")
        self.register_widget(self.rid_label, "label")
        
        self.uds_rid = ctk.CTkEntry(self.col1_row2, placeholder_text="0x633", width=120)
        self.uds_rid.pack(pady=2)
        self.register_widget(self.uds_rid, "entry")
        
        # Column 2: Action Parameters (varies by action)
        self.col2_row2 = ctk.CTkFrame(self.row2_frame, fg_color="transparent")
        self.col2_row2.pack(side="left", padx=10)
        
        # Initialize action-specific frames
        self._init_action_frames()
        
        # Column 3: Discovery Options
        self.col3_row2 = ctk.CTkFrame(self.row2_frame, fg_color="transparent")
        self.col3_row2.pack(side="left", padx=(10, 0))
        
        # Blacklist
        self.blacklist_label = ctk.CTkLabel(self.col3_row2, text="Blacklist:", font=FontConfig.get_label_font(0.9))
        self.blacklist_label.pack(anchor="w")
        self.register_widget(self.blacklist_label, "label")

        self.uds_blacklist = ctk.CTkEntry(self.col3_row2, placeholder_text="0x123 0x456", width=120)
        self.uds_blacklist.pack(pady=2)
        self.register_widget(self.uds_blacklist, "entry")
        
        # Auto blacklist
        self.autoblacklist_frame = ctk.CTkFrame(self.col3_row2, fg_color="transparent")
        self.autoblacklist_frame.pack(pady=2)

        self.autoblacklist_label = ctk.CTkLabel(self.autoblacklist_frame, text="Auto:", width=40)
        self.autoblacklist_label.pack(side="left", padx=(0, 5))
        self.register_widget(self.autoblacklist_label, "label")

        self.uds_autoblacklist = ctk.CTkEntry(self.autoblacklist_frame, placeholder_text="10", width=60)
        self.uds_autoblacklist.pack(side="left")
        self.register_widget(self.uds_autoblacklist, "entry")
        
        # ========== ROW 3: 3 COLUMNS ==========
        self.row3_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.row3_frame.pack(fill="x", pady=(10, 0))
        
        # Column 1: Extra Args
        self.col1_row3 = ctk.CTkFrame(self.row3_frame, fg_color="transparent")
        self.col1_row3.pack(side="left", padx=(0, 10))
        
        extra_label = ctk.CTkLabel(self.col1_row3, text="Extra Args:", font=FontConfig.get_label_font(0.9))
        extra_label.pack(anchor="w")
        self.register_widget(extra_label, "label")
        
        self.uds_extra_args = ctk.CTkEntry(self.col1_row3, placeholder_text="Optional", width=120)
        self.uds_extra_args.pack(pady=2)
        self.register_widget(self.uds_extra_args, "entry")
        
        # Column 2: Interface Checkbox
        self.col2_row3 = ctk.CTkFrame(self.row3_frame, fg_color="transparent")
        self.col2_row3.pack(side="left", padx=10)
        
        self.uds_use_interface = ctk.BooleanVar(value=True)
        self.uds_interface_check = ctk.CTkCheckBox(self.col2_row3, text="-i vcan0",
                                                 variable=self.uds_use_interface,
                                                 font=FontConfig.get_label_font(0.9))
        self.uds_interface_check.pack(anchor="w", pady=10)
        self.register_widget(self.uds_interface_check, "checkbox")
        
        # Column 3: Execute Button
        self.col3_row3 = ctk.CTkFrame(self.row3_frame, fg_color="transparent")
        self.col3_row3.pack(side="left", padx=(5, 0))
        
        self.uds_execute_btn = ctk.CTkButton(
            self.col3_row3,
            text="Execute UDS",
            width=120,
            height=30,
            command=self.run_uds,
            fg_color="#8e44ad"
        )
        self.uds_execute_btn.pack(anchor="w", pady=10)
        self.register_widget(self.uds_execute_btn, "button_large")

        # Initialize UI based on default action
        self.on_uds_action_change("discovery")

    def _init_action_frames(self):
        """Initialize action-specific parameter frames in col2_row2"""
        
        # ECU Reset Frame
        self.ecu_reset_frame = ctk.CTkFrame(self.col2_row2, fg_color="transparent")
        
        ecu_reset_label = ctk.CTkLabel(self.ecu_reset_frame, text="Reset Subfunc:", font=FontConfig.get_label_font(0.9))
        ecu_reset_label.pack(anchor="w")
        
        self.ecu_reset_subfunc = ctk.CTkEntry(self.ecu_reset_frame, placeholder_text="1 (Hard Reset)", width=100)
        self.ecu_reset_subfunc.pack(pady=(2, 0))
        self.register_widget(self.ecu_reset_subfunc, "entry")

        # Security Seed Frame
        self.security_seed_frame = ctk.CTkFrame(self.col2_row2, fg_color="transparent")
        
        # Security parameters in one row
        security_row = ctk.CTkFrame(self.security_seed_frame, fg_color="transparent")
        security_row.pack(fill="x", pady=(0, 8))
        
        level_label = ctk.CTkLabel(security_row, text="Level:", font=FontConfig.get_label_font(0.9))
        level_label.pack(side="left", padx=(0, 5))
        
        self.security_level = ctk.CTkEntry(security_row, placeholder_text="0x3", width=80)
        self.security_level.pack(side="left", padx=(0, 15))
        
        subfunc_label = ctk.CTkLabel(security_row, text="Subfunc:", font=FontConfig.get_label_font(0.9))
        subfunc_label.pack(side="left", padx=(0, 5))
        
        self.security_subfunc = ctk.CTkEntry(security_row, placeholder_text="0x1", width=80)
        self.security_subfunc.pack(side="left")
        
        # Security options
        security_options = ctk.CTkFrame(self.security_seed_frame, fg_color="transparent")
        security_options.pack(fill="x")
        
        self.retry_var = ctk.BooleanVar(value=True)
        self.retry_check = ctk.CTkCheckBox(security_options, text="Retry", 
                                          variable=self.retry_var,
                                          font=FontConfig.get_label_font(0.9))
        self.retry_check.pack(side="left", padx=(0, 15))
        
        delay_label = ctk.CTkLabel(security_options, text="Delay:", font=FontConfig.get_label_font(0.9))
        delay_label.pack(side="left", padx=(0, 5))
        
        self.security_delay = ctk.CTkEntry(security_options, placeholder_text="0.5", width=80)
        self.security_delay.pack(side="left")
        
        self.register_widget(self.security_level, "entry")
        self.register_widget(self.security_subfunc, "entry")
        self.register_widget(self.retry_check, "checkbox")
        self.register_widget(self.security_delay, "entry")

        # Memory Frame
        self.memory_frame = ctk.CTkFrame(self.col2_row2, fg_color="transparent")
        
        # Memory parameters in one row
        memory_row = ctk.CTkFrame(self.memory_frame, fg_color="transparent")
        memory_row.pack(fill="x")
        
        start_label = ctk.CTkLabel(memory_row, text="Start:", font=FontConfig.get_label_font(0.9))
        start_label.pack(side="left", padx=(0, 5))
        
        self.start_addr = ctk.CTkEntry(memory_row, placeholder_text="0x0200", width=100)
        self.start_addr.pack(side="left", padx=(0, 15))
        
        length_label = ctk.CTkLabel(memory_row, text="Length:", font=FontConfig.get_label_font(0.9))
        length_label.pack(side="left", padx=(0, 5))
        
        self.mem_length = ctk.CTkEntry(memory_row, placeholder_text="0x10000", width=100)
        self.mem_length.pack(side="left")
        
        self.register_widget(self.start_addr, "entry")
        self.register_widget(self.mem_length, "entry")

        # DID Range Frame
        self.did_range_frame = ctk.CTkFrame(self.col2_row2, fg_color="transparent")
        
        # DID range in one row
        did_range_row = ctk.CTkFrame(self.did_range_frame, fg_color="transparent")
        did_range_row.pack(fill="x", pady=(0, 8))
        
        min_label = ctk.CTkLabel(did_range_row, text="Min DID:", font=FontConfig.get_label_font(0.9))
        min_label.pack(side="left", padx=(0, 5))
        
        self.min_did = ctk.CTkEntry(did_range_row, placeholder_text="0x6300", width=100)
        self.min_did.pack(side="left", padx=(0, 15))
        
        max_label = ctk.CTkLabel(did_range_row, text="Max DID:", font=FontConfig.get_label_font(0.9))
        max_label.pack(side="left", padx=(0, 5))
        
        self.max_did = ctk.CTkEntry(did_range_row, placeholder_text="0x6FFF", width=100)
        self.max_did.pack(side="left")
        
        # Timeout
        timeout_frame = ctk.CTkFrame(self.did_range_frame, fg_color="transparent")
        timeout_frame.pack(fill="x")
        
        timeout_label = ctk.CTkLabel(timeout_frame, text="Timeout (s):", font=FontConfig.get_label_font(0.9))
        timeout_label.pack(side="left", padx=(0, 5))
        
        self.did_timeout = ctk.CTkEntry(timeout_frame, placeholder_text="0.1", width=80)
        self.did_timeout.pack(side="left")
        
        self.register_widget(self.min_did, "entry")
        self.register_widget(self.max_did, "entry")
        self.register_widget(self.did_timeout, "entry")

    def on_uds_action_change(self, selection):
        """Update UDS UI based on selected action - SAME LOGIC AS DCM"""
        # Hide all optional sections first
        self.col1_row2.pack_forget()
        self.col2_row2.pack_forget()
        self.col3_row2.pack_forget()
        
        if selection == "discovery":
            # Show only blacklist options
            self.col3_row2.pack(side="left", padx=(5, 0))
            
        elif selection in ["services", "testerpresent"]:
            # Show response ID
            self.col1_row2.pack(side="left", padx=(0, 5))
            
        elif selection == "ecu_reset":
            # Show response ID and ECU reset
            self.col1_row2.pack(side="left", padx=(0, 5))
            self.col2_row2.pack(side="left", padx=5)
            self.ecu_reset_frame.pack(fill="x")
            self.security_seed_frame.pack_forget()
            self.memory_frame.pack_forget()
            self.did_range_frame.pack_forget()
            
        elif selection == "security_seed":
            # Show response ID and security parameters
            self.col1_row2.pack(side="left", padx=(0, 5))
            self.col2_row2.pack(side="left", padx=5)
            self.ecu_reset_frame.pack_forget()
            self.security_seed_frame.pack(fill="x")
            self.memory_frame.pack_forget()
            self.did_range_frame.pack_forget()
            
        elif selection == "dump_dids":
            # Show response ID and DID range
            self.col1_row2.pack(side="left", padx=(0, 5))
            self.col2_row2.pack(side="left", padx=5)
            self.ecu_reset_frame.pack_forget()
            self.security_seed_frame.pack_forget()
            self.memory_frame.pack_forget()
            self.did_range_frame.pack(fill="x")
            
        elif selection == "read_mem":
            # Show response ID and memory parameters
            self.col1_row2.pack(side="left", padx=(0, 5))
            self.col2_row2.pack(side="left", padx=5)
            self.ecu_reset_frame.pack_forget()
            self.security_seed_frame.pack_forget()
            self.memory_frame.pack(fill="x")
            self.did_range_frame.pack_forget()

    def run_uds(self):
        """Execute UDS command"""
        action = self.uds_act.get()
        cmd = ["uds", action]

        # Add target ID if provided
        tid = self.uds_tid.get().strip()
        if tid:
            cmd.append(tid)
        elif action != "discovery":  # discovery can work without target ID
            messagebox.showerror("Error", "Target ID is required for this action")
            return

        # Action-specific parameters
        if action in ["services", "dump_dids", "read_mem", "ecu_reset", "security_seed"]:
            rid = self.uds_rid.get().strip()
            if rid:
                cmd.append(rid)
            elif action != "testerpresent":  # testerpresent doesn't need response ID
                messagebox.showerror("Error", "Response ID is required for this action")
                return

        if action == "ecu_reset":
            # Add reset subfunction
            subfunc = self.ecu_reset_subfunc.get().strip()
            if subfunc:
                cmd.append(subfunc)

        elif action == "security_seed":
            # Add security parameters
            level = self.security_level.get().strip()
            subfunc = self.security_subfunc.get().strip()
            
            if level:
                cmd.append(level)
            else:
                messagebox.showerror("Error", "Security level is required for security_seed")
                return
                
            if subfunc:
                cmd.append(subfunc)
            
            # Add options
            if self.retry_var.get():
                cmd.append("-r")
                cmd.append("1")
                
            delay = self.security_delay.get().strip()
            if delay:
                cmd.extend(["-d", delay])

        elif action == "dump_dids":
            # Add DID range parameters
            min_did = self.min_did.get().strip()
            max_did = self.max_did.get().strip()
            timeout = self.did_timeout.get().strip()
            
            if min_did:
                cmd.extend(["--min_did", min_did])
            if max_did:
                cmd.extend(["--max_did", max_did])
            if timeout:
                cmd.extend(["-t", timeout])

        elif action == "read_mem":
            # Add memory parameters
            start_addr = self.start_addr.get().strip()
            mem_length = self.mem_length.get().strip()
            
            if start_addr:
                cmd.extend(["--start_addr", start_addr])
            if mem_length:
                cmd.extend(["--mem_length", mem_length])

        # Add blacklist options for discovery
        if action == "discovery":
            blacklist = self.uds_blacklist.get().strip()
            if blacklist:
                cmd.extend(["-blacklist"] + blacklist.split())

            autoblacklist = self.uds_autoblacklist.get().strip()
            if autoblacklist:
                cmd.extend(["-autoblacklist", autoblacklist])

        # Add extra arguments if provided
        extra_args = self.uds_extra_args.get().strip()
        if extra_args:
            cmd.extend(extra_args.split())

        # Add interface if checkbox is checked
        if self.uds_use_interface.get():
            cmd.extend(["-i", "vcan0"])

        self.app.run_command(cmd, "UDS")

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")

    def on_msg_select(self, selection):
        hex_id = self.app.get_id_by_name(selection)
        if hex_id:
            self.uds_tid.delete(0, "end")
            self.uds_tid.insert(0, hex_id)

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements - SAME AS DCMFRAME"""
        super()._apply_scaling(scale_factor)
        
        # Scale button width
        if self.uds_execute_btn.winfo_exists():
            self.uds_execute_btn.configure(
                width=int(120 * scale_factor),
                height=int(30 * scale_factor)
            )
        
        # Scale header buttons - SAME AS DCMFRAME
        if self.help_btn.winfo_exists():
            self.help_btn.configure(width=FontConfig.get_width("button_small", scale_factor))
        
        if self.report_btn.winfo_exists():
            self.report_btn.configure(width=FontConfig.get_width("button_small", scale_factor))
        
        # Scale dropdown widths
        for dropdown in [self.msg_select, self.uds_act]:
            if dropdown.winfo_exists():
                dropdown.configure(
                    width=int(150 * scale_factor),
                    font=FontConfig.get_entry_font(scale_factor),
                    dropdown_font=FontConfig.get_entry_font(scale_factor * 0.9)
                )
        
        # Scale entry widths - SAME PATTERN AS DCMFRAME
        entry_widths = {
            'uds_tid': 120,
            'uds_rid': 120,
            'ecu_reset_subfunc': 100,
            'security_level': 80,
            'security_subfunc': 80,
            'security_delay': 80,
            'start_addr': 100,
            'mem_length': 100,
            'min_did': 100,
            'max_did': 100,
            'did_timeout': 80,
            'uds_blacklist': 120,
            'uds_autoblacklist': 60,
            'uds_extra_args': 120
        }
        
        for entry_name, base_width in entry_widths.items():
            entry = getattr(self, entry_name, None)
            if entry and entry.winfo_exists():
                entry.configure(width=int(base_width * scale_factor))

class AdvancedFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="Advanced", font=FontConfig.get_title_font(1.0))
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        # Header Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help(["doip", "xcp", "uds"]))
        self.help_btn.pack(side="right", padx=5)
        self.register_widget(self.help_btn, "button_small")

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("Advanced"))
        self.report_btn.pack(side="right", padx=5)
        self.register_widget(self.report_btn, "button_small")

        # Create notebook for different advanced functions
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, pady=10)

        # Tab 1: DoIP
        self.doip_tab = self.tabs.add("DoIP")
        self._setup_doip_tab()

        # Tab 2: XCP
        self.xcp_tab = self.tabs.add("XCP")
        self._setup_xcp_tab()

        # Tab 3: UDS DID Reader with LEFT-RIGHT layout
        self.did_tab = self.tabs.add("DID Reader")
        self._setup_did_tab()

    def _setup_doip_tab(self):
        """Setup DoIP tab with 3-column layout"""
        self.doip_main_frame = ctk.CTkFrame(self.doip_tab, fg_color="transparent")
        self.doip_main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Description
        desc_label = ctk.CTkLabel(self.doip_main_frame, 
                                 text="DoIP (Diagnostics over IP) Discovery",
                                 font=FontConfig.get_label_font(1.0, bold=True))
        desc_label.pack(anchor="w", pady=(0, 15))
        self.register_widget(desc_label, "label")
        
        # Row: 3 columns
        self.doip_row_frame = ctk.CTkFrame(self.doip_main_frame, fg_color="transparent")
        self.doip_row_frame.pack(fill="x", pady=10)
        
        # Column 1: Interface checkbox
        self.doip_interface_col = ctk.CTkFrame(self.doip_row_frame, fg_color="transparent")
        self.doip_interface_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.doip_use_interface = ctk.BooleanVar(value=True)
        self.doip_interface_check = ctk.CTkCheckBox(self.doip_interface_col, 
                                                   text="Use -i vcan0 interface",
                                                   variable=self.doip_use_interface)
        self.doip_interface_check.pack(anchor="w")
        self.register_widget(self.doip_interface_check, "checkbox")
        
        # Column 2: Spacer
        self.doip_spacer_col = ctk.CTkFrame(self.doip_row_frame, fg_color="transparent")
        self.doip_spacer_col.pack(side="left", fill="both", expand=True, padx=10)
        
        # Column 3: DoIP Button
        self.doip_button_col = ctk.CTkFrame(self.doip_row_frame, fg_color="transparent")
        self.doip_button_col.pack(side="left", fill="both", expand=True, padx=(10, 0))
        
        self.doip_btn = ctk.CTkButton(
            self.doip_button_col,
            text="DoIP Discovery",
            width=FontConfig.get_width("button_large", 1.0),
            command=self.run_doip,
            fg_color="#3498db"
        )
        self.doip_btn.pack()
        self.register_widget(self.doip_btn, "button_large")

    def _setup_xcp_tab(self):
        """Setup XCP tab with 3-column layout"""
        self.xcp_main_frame = ctk.CTkFrame(self.xcp_tab, fg_color="transparent")
        self.xcp_main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Description
        desc_label = ctk.CTkLabel(self.xcp_main_frame, 
                                 text="XCP (Universal Measurement and Calibration Protocol)",
                                 font=FontConfig.get_label_font(1.0, bold=True))
        desc_label.pack(anchor="w", pady=(0, 15))
        self.register_widget(desc_label, "label")
        
        # Row: 3 columns
        self.xcp_row_frame = ctk.CTkFrame(self.xcp_main_frame, fg_color="transparent")
        self.xcp_row_frame.pack(fill="x", pady=10)
        
        # Column 1: XCP ID Entry
        self.xcp_id_col = ctk.CTkFrame(self.xcp_row_frame, fg_color="transparent")
        self.xcp_id_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        xcp_id_label = ctk.CTkLabel(self.xcp_id_col, text="XCP ID (Hex):")
        xcp_id_label.pack(anchor="w")
        self.register_widget(xcp_id_label, "label")
        
        self.xcp_id = ctk.CTkEntry(self.xcp_id_col, placeholder_text="e.g., 0x123")
        self.xcp_id.pack(fill="x", pady=5)
        self.register_widget(self.xcp_id, "entry")
        
        # Column 2: Interface checkbox
        self.xcp_interface_col = ctk.CTkFrame(self.xcp_row_frame, fg_color="transparent")
        self.xcp_interface_col.pack(side="left", fill="both", expand=True, padx=10)
        
        self.xcp_use_interface = ctk.BooleanVar(value=True)
        self.xcp_interface_check = ctk.CTkCheckBox(self.xcp_interface_col, 
                                                  text="Use -i vcan0 interface",
                                                  variable=self.xcp_use_interface)
        self.xcp_interface_check.pack(anchor="w", pady=(20, 0))
        self.register_widget(self.xcp_interface_check, "checkbox")
        
        # Column 3: XCP Button
        self.xcp_button_col = ctk.CTkFrame(self.xcp_row_frame, fg_color="transparent")
        self.xcp_button_col.pack(side="left", fill="both", expand=True, padx=(10, 0))
        
        self.xcp_btn = ctk.CTkButton(
            self.xcp_button_col,
            text="XCP Info",
            width=FontConfig.get_width("button_large", 1.0),
            command=self.run_xcp,
            fg_color="#3498db"
        )
        self.xcp_btn.pack(pady=(20, 0))
        self.register_widget(self.xcp_btn, "button_large")

    def _setup_did_tab(self):
        """Setup UDS DID Reader tab with LEFT-RIGHT layout"""
        # Main container with left-right split with more padding
        self.did_main_frame = ctk.CTkFrame(self.did_tab, fg_color="transparent")
        self.did_main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ========== LEFT PANEL: Controls ==========
        self.left_panel = ctk.CTkFrame(self.did_main_frame, fg_color="transparent")
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 15))
        
        # DID Selection with spacing
        did_select_label = ctk.CTkLabel(self.left_panel, text="Select DID to Read:")
        did_select_label.pack(anchor="w", pady=(0, 10))
        self.register_widget(did_select_label, "label")

        # COMPACT dropdown with increased width
        self.did_select = ctk.CTkOptionMenu(
            self.left_panel,
            values=[
                "Single DID: 0xF190 - VIN",
                "Single DID: 0xF180 - Boot SW",
                "Single DID: 0xF181 - App SW",
                "Single DID: 0xF186 - Session",
                "Single DID: 0xF187 - Part No",
                "Single DID: 0xF188 - ECU SW",
                "Single DID: 0xF198 - Shop Code",
                "Single DID: 0xF18C - Serial No",
                "Custom DID",
                "Scan Range: F180-F1FF"
            ],
            command=self.on_did_selection_change,
            fg_color="#1f538d",
            button_color="#1f538d",
            button_hover_color="#14375e",
            width=450,
            dynamic_resizing=False
        )
        self.did_select.pack(anchor="w", pady=(0, 20))
        self.did_select.set("Single DID: 0xF190 - VIN")
        self.register_widget(self.did_select, "dropdown")
        
        # Custom DID Frame
        self.custom_did_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        
        custom_label = ctk.CTkLabel(self.custom_did_frame, text="Custom DID:")
        custom_label.pack(anchor="w", pady=(0, 8))
        self.register_widget(custom_label, "label")

        self.custom_did_entry = ctk.CTkEntry(self.custom_did_frame, placeholder_text="F190 (no 0x)")
        self.custom_did_entry.pack(fill="x", pady=(0, 20))
        self.register_widget(self.custom_did_entry, "entry")
        
        # Range Frame
        self.range_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        
        range_label = ctk.CTkLabel(self.range_frame, text="DID Range:")
        range_label.pack(anchor="w", pady=(0, 10))
        self.register_widget(range_label, "label")
        
        # Start and End in one row
        range_row = ctk.CTkFrame(self.range_frame, fg_color="transparent")
        range_row.pack(fill="x", pady=(0, 20))
        
        start_label = ctk.CTkLabel(range_row, text="Start:", width=60)
        start_label.pack(side="left", padx=(0, 10))
        self.register_widget(start_label, "label")

        self.start_did_entry = ctk.CTkEntry(range_row, placeholder_text="F180", width=130)
        self.start_did_entry.pack(side="left", padx=(0, 20))
        self.register_widget(self.start_did_entry, "entry")

        end_label = ctk.CTkLabel(range_row, text="End:", width=60)
        end_label.pack(side="left", padx=(0, 10))
        self.register_widget(end_label, "label")

        self.end_did_entry = ctk.CTkEntry(range_row, placeholder_text="F1FF", width=130)
        self.end_did_entry.pack(side="left")
        self.register_widget(self.end_did_entry, "entry")
        
        # Target/Response IDs in one row
        ids_row = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        ids_row.pack(fill="x", pady=(0, 20))
        
        target_label = ctk.CTkLabel(ids_row, text="Target ID:", width=80)
        target_label.pack(side="left", padx=(0, 10))
        self.register_widget(target_label, "label")

        self.uds_target_id = ctk.CTkEntry(ids_row, placeholder_text="0x7E0", width=150)
        self.uds_target_id.insert(0, "0x7E0")
        self.uds_target_id.pack(side="left", padx=(0, 20))
        self.register_widget(self.uds_target_id, "entry")

        response_label = ctk.CTkLabel(ids_row, text="Resp ID:", width=70)
        response_label.pack(side="left", padx=(0, 10))
        self.register_widget(response_label, "label")

        self.uds_response_id = ctk.CTkEntry(ids_row, placeholder_text="0x7E8", width=150)
        self.uds_response_id.insert(0, "0x7E8")
        self.uds_response_id.pack(side="left")
        self.register_widget(self.uds_response_id, "entry")
        
        # Timeout and Interface in one row
        options_row = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        options_row.pack(fill="x", pady=(0, 20))
        
        timeout_label = ctk.CTkLabel(options_row, text="Timeout (s):", width=80)
        timeout_label.pack(side="left", padx=(0, 10))
        self.register_widget(timeout_label, "label")

        self.timeout_entry = ctk.CTkEntry(options_row, placeholder_text="0.2", width=130)
        self.timeout_entry.insert(0, "0.2")
        self.timeout_entry.pack(side="left", padx=(0, 30))
        self.register_widget(self.timeout_entry, "entry")
        
        self.did_use_interface = ctk.BooleanVar(value=True)
        self.did_interface_check = ctk.CTkCheckBox(options_row, 
                                                  text="-i vcan0",
                                                  variable=self.did_use_interface,
                                                  width=100)
        self.did_interface_check.pack(side="left", padx=(0, 10))
        self.register_widget(self.did_interface_check, "checkbox")
        
        # ========== SINGLE READ BUTTON ==========
        button_container = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        button_container.pack(fill="x", pady=(0, 15))
        
        self.did_read_btn = ctk.CTkButton(
            button_container,
            text="🔍 Read DID & Display Response",
            width=250,
            height=FontConfig.get_height("button", 1.0),
            command=self.read_did_and_show_response,
            fg_color="#8e44ad"
        )
        self.did_read_btn.pack(anchor="w")
        self.register_widget(self.did_read_btn, "button")
        
        # ========== RIGHT PANEL: Response Display ==========
        self.right_panel = ctk.CTkFrame(self.did_main_frame, fg_color="transparent")
        self.right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        # Response header
        response_header = ctk.CTkLabel(self.right_panel, text="Response Display", 
                                      font=FontConfig.get_label_font(1.0, bold=True))
        response_header.pack(anchor="w", pady=(0, 10))
        self.register_widget(response_header, "label")
        
        # Status label
        self.status_label = ctk.CTkLabel(self.right_panel, text="Ready to read DID...", 
                                        font=FontConfig.get_label_font(0.9),
                                        text_color="#7f8c8d")
        self.status_label.pack(anchor="w", pady=(0, 5))
        self.register_widget(self.status_label, "label")
        
        # Response textbox
        self.response_text = ctk.CTkTextbox(self.right_panel, font=FontConfig.get_mono_font(1.0))
        self.response_text.pack(fill="both", expand=True, padx=(5, 0))
        self.register_widget(self.response_text, "textbox")
        
        # Initialize UI state
        self.on_did_selection_change("Single DID: 0xF190 - VIN")

    # ==================== METHODS ====================
    
    def run_doip(self):
        """Run DoIP with optional interface"""
        cmd = ["doip", "discovery"]
        if self.doip_use_interface.get():
            cmd.extend(["-i", "vcan0"])
        self.app.run_command(cmd, "Advanced")

    def run_xcp(self):
        """Run XCP with optional interface"""
        xcp_id = self.xcp_id.get().strip()
        if not xcp_id:
            messagebox.showerror("Error", "Please enter an XCP ID")
            return

        cmd = ["xcp", "info", xcp_id]
        if self.xcp_use_interface.get():
            cmd.extend(["-i", "vcan0"])
        self.app.run_command(cmd, "Advanced")

    def on_did_selection_change(self, selection):
        """Show/hide custom DID entry based on selection"""
        # Hide all optional frames first
        self.custom_did_frame.pack_forget()
        self.range_frame.pack_forget()

        if selection == "Custom DID":
            self.custom_did_frame.pack(fill="x", pady=(0, 15))
        elif "Scan Range:" in selection:
            # Pre-fill the range for manufacturer DIDs
            self.start_did_entry.delete(0, "end")
            self.end_did_entry.delete(0, "end")
            self.start_did_entry.insert(0, "F180")
            self.end_did_entry.insert(0, "F1FF")
            self.range_frame.pack(fill="x", pady=(0, 15))

    def read_did_and_show_response(self):
        """Execute UDS DID read command and automatically show response"""
        # Clear previous response
        self.response_text.delete("1.0", "end")
        self.status_label.configure(text="Reading DID...", text_color="#3498db")
        
        # Get target ID
        target_id = self.uds_target_id.get().strip()

        if not target_id:
            messagebox.showerror("Error", "Please enter a Target ECU ID")
            self.status_label.configure(text="Error: No Target ID", text_color="#e74c3c")
            return

        # Ensure target_id has 0x prefix
        if not target_id.startswith("0x"):
            target_id = "0x" + target_id

        # Get selected DID
        selection = self.did_select.get()

        if selection == "Custom DID":
            did_hex = self.custom_did_entry.get().strip()
            if not did_hex:
                messagebox.showerror("Error", "Please enter a custom DID")
                self.status_label.configure(text="Error: No DID entered", text_color="#e74c3c")
                return
            # Remove 0x prefix if present
            did_hex = did_hex.replace("0x", "")
            # Ensure it's 4 hex digits
            if len(did_hex) != 4:
                messagebox.showerror("Error", "DID must be 4 hex digits (e.g., F190)")
                self.status_label.configure(text="Error: Invalid DID format", text_color="#e74c3c")
                return
            did_bytes = did_hex.upper()

        elif "Single DID:" in selection:
            # Extract DID from the option text
            # e.g., "Single DID: 0xF190 - VIN" -> "F190"
            did_full = selection.split(": ")[1].split(" - ")[0]  # "0xF190"
            did_bytes = did_full[2:].upper()  # "F190"

        elif "Scan Range:" in selection:
            # For range scanning, use the dump_dids command
            self.read_did_range()
            return
        else:
            messagebox.showerror("Error", "Invalid selection")
            self.status_label.configure(text="Error: Invalid selection", text_color="#e74c3c")
            return

        # Get response ID
        response_id = self.uds_response_id.get().strip() or "0x7E8"
        
        # Get timeout value
        timeout = "0.5"
        if hasattr(self, 'timeout_entry'):
            timeout_val = self.timeout_entry.get().strip()
            if timeout_val:
                timeout = timeout_val
        
        # Store the DID for later use
        self.last_did_hex = did_bytes
        self.last_target_id = target_id
        self.last_response_id = response_id
        
        # Update response display with request info
        self.response_text.insert("1.0", f"📤 UDS Request Details\n")
        self.response_text.insert("end", "="*50 + "\n")
        self.response_text.insert("end", f"Target ID: {target_id}\n")
        self.response_text.insert("end", f"Response ID: {response_id}\n")
        self.response_text.insert("end", f"DID: 0x{did_bytes}\n")
        self.response_text.insert("end", f"Service: 0x22 (Read Data By Identifier)\n\n")
        self.response_text.insert("end", "⏳ Sending request and awaiting response...\n")
        
        try:
            # Build the UDS dump_dids command for specific DID
            did_int = int(did_bytes, 16)
            
            cmd = ["uds", "dump_dids", target_id, response_id,
                   "--min_did", f"0x{did_int:04X}",
                   "--max_did", f"0x{did_int:04X}",
                   "-t", timeout]
            
            # Add interface if selected
            if self.did_use_interface.get():
                cmd.extend(["-i", "vcan0"])
            
            # Show the command
            self.response_text.insert("end", f"\n🔧 Command: python -m fucyfuzz.fucyfuzz {' '.join(cmd)}\n")
            self.response_text.insert("end", "-"*50 + "\n\n")
            
            # Run command in background thread
            threading.Thread(target=self._execute_and_display_response, 
                           args=(cmd, did_int), daemon=True).start()
            
            # Also send the raw CAN frame for the request
            self._send_can_request(target_id, did_bytes)
            
        except Exception as e:
            error_msg = f"\n❌ Error: {str(e)}\n"
            self.response_text.insert("end", error_msg)
            self.status_label.configure(text=f"Error: {str(e)}", text_color="#e74c3c")

    def _send_can_request(self, target_id, did_bytes):
        """Send the raw CAN request frame"""
        try:
            # Build the CAN frame in the correct format
            did_high_byte = did_bytes[0:2].lower()
            did_low_byte = did_bytes[2:4].lower()

            # Create the CAN frame
            can_frame = f"{target_id}#03.22.{did_high_byte}.{did_low_byte}.00.00.00.00"

            # Build the send command
            cmd = ["send", "message", can_frame]

            # Add interface if selected
            if self.did_use_interface.get():
                cmd.extend(["-i", "vcan0"])

            # Run the command in a separate thread
            threading.Thread(
                target=self.app.run_command,
                args=(cmd, "UDS_DID_Reader"),
                daemon=True
            ).start()
            
        except Exception as e:
            self.response_text.insert("end", f"\n⚠️ Failed to send CAN request: {str(e)}\n")

    def _execute_and_display_response(self, cmd, did_int):
        """Execute command and display results in real-time"""
        working_dir = self.app.working_dir
        env = os.environ.copy()
        env["PYTHONPATH"] = working_dir + os.pathsep + env.get("PYTHONPATH", "")
        
        try:
            # Build the full command
            full_cmd = [sys.executable, "-m", "fucyfuzz.fucyfuzz"] + cmd
            
            # Update UI
            self.after(0, lambda: self.status_label.configure(
                text="Executing UDS command...", 
                text_color="#3498db"))
            
            self.after(0, lambda: self.response_text.insert("end", "🚀 Starting UDS command...\n"))
            
            # Run subprocess
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=working_dir,
                env=env,
                universal_newlines=True
            )
            
            output_lines = []
            
            # Read output in real-time
            for line in iter(process.stdout.readline, ''):
                output_lines.append(line)
                # Update UI with each line
                self.after(0, lambda l=line: self._update_response_display(l))
            
            process.wait()
            
            # Process the output
            full_output = "".join(output_lines)
            
            if process.returncode == 0:
                self.after(0, lambda: self.status_label.configure(
                    text="Command completed successfully", 
                    text_color="#27ae60"))
                self.after(0, lambda: self.response_text.insert("end", f"\n✅ Command completed successfully\n"))
                self.after(0, lambda: self._parse_and_display_uds_response(full_output, did_int))
            else:
                self.after(0, lambda: self.status_label.configure(
                    text=f"Command failed (code: {process.returncode})", 
                    text_color="#e74c3c"))
                self.after(0, lambda: self.response_text.insert("end", 
                    f"\n⚠️ Command failed with exit code: {process.returncode}\n"))
                self.after(0, lambda: self._display_raw_output(full_output))
                
        except Exception as e:
            error_msg = f"\n❌ Error running command: {str(e)}\n"
            self.after(0, lambda: self.status_label.configure(
                text=f"Error: {str(e)}", 
                text_color="#e74c3c"))
            self.after(0, lambda: self.response_text.insert("end", error_msg))

    def _update_response_display(self, line):
        """Update response display with a new line"""
        self.response_text.insert("end", f"  {line}")
        self.response_text.see("end")

    def _parse_and_display_uds_response(self, output, did_int):
        """Parse UDS response and display decoded information"""
        self.response_text.insert("end", "\n" + "="*50 + "\n")
        self.response_text.insert("end", "📊 UDS RESPONSE DECODED\n")
        self.response_text.insert("end", "="*50 + "\n\n")
        
        # Look for DID data in the output
        lines = output.split('\n')
        found_response = False
        
        for line in lines:
            line = line.strip()
            
            # Look for the specific DID in the output
            if f"0x{did_int:04X}".lower() in line.lower():
                self.response_text.insert("end", f"🔍 Found response for DID 0x{did_int:04X}:\n")
                self.response_text.insert("end", f"   {line}\n\n")
                found_response = True
                
                # Try to extract and decode hex data
                parts = line.split()
                hex_data = []
                
                for part in parts:
                    # Look for 2-character hex strings
                    if len(part) == 2 and all(c in "0123456789abcdefABCDEF" for c in part):
                        try:
                            hex_data.append(int(part, 16))
                        except:
                            pass
                
                if hex_data:
                    self.response_text.insert("end", "🔬 Hex Data Analysis:\n")
                    self.response_text.insert("end", f"   Raw bytes: {' '.join(f'{b:02X}' for b in hex_data)}\n")
                    
                    # Try to decode as UDS response
                    self._decode_uds_response_bytes(hex_data, did_int)
        
        if not found_response:
            self.response_text.insert("end", "❌ No response found for the requested DID\n")
            self.response_text.insert("end", "Raw output:\n")
            self.response_text.insert("end", "-"*40 + "\n")
            for line in lines:
                if line.strip():
                    self.response_text.insert("end", f"{line}\n")

    def _decode_uds_response_bytes(self, data_bytes, did_int):
        """Decode UDS response bytes"""
        if not data_bytes:
            return
        
        self.response_text.insert("end", "\n📖 UDS Protocol Decoding:\n")
        
        # Check for positive response (0x62)
        if len(data_bytes) >= 3 and data_bytes[2] == 0x62:
            self.response_text.insert("end", "   ✅ Positive Response (0x62)\n")
            
            if len(data_bytes) >= 5:
                # Extract DID from response
                resp_did = (data_bytes[3] << 8) | data_bytes[4]
                self.response_text.insert("end", f"   📋 DID in response: 0x{resp_did:04X}\n")
                
                # Check if DID matches
                if resp_did == did_int:
                    self.response_text.insert("end", "   ✓ DID matches request\n")
                else:
                    self.response_text.insert("end", f"   ⚠️ DID mismatch: expected 0x{did_int:04X}, got 0x{resp_did:04X}\n")
                
                # Extract data payload
                if len(data_bytes) > 5:
                    payload = data_bytes[5:]
                    self.response_text.insert("end", f"   📦 Payload ({len(payload)} bytes): {' '.join(f'{b:02X}' for b in payload)}\n")
                    
                    # Try ASCII decoding
                    ascii_str = ""
                    hex_str = ""
                    for byte in payload:
                        if 32 <= byte <= 126:
                            ascii_str += chr(byte)
                            hex_str += f"{byte:02X} "
                        elif byte == 0x00:
                            ascii_str += "·"
                            hex_str += "00 "
                        else:
                            ascii_str += "."
                            hex_str += f"{byte:02X} "
                    
                    if ascii_str.strip("·."):
                        self.response_text.insert("end", f"   🔤 ASCII: {ascii_str}\n")
                    self.response_text.insert("end", f"   🔢 Hex: {hex_str.strip()}\n")
                    
                    # Special decoding for common DIDs
                    self._decode_specific_did(did_int, payload)
        
        # Check for negative response (0x7F)
        elif len(data_bytes) >= 3 and data_bytes[2] == 0x7F:
            self.response_text.insert("end", "   ❌ Negative Response (0x7F)\n")
            
            if len(data_bytes) >= 5:
                failed_service = data_bytes[3]
                nrc = data_bytes[4]
                
                nrc_codes = {
                    0x11: "Service not supported",
                    0x12: "Sub-function not supported",
                    0x13: "Incorrect message length or format",
                    0x22: "Conditions not correct",
                    0x31: "Request out of range",
                    0x33: "Security access denied",
                    0x35: "Invalid key",
                    0x78: "Response pending"
                }
                
                self.response_text.insert("end", f"   🚫 Failed Service: 0x{failed_service:02X}\n")
                self.response_text.insert("end", f"   📛 NRC: 0x{nrc:02X} - {nrc_codes.get(nrc, 'Unknown error')}\n")
        
        else:
            self.response_text.insert("end", "   ⚠️ Unknown response format\n")
            self.response_text.insert("end", f"   First bytes: {' '.join(f'{b:02X}' for b in data_bytes[:8])}\n")

    def _decode_specific_did(self, did_int, payload):
        """Decode specific known DIDs"""
        if did_int == 0xF190:  # VIN
            self.response_text.insert("end", "\n🚗 VIN DECODING:\n")
            vin = ""
            for byte in payload:
                if 32 <= byte <= 126:
                    vin += chr(byte)
                elif byte == 0x00:
                    break
                else:
                    vin += f"\\x{byte:02X}"
            self.response_text.insert("end", f"   VIN: {vin}\n")
            
        elif did_int == 0xF180:  # Boot Software ID
            self.response_text.insert("end", "\n👢 BOOT SOFTWARE ID:\n")
            self._decode_software_id(payload, "Boot")
            
        elif did_int == 0xF181:  # Application Software ID
            self.response_text.insert("end", "\n📱 APPLICATION SOFTWARE ID:\n")
            self._decode_software_id(payload, "App")
            
        elif did_int == 0xF18C:  # ECU Serial Number
            self.response_text.insert("end", "\n🔢 ECU SERIAL NUMBER:\n")
            serial = ""
            for byte in payload:
                if 32 <= byte <= 126:
                    serial += chr(byte)
                elif byte == 0x00:
                    serial += "·"
                else:
                    serial += f"\\x{byte:02X}"
            self.response_text.insert("end", f"   Serial: {serial}\n")

    def _decode_software_id(self, payload, software_type):
        """Decode software ID payload"""
        ascii_str = ""
        for byte in payload:
            if 32 <= byte <= 126:
                ascii_str += chr(byte)
            elif byte == 0x00:
                ascii_str += "·"
            else:
                ascii_str += "."
        
        self.response_text.insert("end", f"   {software_type} ID: {ascii_str}\n")
        
        # Try to extract version if present
        if "." in ascii_str:
            parts = ascii_str.split(".")
            if len(parts) >= 2:
                self.response_text.insert("end", f"   Version: {parts[0]}.{parts[1]}\n")

    def _display_raw_output(self, output):
        """Display raw command output"""
        self.response_text.insert("end", "\n📄 RAW OUTPUT:\n")
        self.response_text.insert("end", "="*40 + "\n")
        for line in output.split('\n'):
            if line.strip():
                self.response_text.insert("end", f"{line}\n")

    def read_did_range(self):
        """Use dump_dids for range scanning"""
        target_id = self.uds_target_id.get().strip()
        response_id = self.uds_response_id.get().strip()

        # Get timeout value
        timeout = "0.2"
        if hasattr(self, 'timeout_entry'):
            timeout_val = self.timeout_entry.get().strip()
            if timeout_val:
                timeout = timeout_val

        if not target_id:
            messagebox.showerror("Error", "Please enter a Target ECU ID")
            return

        # Ensure target_id has 0x prefix
        if not target_id.startswith("0x"):
            target_id = "0x" + target_id

        # Get range
        selection = self.did_select.get()

        if selection == "Scan Range: F180-F1FF":
            min_did = "0xF180"
            max_did = "0xF1FF"
        else:
            return

        # Clear response display
        self.response_text.delete("1.0", "end")
        self.status_label.configure(text="Scanning DID range...", text_color="#3498db")
        
        # Update response display
        self.response_text.insert("1.0", f"📤 UDS Range Scan Request\n")
        self.response_text.insert("end", "="*50 + "\n")
        self.response_text.insert("end", f"Target ID: {target_id}\n")
        self.response_text.insert("end", f"Response ID: {response_id}\n")
        self.response_text.insert("end", f"Range: {min_did} to {max_did}\n")
        self.response_text.insert("end", f"Timeout: {timeout}s\n\n")
        self.response_text.insert("end", "⏳ Scanning for accessible DIDs...\n")

        # Build the UDS dump_dids command
        cmd = ["uds", "dump_dids", target_id]

        if response_id:
            cmd.append(response_id)

        # Add options
        cmd.extend(["--min_did", min_did, "--max_did", max_did, "-t", timeout])

        # Add interface if selected
        if self.did_use_interface.get():
            cmd.extend(["-i", "vcan0"])

        # Show the command
        self.response_text.insert("end", f"\n🔧 Command: python -m fucyfuzz.fucyfuzz {' '.join(cmd)}\n")
        self.response_text.insert("end", "-"*50 + "\n\n")
        
        # Run in background thread
        threading.Thread(
            target=self._execute_range_scan,
            args=(cmd,),
            daemon=True
        ).start()

    def _execute_range_scan(self, cmd):
        """Execute range scan command"""
        working_dir = self.app.working_dir
        env = os.environ.copy()
        env["PYTHONPATH"] = working_dir + os.pathsep + env.get("PYTHONPATH", "")
        
        try:
            # Build the full command
            full_cmd = [sys.executable, "-m", "fucyfuzz.fucyfuzz"] + cmd
            
            # Update UI
            self.after(0, lambda: self.status_label.configure(
                text="Executing range scan...", 
                text_color="#3498db"))
            
            self.after(0, lambda: self.response_text.insert("end", "🚀 Starting range scan...\n"))
            
            # Run subprocess
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=working_dir,
                env=env,
                universal_newlines=True
            )
            
            output_lines = []
            
            # Read output in real-time
            for line in iter(process.stdout.readline, ''):
                output_lines.append(line)
                # Update UI with each line
                self.after(0, lambda l=line: self._update_response_display(l))
            
            process.wait()
            
            # Process the output
            full_output = "".join(output_lines)
            
            if process.returncode == 0:
                self.after(0, lambda: self.status_label.configure(
                    text="Range scan completed", 
                    text_color="#27ae60"))
                self.after(0, lambda: self.response_text.insert("end", f"\n✅ Range scan completed\n"))
                
                # Parse and display results
                self._parse_range_scan_results(full_output)
            else:
                self.after(0, lambda: self.status_label.configure(
                    text=f"Range scan failed (code: {process.returncode})", 
                    text_color="#e74c3c"))
                self.after(0, lambda: self.response_text.insert("end", 
                    f"\n⚠️ Range scan failed with exit code: {process.returncode}\n"))
                
        except Exception as e:
            error_msg = f"\n❌ Error running range scan: {str(e)}\n"
            self.after(0, lambda: self.status_label.configure(
                text=f"Error: {str(e)}", 
                text_color="#e74c3c"))
            self.after(0, lambda: self.response_text.insert("end", error_msg))

    def _parse_range_scan_results(self, output):
        """Parse and display range scan results"""
        lines = output.split('\n')
        accessible_dids = []
        
        self.response_text.insert("end", "\n" + "="*50 + "\n")
        self.response_text.insert("end", "📊 RANGE SCAN RESULTS\n")
        self.response_text.insert("end", "="*50 + "\n\n")
        
        for line in lines:
            line = line.strip()
            if "0x" in line and "Accessible" in line:
                # Extract DID from line like "0xF190 - VIN - Accessible"
                parts = line.split()
                for part in parts:
                    if part.startswith("0x"):
                        accessible_dids.append(part)
                        break
        
        if accessible_dids:
            self.response_text.insert("end", f"✅ Found {len(accessible_dids)} accessible DIDs:\n\n")
            for did in accessible_dids:
                self.response_text.insert("end", f"   • {did}\n")
        else:
            self.response_text.insert("end", "❌ No accessible DIDs found in the specified range\n")

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        super()._apply_scaling(scale_factor)
        
        # Scale tabview fonts
        if hasattr(self.tabs, '_segmented_button'):
            self.tabs._segmented_button.configure(font=FontConfig.get_tab_font(scale_factor))
        
        # Scale DID Reader dropdown width
        if self.did_select.winfo_exists():
            self.did_select.configure(
                width=int(450 * scale_factor),
                font=FontConfig.get_entry_font(scale_factor),
                dropdown_font=FontConfig.get_entry_font(scale_factor * 0.9)
            )
        
        # Scale button widths
        for btn_name in ['doip_btn', 'xcp_btn']:
            btn = getattr(self, btn_name, None)
            if btn and btn.winfo_exists():
                btn.configure(width=FontConfig.get_width("button_large", scale_factor))
        
        # Scale DID Reader button
        if self.did_read_btn.winfo_exists():
            self.did_read_btn.configure(
                width=int(250 * scale_factor),
                height=FontConfig.get_height("button", scale_factor)
            )
        
        # Scale entry widths in left panel
        entry_widths = {
            'start_did_entry': 130,
            'end_did_entry': 130,
            'uds_target_id': 150,
            'uds_response_id': 150,
            'timeout_entry': 130
        }
        
        for entry_name, base_width in entry_widths.items():
            entry = getattr(self, entry_name, None)
            if entry and entry.winfo_exists():
                entry.configure(width=int(base_width * scale_factor))
        
        # Scale header buttons
        if self.help_btn.winfo_exists():
            self.help_btn.configure(width=FontConfig.get_width("button_small", scale_factor))
        
        if self.report_btn.winfo_exists():
            self.report_btn.configure(width=FontConfig.get_width("button_small", scale_factor))

class SendFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="Send & Replay", font=FontConfig.get_title_font(1.0))
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        # Header Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("send"))
        self.help_btn.pack(side="right", padx=(0, 10))
        self.register_widget(self.help_btn, "button_small")

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("SendReplay"))
        self.report_btn.pack(side="right", padx=(10, 0))
        self.register_widget(self.report_btn, "button_small")

        # Main container - Compact
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ========== TOP SECTION: Send Type ==========
        self.top_section = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.top_section.pack(fill="x", pady=(0, 15))
        
        # Send Type
        type_frame = ctk.CTkFrame(self.top_section, fg_color="transparent")
        type_frame.pack(side="left", padx=(0, 15))
        
        type_label = ctk.CTkLabel(type_frame, text="Send Type:", font=FontConfig.get_label_font(0.9))
        type_label.pack(anchor="w")
        
        self.send_type = ctk.CTkOptionMenu(type_frame,
                                         values=["message", "file"],
                                         command=self.on_send_type_change,
                                         fg_color="#1f538d", button_color="#1f538d", 
                                         button_hover_color="#14375e", width=120)
        self.send_type.pack(pady=(2, 0))
        self.send_type.set("message")
        self.register_widget(self.send_type, "dropdown")
        
        # DBC Message (for message type)
        self.dbc_frame = ctk.CTkFrame(self.top_section, fg_color="transparent")
        self.dbc_frame.pack(side="left", padx=15)
        
        dbc_label = ctk.CTkLabel(self.dbc_frame, text="DBC Message:", font=FontConfig.get_label_font(0.9))
        dbc_label.pack(anchor="w")
        
        self.msg_select = ctk.CTkOptionMenu(self.dbc_frame, values=["No DBC Loaded"], 
                                           command=self.on_msg_select,
                                           fg_color="#1f538d", button_color="#1f538d", 
                                           button_hover_color="#14375e", width=180)
        self.msg_select.pack(pady=(2, 0))
        self.register_widget(self.msg_select, "dropdown")
        
        # File Browser (for file type, initially hidden)
        self.file_frame = ctk.CTkFrame(self.top_section, fg_color="transparent")
        
        file_label = ctk.CTkLabel(self.file_frame, text="CAN File:", font=FontConfig.get_label_font(0.9))
        file_label.pack(anchor="w")
        
        # File entry and browse button in one row
        file_row = ctk.CTkFrame(self.file_frame, fg_color="transparent")
        file_row.pack(fill="x", pady=(2, 0))
        
        self.file_path_entry = ctk.CTkEntry(file_row, placeholder_text="Select file...", width=150)
        self.file_path_entry.pack(side="left", padx=(0, 5))
        
        self.browse_file_btn = ctk.CTkButton(file_row, text="Browse",
                                           command=self.browse_file,
                                           width=70, height=24)
        self.browse_file_btn.pack(side="left")
        
        self.register_widget(self.file_path_entry, "entry")
        self.register_widget(self.browse_file_btn, "button_small")
        
        # ========== MIDDLE SECTION: Message/File Details ==========
        self.middle_section = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.middle_section.pack(fill="x", pady=(0, 15))
        
        # Manual Frame (for message type)
        self.manual_frame_widget = ctk.CTkFrame(self.middle_section, fg_color="transparent")
        
        manual_label = ctk.CTkLabel(self.manual_frame_widget, text="CAN Frame:", font=FontConfig.get_label_font(0.9))
        manual_label.pack(anchor="w")
        
        self.manual_frame = ctk.CTkEntry(self.manual_frame_widget, 
                                       placeholder_text="0x7a0#c0.ff.ee.00.11.22.33.44",
                                       width=250)
        self.manual_frame.pack(pady=(2, 0))
        self.register_widget(self.manual_frame, "entry")
        
        # File Delay (for file type, initially hidden)
        self.file_delay_frame = ctk.CTkFrame(self.middle_section, fg_color="transparent")
        
        file_delay_label = ctk.CTkLabel(self.file_delay_frame, text="File Delay (s):", font=FontConfig.get_label_font(0.9))
        file_delay_label.pack(anchor="w")
        
        self.file_delay_entry = ctk.CTkEntry(self.file_delay_frame, placeholder_text="0.2", width=100)
        self.file_delay_entry.pack(pady=(2, 0))
        self.register_widget(self.file_delay_entry, "entry")
        
        # ========== BOTTOM SECTION: Options & Execute ==========
        self.bottom_section = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.bottom_section.pack(fill="x")
        
        # Delay (left side)
        delay_frame = ctk.CTkFrame(self.bottom_section, fg_color="transparent")
        delay_frame.pack(side="left", padx=(0, 15))
        
        delay_label = ctk.CTkLabel(delay_frame, text="Delay (s):", font=FontConfig.get_label_font(0.9))
        delay_label.pack(anchor="w")
        
        self.delay_entry = ctk.CTkEntry(delay_frame, placeholder_text="0.5", width=100)
        self.delay_entry.pack(pady=(2, 0))
        self.register_widget(self.delay_entry, "entry")
        
        # Periodic Checkbox (center)
        periodic_frame = ctk.CTkFrame(self.bottom_section, fg_color="transparent")
        periodic_frame.pack(side="left", padx=15)
        
        self.periodic_var = ctk.BooleanVar()
        self.periodic_check = ctk.CTkCheckBox(periodic_frame, text="Periodic",
                                            variable=self.periodic_var,
                                            font=FontConfig.get_label_font(0.9))
        self.periodic_check.pack(anchor="w", pady=5)
        self.register_widget(self.periodic_check, "checkbox")
        
        # Interface Checkbox (center)
        interface_frame = ctk.CTkFrame(self.bottom_section, fg_color="transparent")
        interface_frame.pack(side="left", padx=15)
        
        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(interface_frame, text="Use -i vcan0",
                                             variable=self.use_interface,
                                             font=FontConfig.get_label_font(0.9))
        self.interface_check.pack(anchor="w", pady=5)
        self.register_widget(self.interface_check, "checkbox")
        
        # Execute Button (right side)
        execute_frame = ctk.CTkFrame(self.bottom_section, fg_color="transparent")
        execute_frame.pack(side="left", padx=(15, 0))
        
        self.send_btn = ctk.CTkButton(
            execute_frame,
            text="Send Message",
            width=120,
            height=30,
            command=self.run_send,
            fg_color="#27ae60"
        )
        self.send_btn.pack(anchor="w", pady=5)
        self.register_widget(self.send_btn, "button_large")

        # Initialize UI state
        self.on_send_type_change("message")

    def on_send_type_change(self, selection):
        """Update UI based on send type selection"""
        if selection == "message":
            # Show message-type elements
            self.dbc_frame.pack(side="left", padx=15)
            self.file_frame.pack_forget()
            self.manual_frame_widget.pack(side="left", padx=(0, 15))
            self.file_delay_frame.pack_forget()
            self.send_btn.configure(text="Send Message")
            self.periodic_check.pack(anchor="w", pady=5)  # Show periodic checkbox
        else:  # file type
            # Show file-type elements
            self.dbc_frame.pack_forget()
            self.file_frame.pack(side="left", padx=15)
            self.manual_frame_widget.pack_forget()
            self.file_delay_frame.pack(side="left", padx=(0, 15))
            self.send_btn.configure(text="Send File")
            self.periodic_check.pack_forget()  # Hide periodic checkbox

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
        super()._apply_scaling(scale_factor)
        
        # Scale buttons
        if self.send_btn.winfo_exists():
            self.send_btn.configure(
                width=int(120 * scale_factor),
                height=int(30 * scale_factor)
            )
        
        if self.browse_file_btn.winfo_exists():
            self.browse_file_btn.configure(
                width=int(70 * scale_factor),
                height=int(24 * scale_factor)
            )
        
        # Scale header buttons
        if self.help_btn.winfo_exists():
            self.help_btn.configure(width=FontConfig.get_width("button_small", scale_factor))
        
        if self.report_btn.winfo_exists():
            self.report_btn.configure(width=FontConfig.get_width("button_small", scale_factor))
        
        # Scale dropdowns
        for dropdown in [self.send_type, self.msg_select]:
            if dropdown.winfo_exists():
                width = 120 if dropdown == self.send_type else 180
                dropdown.configure(
                    width=int(width * scale_factor),
                    font=FontConfig.get_entry_font(scale_factor),
                    dropdown_font=FontConfig.get_entry_font(scale_factor * 0.9)
                )
        
        # Scale entry widths
        entry_widths = {
            'file_path_entry': 150,
            'manual_frame': 250,
            'delay_entry': 100,
            'file_delay_entry': 100
        }
        
        for entry_name, base_width in entry_widths.items():
            entry = getattr(self, entry_name, None)
            if entry and entry.winfo_exists():
                entry.configure(width=int(base_width * scale_factor))

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")
