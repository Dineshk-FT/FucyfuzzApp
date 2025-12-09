import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import os
import sys
import time
import random
import threading


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
#  FRAME CLASSES
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
        except Exception as e: 
            messagebox.showerror("Error", str(e))


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
        """Run listener with correct FucyFuzz interface handling"""
        cmd = []

        # Add interface BEFORE the module name
        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])

        # Module name and arguments
        cmd.extend(["listener", "-r"])

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

        # Main container
        self.button_container = ctk.CTkFrame(self, fg_color="transparent")
        self.button_container.pack(expand=True, fill="both", pady=20)

        # -----------------------
        # SPEED FUZZING
        # -----------------------
        self.speed_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.speed_frame.pack(pady=10)

        self.start_speeding_btn = ctk.CTkButton(self.speed_frame, text="Start Speed Fuzz",
                                                command=self.start_speeding)
        self.start_speeding_btn.pack(side="left", padx=5)

        self.stop_speeding_btn = ctk.CTkButton(self.speed_frame, text="Stop Speed Fuzz",
                                               command=self.stop_speeding)
        self.stop_speeding_btn.pack(side="left", padx=5)

        self.reset_speed_btn = ctk.CTkButton(self.speed_frame, text="Reset Speed",
                                             command=self.reset_speed)
        self.reset_speed_btn.pack(side="left", padx=5)

        # -----------------------
        # INDICATOR FUZZING
        # -----------------------
        self.indicator_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.indicator_frame.pack(pady=10)

        self.start_indicator_fuzz_btn = ctk.CTkButton(self.indicator_frame,
                                                      text="Start Indicator Fuzz",
                                                      command=self.start_indicator_fuzz)
        self.start_indicator_fuzz_btn.pack(side="left", padx=5)

        self.stop_indicator_fuzz_btn = ctk.CTkButton(self.indicator_frame,
                                                     text="Stop Indicator Fuzz",
                                                     command=self.stop_indicator_fuzz)
        self.stop_indicator_fuzz_btn.pack(side="left", padx=5)

        # -----------------------
        # DOOR FUZZING
        # -----------------------
        self.doors_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.doors_frame.pack(pady=10)

        self.start_door_fuzz_btn = ctk.CTkButton(self.doors_frame,
                                                 text="Start Door Fuzz",
                                                 command=self.start_door_fuzz)
        self.start_door_fuzz_btn.pack(side="left", padx=5)

        self.stop_door_fuzz_btn = ctk.CTkButton(self.doors_frame,
                                                text="Stop Door Fuzz",
                                                command=self.stop_door_fuzz)
        self.stop_door_fuzz_btn.pack(side="left", padx=5)

        # -----------------------
        # State Variables
        # -----------------------
        self.fuzzing_speed_active = False
        self.fuzzing_indicator_active = False
        self.fuzzing_door_active = False

        self.speed_process = None
        self.indicator_process = None
        self.door_process = None

    # ------------------------------------------------------------
    # Helper for executing background fuzzing commands
    # ------------------------------------------------------------
    def run_demo_command(self, cmd_args, description):
        try:
            working_dir = self.app.working_dir
            env = os.environ.copy()
            env["PYTHONPATH"] = working_dir + os.pathsep + env.get("PYTHONPATH", "")

            cmd = [sys.executable, "-m", "fucyfuzz.fucyfuzz"] + cmd_args

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=working_dir,
                env=env
            )

            self.app._console_write(f"[DEMO] Sent: {description}\n")
            return process

        except Exception as e:
            self.app._console_write(f"[DEMO ERROR] {description}: {e}\n")
            return None

    # ------------------------------------------------------------
    # SPEED FUZZING
    # ------------------------------------------------------------
    def start_speeding(self):
        if not self.fuzzing_speed_active:
            self.fuzzing_speed_active = True
            self.start_speeding_btn.configure(fg_color="#c0392b", text="Fuzzing...")

            cmd = ["fuzzer", "mutate", "244", "..", "-d", "0.5"]
            self.speed_process = self.run_demo_command(cmd, "Speed Fuzzing Started")

    def stop_speeding(self):
        if self.fuzzing_speed_active and self.speed_process:
            self.speed_process.terminate()
            self.speed_process = None

        self.fuzzing_speed_active = False
        self.start_speeding_btn.configure(fg_color="#1f538d", text="Start Speed Fuzz")
        self.app._console_write("[DEMO] Speed fuzz stopped\n")

    def reset_speed(self):
        self.stop_speeding()
        cmd = ["send", "message", "0x244#00"]
        self.run_demo_command(cmd, "Reset Speed to 0")
    # ------------------------------------------------------------
    # INDICATOR FUZZING (ID: 0x188)
    # ------------------------------------------------------------
    def start_indicator_fuzz(self):
        if not self.fuzzing_indicator_active:
            self.fuzzing_indicator_active = True
            self.start_indicator_fuzz_btn.configure(fg_color="#c0392b", text="Fuzzing...")

            # 1-byte indicator payload -> fuzz full byte with delay
            cmd = ["fuzzer", "mutate", "188", ".", "-d", "0.5"]
            self.indicator_process = self.run_demo_command(cmd, "Indicator Fuzzing Started")


    def stop_indicator_fuzz(self):
        if self.fuzzing_indicator_active and self.indicator_process:
            self.indicator_process.terminate()
            self.indicator_process = None

        self.fuzzing_indicator_active = False
        self.start_indicator_fuzz_btn.configure(fg_color="#1f538d", text="Start Indicator Fuzz")
        self.app._console_write("[DEMO] Indicator fuzz stopped\n")

        # IMPORTANT: Reset indicator state
        reset_cmd = ["send", "message", "0x188#00"]
        self.run_demo_command(reset_cmd, "Indicators OFF")


    # ------------------------------------------------------------
    # DOOR FUZZING (ID: 0x19B) - Full 4-byte mutation
    # ------------------------------------------------------------
    def start_door_fuzz(self):
        if not self.fuzzing_door_active:
            self.fuzzing_door_active = True
            self.start_door_fuzz_btn.configure(fg_color="#c0392b", text="Fuzzing...")

            # WARNING: 4 bytes required for doors, so mutate 4 dots (....)
            cmd = ["fuzzer", "mutate", "19B", "........", "-d", "0.5"]
            self.door_process = self.run_demo_command(cmd, "Door Fuzzing Started")


    def stop_door_fuzz(self):
        if self.fuzzing_door_active and self.door_process:
            self.door_process.terminate()
            self.door_process = None

        self.fuzzing_door_active = False
        self.start_door_fuzz_btn.configure(fg_color="#1f538d", text="Start Door Fuzz")
        self.app._console_write("[DEMO] Door fuzz stopped\n")

        # Reset door state to all closed
        reset_cmd = ["send", "message", "0x19B#00.00.00.00"]
        self.run_demo_command(reset_cmd, "Reset Doors")

    # ------------------------------------------------------------
    # Apply Scaling
    # ------------------------------------------------------------
    def _apply_scaling(self, scale_factor):
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        button_font_size = max(14, min(22, int(16 * scale_factor)))

        self.title_label.configure(font=("Arial", title_font_size, "bold"))

        btn_height = max(40, min(70, int(50 * scale_factor)))
        btn_width = max(120, min(200, int(150 * scale_factor)))

        buttons = [
            self.start_speeding_btn, self.stop_speeding_btn, self.reset_speed_btn,
            self.start_indicator_fuzz_btn, self.stop_indicator_fuzz_btn,
            self.start_door_fuzz_btn, self.stop_door_fuzz_btn
        ]

        for button in buttons:
            button.configure(height=btn_height, width=btn_width,
                             font=("Arial", button_font_size), corner_radius=8)

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

        # NEW: View Failures button
        self.view_failures_btn = ctk.CTkButton(self.head_frame, text="📊 View Failures", 
                      fg_color="#e74c3c", command=lambda: app.show_failure_cases())
        self.view_failures_btn.pack(side="right", padx=10)

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
        self.view_failures_btn.configure(height=small_btn_size, font=("Arial", button_font_size-1),
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

        # NEW: View Failures button
        self.view_failures_btn = ctk.CTkButton(self.head_frame, text="📊 View Failures", 
                      fg_color="#e74c3c", command=lambda: app.show_failure_cases())
        self.view_failures_btn.pack(side="right", padx=10)

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
        self.view_failures_btn.configure(height=small_btn_size, font=("Arial", button_font_size-1),
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

        # NEW: View Failures button
        self.view_failures_btn = ctk.CTkButton(self.head_frame, text="📊 View Failures", 
                      fg_color="#e74c3c", command=lambda: app.show_failure_cases())
        self.view_failures_btn.pack(side="right", padx=5)

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
        self.view_failures_btn.configure(height=small_btn_size, font=("Arial", button_font_size-2), width=btn_width)

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

        # NEW: View Failures button
        self.view_failures_btn = ctk.CTkButton(self.head_frame, text="📊 View Failures", 
                      fg_color="#e74c3c", command=lambda: app.show_failure_cases())
        self.view_failures_btn.pack(side="right", padx=5)

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
        self.view_failures_btn.configure(height=small_btn_size, font=("Arial", button_font_size-2), width=btn_width)

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

        if self.args.get(): 
            cmd.extend(self.args.get().split())
        self.app.run_command(cmd, "UDS")


class AdvancedFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="Advanced", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")

        # Buttons (Show help for all advanced modules)
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help(["doip", "xcp", "uds"]))
        self.help_btn.pack(side="right", padx=5)

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("Advanced"))
        self.report_btn.pack(side="right", padx=5)

        # NEW: View Failures button
        self.view_failures_btn = ctk.CTkButton(self.head_frame, text="📊 View Failures", 
                      fg_color="#e74c3c", command=lambda: app.show_failure_cases())
        self.view_failures_btn.pack(side="right", padx=5)

        # Create notebook for different advanced functions
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, pady=10)

        # Tab 1: DoIP
        self.doip_tab = self.tabs.add("DoIP")

        # DoIP Section with interface checkbox
        self.doip_frame = ctk.CTkFrame(self.doip_tab, fg_color="transparent")
        self.doip_frame.pack(fill="x", pady=10, padx=20)

        self.doip_use_interface = ctk.BooleanVar(value=True)
        self.doip_interface_check = ctk.CTkCheckBox(self.doip_frame, text="Use -i vcan0 interface for DoIP",
                                                  variable=self.doip_use_interface)
        self.doip_interface_check.pack(pady=5)

        self.doip_btn = ctk.CTkButton(self.doip_frame, text="DoIP Discovery",
                                    command=self.run_doip)
        self.doip_btn.pack(fill="x", pady=5)

        # Tab 2: XCP
        self.xcp_tab = self.tabs.add("XCP")

        # XCP Section with interface checkbox
        self.xcp_frame = ctk.CTkFrame(self.xcp_tab, fg_color="transparent")
        self.xcp_frame.pack(fill="x", pady=10, padx=20)

        self.xcp_use_interface = ctk.BooleanVar(value=True)
        self.xcp_interface_check = ctk.CTkCheckBox(self.xcp_frame, text="Use -i vcan0 interface for XCP",
                                                 variable=self.xcp_use_interface)
        self.xcp_interface_check.pack(pady=5)

        self.xcp_id = ctk.CTkEntry(self.xcp_frame, placeholder_text="XCP ID (e.g., 0x123)")
        self.xcp_id.pack(pady=5, fill="x")

        self.xcp_btn = ctk.CTkButton(self.xcp_frame, text="XCP Info",
                                   command=self.run_xcp)
        self.xcp_btn.pack(pady=5, fill="x")

        # Tab 3: UDS DID Reader
        self.did_tab = self.tabs.add("DID Reader")

        # UDS DID Reader Section
        self.did_frame = ctk.CTkFrame(self.did_tab, fg_color="transparent")
        self.did_frame.pack(fill="both", expand=True, pady=10, padx=20)

        # DID Selection
        ctk.CTkLabel(self.did_frame, text="Select DID to Read:").pack(anchor="w", pady=(0, 5))

        self.did_select = ctk.CTkOptionMenu(self.did_frame,
                                          values=[
                                              "Single DID: 0xF190 - VIN (Vehicle ID)",
                                              "Single DID: 0xF180 - Boot Software ID",
                                              "Single DID: 0xF181 - Application Software ID",
                                              "Single DID: 0xF186 - Active Session",
                                              "Single DID: 0xF187 - Spare Part Number",
                                              "Single DID: 0xF188 - ECU SW Number",
                                              "Single DID: 0xF198 - Repair Shop Code",
                                              "Single DID: 0xF18C - ECU Serial Number",
                                              "Custom DID",
                                              "Scan Range: 0xF180-0xF1FF (Manufacturer DIDs)"
                                          ],
                                          command=self.on_did_selection_change,
                                          fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.did_select.pack(pady=5, fill="x")
        self.did_select.set("Single DID: 0xF190 - VIN (Vehicle ID)")

        # Custom DID entry (initially hidden)
        self.custom_did_frame = ctk.CTkFrame(self.did_frame, fg_color="transparent")

        ctk.CTkLabel(self.custom_did_frame, text="Custom DID (Hex):").pack(anchor="w", pady=(0, 5))
        self.custom_did_entry = ctk.CTkEntry(self.custom_did_frame, placeholder_text="e.g., F190 (without 0x)")
        self.custom_did_entry.pack(pady=5, fill="x")

        # Range scanning options (initially hidden)
        self.range_frame = ctk.CTkFrame(self.did_frame, fg_color="transparent")

        ctk.CTkLabel(self.range_frame, text="Start DID (Hex):").pack(anchor="w", pady=(0, 5))
        self.start_did_entry = ctk.CTkEntry(self.range_frame, placeholder_text="F180")
        self.start_did_entry.pack(pady=5, fill="x")

        ctk.CTkLabel(self.range_frame, text="End DID (Hex):").pack(anchor="w", pady=(10, 5))
        self.end_did_entry = ctk.CTkEntry(self.range_frame, placeholder_text="F1FF")
        self.end_did_entry.pack(pady=5, fill="x")

        # Target ID for UDS request
        ctk.CTkLabel(self.did_frame, text="Target ECU ID (Hex):").pack(anchor="w", pady=(10, 5))
        self.uds_target_id = ctk.CTkEntry(self.did_frame, placeholder_text="0x7E0 (default)")
        self.uds_target_id.insert(0, "0x7E0")
        self.uds_target_id.pack(pady=5, fill="x")

        # Response ID
        ctk.CTkLabel(self.did_frame, text="Response ID:").pack(anchor="w", pady=(10, 5))
        self.uds_response_id = ctk.CTkEntry(self.did_frame, placeholder_text="0x7E8 (default)")
        self.uds_response_id.insert(0, "0x7E8")
        self.uds_response_id.pack(pady=5, fill="x")

        # Timeout option
        ctk.CTkLabel(self.did_frame, text="Timeout (seconds):").pack(anchor="w", pady=(10, 5))
        self.timeout_entry = ctk.CTkEntry(self.did_frame, placeholder_text="0.2 (default)")
        self.timeout_entry.insert(0, "0.2")
        self.timeout_entry.pack(pady=5, fill="x")

        # Interface checkbox for DID reading
        self.did_use_interface = ctk.BooleanVar(value=True)
        self.did_interface_check = ctk.CTkCheckBox(self.did_frame, text="Use -i vcan0 interface for UDS",
                                                 variable=self.did_use_interface)
        self.did_interface_check.pack(pady=10)

        # NEW: Response display section
        self.response_section = ctk.CTkFrame(self.did_frame, fg_color="transparent")
        self.response_section.pack(fill="x", pady=(10, 0))

        # Two buttons side by side
        self.button_frame = ctk.CTkFrame(self.response_section, fg_color="transparent")
        self.button_frame.pack(fill="x")

        # Read DID button
        self.did_read_btn = ctk.CTkButton(self.button_frame, text="🔍 Read DID",
                                        command=self.read_did, fg_color="#8e44ad")
        self.did_read_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # NEW: Show Response button
        self.show_response_btn = ctk.CTkButton(self.button_frame, text="📥 Show Response",
                                             command=self.show_did_response, fg_color="#27ae60")
        self.show_response_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # NEW: Response display textbox
        self.response_text = ctk.CTkTextbox(self.did_frame, height=200, font=("Consolas", 11))
        self.response_text.pack(fill="both", expand=True, pady=(10, 0))

        # Initialize UI state
        self.on_did_selection_change("Single DID: 0xF190 - VIN (Vehicle ID)")

        # Tab 4: UDS Response Analyzer
        self.analyzer_tab = self.tabs.add("UDS Analyzer")

        # UDS Analyzer Frame
        self.analyzer_frame = ctk.CTkFrame(self.analyzer_tab, fg_color="transparent")
        self.analyzer_frame.pack(fill="both", expand=True, pady=10, padx=20)

        # Section 1: Input raw UDS response
        input_frame = ctk.CTkFrame(self.analyzer_frame, fg_color="transparent")
        input_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(input_frame, text="Paste UDS Response (from candump):").pack(anchor="w")

        # Example formats
        examples_label = ctk.CTkLabel(input_frame,
                                    text="Example format:\nvcan0  7E8   [8]  10 14 62 F1 90 46 55 43",
                                    text_color="#95a5a6",
                                    font=("Arial", 11))
        examples_label.pack(anchor="w", pady=(0, 5))

        self.uds_response_entry = ctk.CTkTextbox(input_frame, height=120)
        self.uds_response_entry.pack(fill="x", pady=5)

        # Example buttons
        example_btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        example_btn_frame.pack(fill="x", pady=5)

        self.load_vin_example_btn = ctk.CTkButton(example_btn_frame, text="VIN Example",
                                                command=lambda: self.load_uds_example("vin"),
                                                fg_color="#3498db", width=120)
        self.load_vin_example_btn.pack(side="left", padx=(0, 5))

        self.load_boot_example_btn = ctk.CTkButton(example_btn_frame, text="Boot ID Example",
                                                command=lambda: self.load_uds_example("boot"),
                                                fg_color="#3498db", width=120)
        self.load_boot_example_btn.pack(side="left", padx=5)

        self.clear_btn = ctk.CTkButton(example_btn_frame, text="Clear",
                                     command=self.clear_uds_input,
                                     fg_color="#7f8c8d", width=80)
        self.clear_btn.pack(side="right")

        # Analyze button
        self.analyze_btn = ctk.CTkButton(self.analyzer_frame, text="🔍 Analyze Response",
                                       command=self.analyze_uds_response,
                                       fg_color="#27ae60", height=40)
        self.analyze_btn.pack(pady=10)

        # Section 2: Results display
        results_frame = ctk.CTkFrame(self.analyzer_frame, fg_color="transparent")
        results_frame.pack(fill="both", expand=True, pady=(10, 0))

        ctk.CTkLabel(results_frame, text="Analysis Results:").pack(anchor="w")

        self.results_text = ctk.CTkTextbox(results_frame, font=("Consolas", 12))
        self.results_text.pack(fill="both", expand=True, pady=5)

    def on_did_selection_change(self, selection):
        """Show/hide custom DID entry based on selection"""
        # Hide all optional frames first
        self.custom_did_frame.pack_forget()
        self.range_frame.pack_forget()

        if selection == "Custom DID":
            self.custom_did_frame.pack(fill="x", pady=10)
        elif "Scan Range:" in selection:
            # Pre-fill the range for manufacturer DIDs
            self.start_did_entry.delete(0, "end")
            self.end_did_entry.delete(0, "end")
            self.start_did_entry.insert(0, "F180")
            self.end_did_entry.insert(0, "F1FF")
            self.range_frame.pack(fill="x", pady=10)

    def read_did(self):
        """Execute UDS DID read command using raw CAN send"""
        # Get target ID
        target_id = self.uds_target_id.get().strip()

        if not target_id:
            messagebox.showerror("Error", "Please enter a Target ECU ID")
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
                return
            # Remove 0x prefix if present
            did_hex = did_hex.replace("0x", "")
            # Ensure it's 4 hex digits
            if len(did_hex) != 4:
                messagebox.showerror("Error", "DID must be 4 hex digits (e.g., F190)")
                return
            did_bytes = did_hex.upper()

        elif "Single DID:" in selection:
            # Extract DID from the option text
            # e.g., "Single DID: 0xF190 - VIN (Vehicle ID)" -> "F190"
            did_full = selection.split(": ")[1].split(" - ")[0]  # "0xF190"
            did_bytes = did_full[2:].upper()  # "F190"

        elif "Scan Range:" in selection:
            # For range scanning, use the dump_dids command
            self.read_did_range()
            return
        else:
            messagebox.showerror("Error", "Invalid selection")
            return

        # Build the CAN frame in the correct format
        # Format: 0x7E0#03.22.f1.90.00.00.00.00
        # Where:
        #   03 = length (3 bytes total for UDS request: 0x22 + 2-byte DID)
        #   22 = UDS Read Data By Identifier service
        #   f1.90 = DID (2 bytes, lowercase)
        #   00.00.00.00 = padding

        # Parse the DID into two bytes
        did_high_byte = did_bytes[0:2].lower()  # First 2 chars (e.g., "f1")
        did_low_byte = did_bytes[2:4].lower()   # Last 2 chars (e.g., "90")

        # Create the CAN frame with lowercase hex
        can_frame = f"{target_id}#03.22.{did_high_byte}.{did_low_byte}.00.00.00.00"

        # Build the send command
        cmd = ["send", "message", can_frame]

        # Add interface if selected
        if self.did_use_interface.get():
            cmd.extend(["-i", "vcan0"])

        # Run the command
        self.app.run_command(cmd, "UDS_DID_Reader")

        # Show the command that was sent
        response_id = self.uds_response_id.get().strip() or "0x7E8"
        self.app._console_write(f"\n📤 Sent UDS Request:\n")
        self.app._console_write(f"   Service: 0x22 (Read Data By Identifier)\n")
        self.app._console_write(f"   DID: 0x{did_bytes}\n")
        self.app._console_write(f"   Raw Frame: {can_frame}\n")
        self.app._console_write(f"   Expected Response on: {response_id}\n")
        self.app._console_write(f"\n💡 Manual commands:\n")
        self.app._console_write(f"   cansend vcan0 {target_id}#0322{did_bytes}00000000\n")
        self.app._console_write(f"   python -m fucyfuzz.fucyfuzz send message {can_frame}\n")

        # Store the DID for later use in show_response
        self.last_did_hex = did_bytes
        self.last_target_id = target_id
        self.last_response_id = response_id

    def read_did_range(self):
        """Use dump_dids for range scanning"""
        target_id = self.uds_target_id.get().strip()
        response_id = self.uds_response_id.get().strip()

        # Get timeout value (use default if not set)
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

        if selection == "Scan Range: 0xF180-0xF1FF (Manufacturer DIDs)":
            min_did = "0xF180"
            max_did = "0xF1FF"
        else:
            # This shouldn't happen, but just in case
            return

        # Build the UDS dump_dids command
        cmd = ["uds", "dump_dids", target_id]

        if response_id:
            cmd.append(response_id)

        # Add options
        cmd.extend(["--min_did", min_did, "--max_did", max_did, "-t", timeout])

        # Add interface if selected
        if self.did_use_interface.get():
            cmd.extend(["-i", "vcan0"])

        # Run the command
        self.app.run_command(cmd, "UDS_DID_Scanner")

        # Also show manual examples for the first few DIDs in the range
        self.app._console_write(f"\n📋 Manual examples for this range:\n")

        # Show examples for first 3 DIDs in the range
        try:
            start_val = int(min_did, 16)
            for i in range(3):
                did_hex = f"{start_val + i:04X}"
                self.app._console_write(f"   cansend vcan0 {target_id}#0322{did_hex}00000000\n")
        except:
            pass

    def show_did_response(self):
        """Show response for the last read DID using dump_dids command"""
        # Check if we have stored DID information from last read
        if not hasattr(self, 'last_did_hex'):
            messagebox.showwarning("Warning", "Please read a DID first before showing response")
            return

        # Get target and response IDs
        target_id = self.uds_target_id.get().strip() or self.last_target_id
        response_id = self.uds_response_id.get().strip() or self.last_response_id

        if not target_id:
            messagebox.showerror("Error", "Please enter a Target ECU ID")
            return

        # Ensure target_id has 0x prefix
        if not target_id.startswith("0x"):
            target_id = "0x" + target_id

        # Ensure response_id has 0x prefix
        if response_id and not response_id.startswith("0x"):
            response_id = "0x" + response_id

        # Clear previous response
        self.response_text.delete("1.0", "end")
        self.response_text.insert("1.0", "Fetching response for DID 0x{}...\n".format(self.last_did_hex))

        # Get timeout value
        timeout = "0.2"
        if hasattr(self, 'timeout_entry'):
            timeout_val = self.timeout_entry.get().strip()
            if timeout_val:
                timeout = timeout_val

        # Convert DID to hex integer
        try:
            did_int = int(self.last_did_hex, 16)
        except ValueError:
            self.response_text.insert("end", f"❌ Invalid DID format: 0x{self.last_did_hex}\n")
            return

        # Build the dump_dids command for specific DID
        cmd = ["uds", "dump_dids", target_id]

        if response_id:
            cmd.append(response_id)

        # Add options for specific DID
        cmd.extend([
            "--min_did", f"0x{did_int:04X}",
            "--max_did", f"0x{did_int:04X}",
            "-t", timeout
        ])

        # Add interface if selected
        if self.did_use_interface.get():
            cmd.extend(["-i", "vcan0"])

        # Show the command being executed
        cmd_str = " ".join(cmd)
        self.response_text.insert("end", f"\n📋 Executing: python -m fucyfuzz.fucyfuzz {cmd_str}\n\n")

        # Run the command in a separate thread to avoid freezing UI
        threading.Thread(target=self._execute_dump_dids, args=(cmd,), daemon=True).start()

    def _execute_dump_dids(self, cmd):
        """Execute dump_dids command and show results in response_text"""
        working_dir = self.app.working_dir
        env = os.environ.copy()
        env["PYTHONPATH"] = working_dir + os.pathsep + env.get("PYTHONPATH", "")

        try:
            # Build the full command
            full_cmd = [sys.executable, "-m", "fucyfuzz.fucyfuzz"] + cmd

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

            # Read output in real-time
            output_lines = []
            for line in iter(process.stdout.readline, ''):
                output_lines.append(line)
                # Update UI with each line
                self.after(0, self._update_response_text, line)

            process.wait()

            # Update final status
            if process.returncode == 0:
                self.after(0, self._update_response_text, f"\n✅ Command completed successfully (Exit code: {process.returncode})\n")

                # NEW: Decode the response after completion
                full_output = "".join(output_lines)
                self.after(0, self._decode_uds_response, full_output)

            else:
                self.after(0, self._update_response_text, f"\n⚠️ Command completed with errors (Exit code: {process.returncode})\n")

        except Exception as e:
            error_msg = f"\n❌ Error running command: {str(e)}\n"
            self.after(0, self._update_response_text, error_msg)

    def _decode_uds_response(self, full_output):
        """Decode UDS response from dump_dids output"""
        # Add separator
        self.after(0, self._update_response_text, "\n" + "="*70 + "\n")
        self.after(0, self._update_response_text, "📊 UDS RESPONSE DECODER\n")
        self.after(0, self._update_response_text, "="*70 + "\n\n")

        # Look for DID data in the output
        lines = full_output.split('\n')
        decoded_data = []
        current_did = None
        current_data = []

        for line in lines:
            line = line.strip()

            # Look for DID lines
            if "0x" in line and ("f1" in line.lower() or "f2" in line.lower()):
                # Try to parse DID and data
                parts = line.split()
                for part in parts:
                    if part.lower().startswith("0xf"):
                        # Found a DID
                        try:
                            did_hex = part.lower().replace("0x", "")
                            if len(did_hex) == 4:  # Valid DID
                                current_did = did_hex.upper()
                                self.after(0, self._update_response_text, f"🔍 Found DID: 0x{current_did}\n")

                                # Look for data bytes in the same line
                                data_start = line.lower().find(did_hex.lower()) + 4
                                rest_of_line = line[data_start:].strip()

                                # Extract hex bytes (2 chars each)
                                data_bytes = []
                                for i in range(0, len(rest_of_line), 2):
                                    if i+2 <= len(rest_of_line):
                                        byte_str = rest_of_line[i:i+2]
                                        if byte_str.isalnum() and len(byte_str) == 2:
                                            try:
                                                data_bytes.append(int(byte_str, 16))
                                            except:
                                                pass

                                if data_bytes:
                                    current_data = data_bytes
                                    self._decode_did_data(current_did, current_data)
                                break
                        except:
                            continue

        # If no DID found in the output, check for raw hex data
        if not decoded_data:
            # Look for any hex data in the output
            all_hex_data = []
            for line in lines:
                # Extract hex bytes (2 chars each)
                hex_parts = []
                line = line.strip()

                # Split by spaces and look for hex strings
                for word in line.split():
                    if len(word) == 2 and all(c in "0123456789abcdefABCDEF" for c in word):
                        try:
                            hex_parts.append(int(word, 16))
                        except:
                            pass

                if hex_parts:
                    all_hex_data.extend(hex_parts)

            if all_hex_data:
                self.after(0, self._update_response_text, "📋 Raw hex data found:\n")
                self.after(0, self._update_response_text, f"   Hex: {' '.join(f'{b:02X}' for b in all_hex_data)}\n")

                # Try to decode as UDS response
                self._decode_uds_bytes(all_hex_data)

        # Show quick reference
        self.after(0, self._update_response_text, "\n" + "="*70 + "\n")
        self.after(0, self._update_response_text, "📚 UDS RESPONSE FORMAT REFERENCE:\n\n")

        # Positive Response (0x62) format
        self.after(0, self._update_response_text, "✅ Positive Response (0x62) format:\n")
        self.after(0, self._update_response_text, "   Byte 0: 0x10 (First Frame)\n")
        self.after(0, self._update_response_text, "   Byte 1: Total data length (n)\n")
        self.after(0, self._update_response_text, "   Byte 2: 0x62 (Positive response to service 0x22)\n")
        self.after(0, self._update_response_text, "   Byte 3-4: DID (2 bytes, e.g., F1 90)\n")
        self.after(0, self._update_response_text, "   Byte 5+: Data payload\n\n")

        # Negative Response (0x7F) format
        self.after(0, self._update_response_text, "❌ Negative Response (0x7F) format:\n")
        self.after(0, self._update_response_text, "   Byte 0: 0x10 (First Frame)\n")
        self.after(0, self._update_response_text, "   Byte 1: 0x03 (Length)\n")
        self.after(0, self._update_response_text, "   Byte 2: 0x7F (Negative response)\n")
        self.after(0, self._update_response_text, "   Byte 3: Requested service (e.g., 0x22)\n")
        self.after(0, self._update_response_text, "   Byte 4: NRC (Negative Response Code)\n\n")

        # Common NRC codes
        self.after(0, self._update_response_text, "🔧 Common NRC Codes:\n")
        nrc_codes = {
            0x11: "0x11 - Service not supported",
            0x12: "0x12 - Sub-function not supported",
            0x13: "0x13 - Incorrect message length or format",
            0x22: "0x22 - Conditions not correct",
            0x31: "0x31 - Request out of range",
            0x33: "0x33 - Security access denied",
            0x35: "0x35 - Invalid key",
            0x78: "0x78 - Response pending"
        }

        for code, desc in nrc_codes.items():
            self.after(0, self._update_response_text, f"   {desc}\n")

        self.after(0, self._update_response_text, "="*70 + "\n")

    def _decode_did_data(self, did_hex, data_bytes):
        """Decode specific DID data"""
        did_map = {
            "F190": "VIN (Vehicle Identification Number)",
            "F180": "Boot Software ID",
            "F181": "Application Software ID",
            "F186": "Active Session",
            "F187": "Spare Part Number",
            "F188": "ECU SW Number",
            "F198": "Repair Shop Code",
            "F18C": "ECU Serial Number"
        }

        did_name = did_map.get(did_hex.upper(), "Unknown DID")
        self.after(0, self._update_response_text, f"📝 DID 0x{did_hex}: {did_name}\n")

        # Decode based on DID type
        if did_hex.upper() == "F190":  # VIN
            # VIN is ASCII encoded
            ascii_data = ""
            for byte in data_bytes:
                if 32 <= byte <= 126:  # Printable ASCII
                    ascii_data += chr(byte)
                elif byte == 0x00:
                    ascii_data += "·"
                else:
                    ascii_data += f"\\x{byte:02X}"

            self.after(0, self._update_response_text, f"   Decoded VIN: {ascii_data}\n")
            self.after(0, self._update_response_text, f"   Raw hex: {' '.join(f'{b:02X}' for b in data_bytes)}\n")

        elif did_hex.upper() in ["F180", "F181", "F187", "F188", "F18C"]:
            # Software IDs are usually ASCII
            ascii_data = ""
            hex_data = []
            for byte in data_bytes:
                if 32 <= byte <= 126:  # Printable ASCII
                    ascii_data += chr(byte)
                    hex_data.append(f"{byte:02X}")
                elif byte == 0x00:
                    ascii_data += "·"
                    hex_data.append("00")
                else:
                    ascii_data += f"\\x{byte:02X}"
                    hex_data.append(f"{byte:02X}")

            if ascii_data:
                self.after(0, self._update_response_text, f"   ASCII: {ascii_data}\n")
            self.after(0, self._update_response_text, f"   Hex: {' '.join(hex_data)}\n")

        else:
            # Generic hex display
            self.after(0, self._update_response_text, f"   Hex data: {' '.join(f'{b:02X}' for b in data_bytes)}\n")

            # Try ASCII conversion anyway
            ascii_data = ""
            for byte in data_bytes:
                if 32 <= byte <= 126:
                    ascii_data += chr(byte)
                elif byte == 0x00:
                    ascii_data += "·"
                else:
                    ascii_data += "."

            if ascii_data.replace(".", "").replace("·", ""):
                self.after(0, self._update_response_text, f"   ASCII attempt: {ascii_data}\n")

    def _decode_uds_bytes(self, data_bytes):
        """Decode UDS protocol bytes"""
        if not data_bytes:
            return

        self.after(0, self._update_response_text, "\n🔬 UDS Protocol Analysis:\n")

        # Check first byte for frame type
        first_byte = data_bytes[0]

        if first_byte == 0x10:  # First frame
            self.after(0, self._update_response_text, "   Frame Type: First Frame (Multi-frame response)\n")

            if len(data_bytes) >= 2:
                total_len = data_bytes[1]
                self.after(0, self._update_response_text, f"   Total Data Length: {total_len} bytes\n")

            if len(data_bytes) >= 3:
                service = data_bytes[2]
                service_name = {
                    0x62: "Positive Response to Read Data By Identifier (0x22)",
                    0x7F: "Negative Response",
                    0x67: "Positive Response to Security Access (0x27)",
                    0x6E: "Positive Response to Tester Present (0x3E)"
                }.get(service, f"Unknown service 0x{service:02X}")
                self.after(0, self._update_response_text, f"   Service: 0x{service:02X} ({service_name})\n")

                if service == 0x62 and len(data_bytes) >= 5:
                    # Positive response to DID read
                    did = (data_bytes[3] << 8) | data_bytes[4]
                    self.after(0, self._update_response_text, f"   DID: 0x{did:04X}\n")

                    # Extract data payload
                    if len(data_bytes) > 5:
                        payload = data_bytes[5:]
                        self.after(0, self._update_response_text, f"   Payload ({len(payload)} bytes): {' '.join(f'{b:02X}' for b in payload)}\n")

                        # Try to decode payload
                        ascii_payload = ""
                        for byte in payload:
                            if 32 <= byte <= 126:
                                ascii_payload += chr(byte)
                            elif byte == 0x00:
                                ascii_payload += "·"
                            else:
                                ascii_payload += "."

                        if ascii_payload.replace(".", "").replace("·", ""):
                            self.after(0, self._update_response_text, f"   Payload ASCII: {ascii_payload}\n")

                elif service == 0x7F and len(data_bytes) >= 5:
                    # Negative response
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

                    self.after(0, self._update_response_text, f"   Failed Service: 0x{failed_service:02X}\n")
                    self.after(0, self._update_response_text, f"   NRC: 0x{nrc:02X} - {nrc_codes.get(nrc, 'Unknown error')}\n")

        elif (first_byte & 0xF0) == 0x20:  # Continuation frame
            frame_num = first_byte & 0x0F
            self.after(0, self._update_response_text, f"   Frame Type: Continuation Frame {frame_num}\n")

            # Extract data
            payload = data_bytes[1:] if len(data_bytes) > 1 else []
            if payload:
                self.after(0, self._update_response_text, f"   Payload ({len(payload)} bytes): {' '.join(f'{b:02X}' for b in payload)}\n")

                # Try ASCII
                ascii_payload = ""
                for byte in payload:
                    if 32 <= byte <= 126:
                        ascii_payload += chr(byte)
                    elif byte == 0x00:
                        ascii_payload += "·"
                    else:
                        ascii_payload += "."

                if ascii_payload.replace(".", "").replace("·", ""):
                    self.after(0, self._update_response_text, f"   Payload ASCII: {ascii_payload}\n")

        elif first_byte == 0x7F:  # Negative response (single frame)
            self.after(0, self._update_response_text, "   Frame Type: Negative Response (Single Frame)\n")

            if len(data_bytes) >= 3:
                failed_service = data_bytes[1]
                nrc = data_bytes[2]

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

                self.after(0, self._update_response_text, f"   Failed Service: 0x{failed_service:02X}\n")
                self.after(0, self._update_response_text, f"   NRC: 0x{nrc:02X} - {nrc_codes.get(nrc, 'Unknown error')}\n")

        else:
            # Single frame response
            if len(data_bytes) >= 3:
                service = data_bytes[0]
                did_high = data_bytes[1]
                did_low = data_bytes[2]
                did = (did_high << 8) | did_low

                service_name = {
                    0x62: "Positive Response to Read Data By Identifier (0x22)",
                }.get(service, f"Unknown service 0x{service:02X}")

                self.after(0, self._update_response_text, f"   Service: 0x{service:02X} ({service_name})\n")
                self.after(0, self._update_response_text, f"   DID: 0x{did:04X}\n")

                if len(data_bytes) > 3:
                    payload = data_bytes[3:]
                    self.after(0, self._update_response_text, f"   Payload ({len(payload)} bytes): {' '.join(f'{b:02X}' for b in payload)}\n")

                    # Try ASCII
                    ascii_payload = ""
                    for byte in payload:
                        if 32 <= byte <= 126:
                            ascii_payload += chr(byte)
                        elif byte == 0x00:
                            ascii_payload += "·"
                        else:
                            ascii_payload += "."

                    if ascii_payload.replace(".", "").replace("·", ""):
                        self.after(0, self._update_response_text, f"   Payload ASCII: {ascii_payload}\n")
            else:
                self.after(0, self._update_response_text, f"   Unknown frame format\n")
                self.after(0, self._update_response_text, f"   Raw bytes: {' '.join(f'{b:02X}' for b in data_bytes)}\n")

    def _update_response_text(self, text):
        """Update response textbox with new text"""
        self.response_text.insert("end", text)
        self.response_text.see("end")

    def load_uds_example(self, example_type):
        """Load example UDS responses"""
        examples = {
            "vin": """vcan0  7E8   [8]  10 14 62 F1 90 46 55 43
vcan0  7E8   [8]  21 59 54 45 43 48 2D 56
vcan0  7E8   [8]  22 49 4E 2D 30 30 30 31""",

            "boot": """vcan0  7E8   [8]  10 0E 62 F1 80 46 55 43
vcan0  7E8   [8]  21 59 2D 42 4F 4F 54 2D
vcan0  7E8   [8]  22 56 31 2E 30 00 00 00""",

            "app": """vcan0  7E8   [8]  10 10 62 F1 81 46 55 43
vcan0  7E8   [8]  21 59 2D 41 50 50 2D 56
vcan0  7E8   [8]  22 32 2E 35 2E 31 00 00""",

            "serial": """vcan0  7E8   [8]  10 12 62 F1 8C 53 4E 2D
vcan0  7E8   [8]  21 46 55 43 59 2D 38 38
vcan0  7E8   [8]  22 38 38 38 38 38 38 38"""
        }

        if example_type in examples:
            self.uds_response_entry.delete("1.0", "end")
            self.uds_response_entry.insert("1.0", examples[example_type])
            messagebox.showinfo("Example Loaded", f"Loaded {example_type.upper()} response example")

    def clear_uds_input(self):
        """Clear the UDS response input"""
        self.uds_response_entry.delete("1.0", "end")
        self.results_text.delete("1.0", "end")

    def analyze_uds_response(self):
        """Analyze UDS response and decode the data"""
        raw_text = self.uds_response_entry.get("1.0", "end-1c").strip()

        if not raw_text:
            messagebox.showwarning("Warning", "Please paste UDS response data")
            return

        lines = raw_text.split('\n')
        frames = []

        # Parse each line
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for data bytes in typical candump format
            if '[' in line and ']' in line:
                # Extract data bytes part (after the closing bracket)
                parts = line.split(']')
                if len(parts) > 1:
                    hex_part = parts[1].strip()
                    if hex_part:
                        try:
                            # Convert hex string to bytes
                            bytes_list = [int(b, 16) for b in hex_part.split() if b]
                            if bytes_list:  # Only add if we found bytes
                                frames.append(bytes_list)
                        except ValueError as e:
                            continue

        if not frames:
            # Try alternative format - just hex bytes
            all_bytes = []
            for line in lines:
                try:
                    bytes_list = [int(b, 16) for b in line.split() if len(b) == 2]
                    if bytes_list:
                        all_bytes.extend(bytes_list)
                except:
                    continue

            if all_bytes:
                # Group bytes into frames of 8
                for i in range(0, len(all_bytes), 8):
                    frames.append(all_bytes[i:i+8])

        if not frames:
            self.results_text.delete("1.0", "end")
            self.results_text.insert("1.0", "❌ No valid data found. Please check format.\n\nExpected format:\nvcan0  7E8   [8]  10 14 62 F1 90 46 55 43")
            return

        # Analyze frames
        result = "=" * 60 + "\n"
        result += "               UDS RESPONSE ANALYZER\n"
        result += "=" * 60 + "\n\n"

        total_ascii = ""

        for i, frame_bytes in enumerate(frames):
            result += f"📦 FRAME {i+1} ({len(frame_bytes)} bytes):\n"
            result += f"   Hex: {' '.join(f'{b:02X}' for b in frame_bytes)}\n"

            # Check first byte for frame type
            first_byte = frame_bytes[0]

            if first_byte == 0x10:  # First frame
                result += "   Type: First Frame (Multi-frame response)\n"

                if len(frame_bytes) >= 2:
                    total_len = frame_bytes[1]
                    result += f"   Total Data Length: {total_len} bytes\n"

                if len(frame_bytes) >= 3:
                    service = frame_bytes[2]
                    service_name = {
                        0x62: "Read Data By Identifier (0x22)",
                        0x7F: "Negative Response",
                        0x67: "Security Access (0x27)",
                        0x6E: "Tester Present (0x3E)"
                    }.get(service, f"Unknown service 0x{service:02X}")
                    result += f"   Service: 0x{service:02X} ({service_name})\n"

                if len(frame_bytes) >= 5:
                    did = (frame_bytes[3] << 8) | frame_bytes[4]
                    did_info = {
                        0xF190: "VIN (Vehicle Identification Number)",
                        0xF180: "Boot Software ID",
                        0xF181: "Application Software ID",
                        0xF187: "Spare Part Number",
                        0xF18C: "ECU Serial Number",
                        0xF186: "Active Session",
                        0xF188: "ECU SW Number",
                        0xF198: "Repair Shop Code"
                    }

                    result += f"   DID: 0x{did:04X}"
                    if did in did_info:
                        result += f" - {did_info[did]}\n"
                    else:
                        result += f" (Unknown DID)\n"

                # Extract ASCII data from first frame
                if len(frame_bytes) > 5:
                    ascii_part = ""
                    for byte in frame_bytes[5:]:
                        if 32 <= byte <= 126:  # Printable ASCII
                            ascii_part += chr(byte)
                        elif byte == 0x00:
                            ascii_part += "·"  # Show null as dot
                        else:
                            ascii_part += f"\\x{byte:02X}"

                    if ascii_part:
                        result += f"   Data: {ascii_part}\n"
                        total_ascii += ascii_part.replace("·", "")

            elif (first_byte & 0xF0) == 0x20:  # Continuation frame
                frame_num = first_byte & 0x0F
                result += f"   Type: Continuation Frame {frame_num}\n"

                # Extract ASCII data from continuation frame
                ascii_part = ""
                for byte in frame_bytes[1:]:
                    if 32 <= byte <= 126:  # Printable ASCII
                        ascii_part += chr(byte)
                        total_ascii += chr(byte)
                    elif byte == 0x00:
                        ascii_part += "·"
                    else:
                        ascii_part += f"\\x{byte:02X}"
                        total_ascii += f"\\x{byte:02X}"

                if ascii_part:
                    result += f"   Data: {ascii_part}\n"

            elif first_byte == 0x7F:  # Negative response
                result += "   Type: Negative Response\n"
                if len(frame_bytes) >= 3:
                    failed_service = frame_bytes[1]
                    nrc = frame_bytes[2]
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
                    result += f"   Failed Service: 0x{failed_service:02X}\n"
                    result += f"   NRC: 0x{nrc:02X} - {nrc_codes.get(nrc, 'Unknown error')}\n"

            else:
                result += f"   Type: Unknown (0x{first_byte:02X})\n"

            result += "\n"

        # Show complete decoded message
        if total_ascii:
            result += "-" * 60 + "\n"
            result += "📊 COMPLETE DECODED MESSAGE:\n\n"

            # Clean up the ASCII (remove null bytes and non-printable)
            clean_ascii = ""
            hex_representation = ""

            for i, char in enumerate(total_ascii):
                if char == "·":
                    continue
                elif len(char) > 1:  # \xXX format
                    hex_representation += char + " "
                elif 32 <= ord(char) <= 126:  # Printable ASCII
                    clean_ascii += char
                    hex_representation += f"{ord(char):02X} "
                else:
                    hex_representation += f"\\x{ord(char):02X} "

            if clean_ascii:
                result += f"   ASCII: {clean_ascii}\n"

            if hex_representation.strip():
                result += f"   Hex: {hex_representation.strip()}\n"

        # Show UDS quick reference
        result += "\n" + "=" * 60 + "\n"
        result += "📚 UDS QUICK REFERENCE:\n\n"
        result += "Service 0x22 - Read Data By Identifier\n"
        result += "  • Positive Response: 0x62\n"
        result += "  • First Frame: 0x10 XX 62 F1 90 ...\n"
        result += "  • Continuation: 0x2N (N = frame number)\n\n"
        result += "Common DIDs:\n"
        result += "  • 0xF190 - VIN\n"
        result += "  • 0xF180 - Boot Software ID\n"
        result += "  • 0xF181 - Application Software ID\n"
        result += "  • 0xF18C - ECU Serial Number\n"
        result += "=" * 60

        # Display results
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", result)

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

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(12, min(18, int(14 * scale_factor)))
        button_font_size = max(12, min(18, int(14 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))
        results_font_size = max(11, min(16, int(13 * scale_factor)))

        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))

        # Update button and entry sizes
        btn_height = max(35, min(55, int(45 * scale_factor)))
        entry_height = max(30, min(45, int(35 * scale_factor)))
        small_btn_size = max(35, min(60, int(45 * scale_factor)))
        btn_width = max(120, min(200, int(150 * scale_factor)))

        self.doip_btn.configure(height=btn_height, font=("Arial", button_font_size))
        self.xcp_btn.configure(height=btn_height, font=("Arial", button_font_size))
        self.did_read_btn.configure(height=btn_height, font=("Arial", button_font_size))
        self.show_response_btn.configure(height=btn_height, font=("Arial", button_font_size))
        self.analyze_btn.configure(height=btn_height + 5, font=("Arial", button_font_size))
        self.load_vin_example_btn.configure(height=small_btn_size, font=("Arial", button_font_size-1))
        self.load_boot_example_btn.configure(height=small_btn_size, font=("Arial", button_font_size-1))
        self.clear_btn.configure(height=small_btn_size, font=("Arial", button_font_size-1))
        self.help_btn.configure(height=small_btn_size, width=small_btn_size, font=("Arial", button_font_size))
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-2), width=btn_width)
        self.view_failures_btn.configure(height=small_btn_size, font=("Arial", button_font_size-2), width=btn_width)

        # Configure entry fields
        font_cfg = ("Arial", label_font_size)
        self.xcp_id.configure(height=entry_height, font=font_cfg)
        self.uds_target_id.configure(height=entry_height, font=font_cfg)
        self.uds_response_id.configure(height=entry_height, font=font_cfg)
        self.custom_did_entry.configure(height=entry_height, font=font_cfg)
        self.start_did_entry.configure(height=entry_height, font=font_cfg)
        self.end_did_entry.configure(height=entry_height, font=font_cfg)
        self.timeout_entry.configure(height=entry_height, font=font_cfg)

        # Configure text areas
        self.uds_response_entry.configure(font=("Consolas", results_font_size))
        self.results_text.configure(font=("Consolas", results_font_size))
        self.response_text.configure(font=("Consolas", results_font_size))

        # Update dropdowns
        self.did_select.configure(height=entry_height, font=font_cfg,
                                 dropdown_font=("Arial", label_font_size))

        # Configure checkboxes
        self.doip_interface_check.configure(font=("Arial", checkbox_font_size))
        self.xcp_interface_check.configure(font=("Arial", checkbox_font_size))
        self.did_interface_check.configure(font=("Arial", checkbox_font_size))

        # Scale tabview fonts
        if hasattr(self.tabs, '_segmented_button'):
            self.tabs._segmented_button.configure(font=("Arial", label_font_size))


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

        # NEW: View Failures button
        self.view_failures_btn = ctk.CTkButton(self.head_frame, text="📊 View Failures", 
                      fg_color="#e74c3c", command=lambda: app.show_failure_cases())
        self.view_failures_btn.pack(side="right", padx=5)

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
        self.view_failures_btn.configure(height=small_btn_size, font=("Arial", button_font_size-2), width=btn_width)

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
        if len(self.scroll.winfo_children()) > 60: 
            self.scroll.winfo_children()[0].destroy()
        vals = [time.strftime("%H:%M:%S"), hex(aid), "Unknown", "---", " ".join(f"{b:02X}" for b in data)]

        if self.app.dbc_db:
            try:
                m = self.app.dbc_db.get_message_by_frame_id(aid)
                if m:
                    vals[2] = m.name
                    vals[3] = str(m.decode(data))
            except: 
                pass

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
        for w in self.scroll.winfo_children(): 
            w.destroy()

    def toggle_sim(self):
        if not self.is_monitoring:
            self.is_monitoring = True
            threading.Thread(target=self._sim, daemon=True).start()
        else: 
            self.is_monitoring = False

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