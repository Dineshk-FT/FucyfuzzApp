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

        self.title_label = ctk.CTkLabel(self, text="System Configuration", font=FontConfig.get_title_font(1.0))
        self.title_label.pack(anchor="w", pady=(0, 20))
        self.register_widget(self.title_label, "title")

        # Grid for options
        self.grid_frame = ctk.CTkFrame(self)
        self.grid_frame.pack(fill="x", pady=20)

        # Working Directory Section
        wd_label = ctk.CTkLabel(self.grid_frame, text="Fucyfuzz Path:")
        wd_label.grid(row=0, column=0, padx=20, pady=20)
        self.register_widget(wd_label, "label")

        self.wd_entry = ctk.CTkEntry(self.grid_frame, placeholder_text="/path/to/fucyfuzz")
        self.wd_entry.grid(row=0, column=1, padx=(20, 5), pady=20, sticky="ew")
        self.wd_entry.insert(0, app.working_dir)
        self.register_widget(self.wd_entry, "entry")

        self.browse_btn = ctk.CTkButton(self.grid_frame, text="Browse", command=self.browse_wd)
        self.browse_btn.grid(row=0, column=2, padx=20, pady=20)
        self.register_widget(self.browse_btn, "button")

        # Interface Section
        interface_label = ctk.CTkLabel(self.grid_frame, text="Interface:")
        interface_label.grid(row=1, column=0, padx=20, pady=20)
        self.register_widget(interface_label, "label")

        self.driver = ctk.CTkOptionMenu(self.grid_frame, values=["socketcan", "vector", "pcan"],
                                        fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.driver.grid(row=1, column=1, padx=20, pady=20, sticky="ew")
        self.register_widget(self.driver, "dropdown")

        channel_label = ctk.CTkLabel(self.grid_frame, text="Channel:")
        channel_label.grid(row=2, column=0, padx=20, pady=20)
        self.register_widget(channel_label, "label")

        self.channel = ctk.CTkEntry(self.grid_frame, placeholder_text="vcan0")
        self.channel.grid(row=2, column=1, padx=20, pady=20, sticky="ew")
        self.register_widget(self.channel, "entry")

        self.grid_frame.grid_columnconfigure(1, weight=1)

        self.save_btn = ctk.CTkButton(self, text="Save Config", command=self.save)
        self.save_btn.pack(pady=20)
        self.register_widget(self.save_btn, "button_large")

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        super()._apply_scaling(scale_factor)
        
        # Additional frame-specific scaling
        padding = FontConfig.get_padding(scale_factor)
        self.grid_frame.configure(padx=padding, pady=padding)
        
        # Update grid row/column padding
        for child in self.grid_frame.winfo_children():
            info = child.grid_info()
            if info:
                child.grid_configure(padx=padding, pady=padding//2)

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
        self.button_container.pack(expand=True, fill="both", pady=40)

        # ADDED: Interface checkbox
        self.interface_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.interface_frame.pack(pady=(0, 20))

        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(self.interface_frame, text="Use -i vcan0 interface",
                                             variable=self.use_interface)
        self.interface_check.pack()
        self.register_widget(self.interface_check, "checkbox")

        self.start_btn = ctk.CTkButton(self.button_container, text="▶ Start Listener",
                      command=self.run_listener)
        self.start_btn.pack(expand=True)
        self.register_widget(self.start_btn, "button_large")

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
        super()._apply_scaling(scale_factor)


class DemoFrame(ScalableFrame):
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

        self.start_speeding_btn = self._demo_button(
            self.speed_frame, "Start Speed Fuzz", self.start_speeding
        )
        self.stop_speeding_btn = self._demo_button(
            self.speed_frame, "Stop Speed Fuzz", self.stop_speeding
        )
        self.reset_speed_btn = self._demo_button(
            self.speed_frame, "Reset Speed", self.reset_speed
        )

        # ================= INDICATOR FUZZ =================
        self.indicator_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.indicator_frame.pack(pady=10)

        self.start_indicator_fuzz_btn = self._demo_button(
            self.indicator_frame, "Start Indicator Fuzz", self.start_indicator_fuzz
        )
        self.stop_indicator_fuzz_btn = self._demo_button(
            self.indicator_frame, "Stop Indicator Fuzz", self.stop_indicator_fuzz
        )

        # ================= DOOR FUZZ =================
        self.doors_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.doors_frame.pack(pady=10)

        self.start_door_fuzz_btn = self._demo_button(
            self.doors_frame, "Start Door Fuzz", self.start_door_fuzz
        )
        self.stop_door_fuzz_btn = self._demo_button(
            self.doors_frame, "Stop Door Fuzz", self.stop_door_fuzz
        )

        # ================= STATE =================
        self.fuzzing_speed_active = False
        self.fuzzing_indicator_active = False
        self.fuzzing_door_active = False

        self.speed_process = None
        self.indicator_process = None
        self.door_process = None

    # ======================================================
    # BUTTON FACTORY (CRITICAL FIX)
    # ======================================================
    def _demo_button(self, parent, text, command):
        btn = ctk.CTkButton(
            parent,
            text=text,
            command=command,
            font=FontConfig.get_button_font(1.0),
            width=140,
            height=32,
            anchor="center"
        )
        btn.pack(side="left", padx=5)
        self.register_widget(btn, "button")
        return btn

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
    # SPEED FUZZ
    # ======================================================
    def start_speeding(self):
        if self.fuzzing_speed_active:
            return

        self.fuzzing_speed_active = True
        self.start_speeding_btn.configure(text="Fuzzing...", fg_color="#c0392b")

        self.speed_process = self.run_demo_command(
            ["fuzzer", "mutate", "244", "..", "-d", "0.5"],
            "Speed fuzz started"
        )

    def stop_speeding(self):
        if self.speed_process:
            self.speed_process.terminate()
            self.speed_process = None

        self.fuzzing_speed_active = False
        self.start_speeding_btn.configure(text="Start Speed Fuzz", fg_color="#1f538d")
        self.app._console_write("[DEMO] Speed fuzz stopped\n")

    def reset_speed(self):
        self.stop_speeding()
        self.run_demo_command(
            ["send", "message", "0x244#00"],
            "Speed reset"
        )

    # ======================================================
    # INDICATOR FUZZ
    # ======================================================
    def start_indicator_fuzz(self):
        if self.fuzzing_indicator_active:
            return

        self.fuzzing_indicator_active = True
        self.start_indicator_fuzz_btn.configure(text="Fuzzing...", fg_color="#c0392b")

        self.indicator_process = self.run_demo_command(
            ["fuzzer", "mutate", "188", ".", "-d", "0.5"],
            "Indicator fuzz started"
        )

    def stop_indicator_fuzz(self):
        if self.indicator_process:
            self.indicator_process.terminate()
            self.indicator_process = None

        self.fuzzing_indicator_active = False
        self.start_indicator_fuzz_btn.configure(
            text="Start Indicator Fuzz",
            fg_color="#1f538d"
        )

        self.run_demo_command(
            ["send", "message", "0x188#00"],
            "Indicators OFF"
        )

    # ======================================================
    # DOOR FUZZ
    # ======================================================
    def start_door_fuzz(self):
        if self.fuzzing_door_active:
            return

        self.fuzzing_door_active = True
        self.start_door_fuzz_btn.configure(text="Fuzzing...", fg_color="#c0392b")

        self.door_process = self.run_demo_command(
            ["fuzzer", "mutate", "19B", "........", "-d", "0.5"],
            "Door fuzz started"
        )

    def stop_door_fuzz(self):
        if self.door_process:
            self.door_process.terminate()
            self.door_process = None

        self.fuzzing_door_active = False
        self.start_door_fuzz_btn.configure(text="Start Door Fuzz", fg_color="#1f538d")

        self.run_demo_command(
            ["send", "message", "0x19B#00.00.00.00"],
            "Doors reset"
        )

    # ======================================================
    # SCALING (NO AUTO-RESIZE BUG)
    # ======================================================
    def _apply_scaling(self, scale_factor):
        super()._apply_scaling(scale_factor)

        font = FontConfig.get_button_font(scale_factor)
        width = max(120, int(140 * scale_factor))
        height = max(28, int(32 * scale_factor))

        buttons = [
            self.start_speeding_btn,
            self.stop_speeding_btn,
            self.reset_speed_btn,
            self.start_indicator_fuzz_btn,
            self.stop_indicator_fuzz_btn,
            self.start_door_fuzz_btn,
            self.stop_door_fuzz_btn
        ]

        for btn in buttons:
            if btn.winfo_exists():
                btn.configure(font=font, width=width, height=height)


class FuzzerFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        # Header
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(
            self.head_frame,
            text="Signal Fuzzer",
            font=FontConfig.get_title_font(1.0)
        )
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        # Buttons
        self.help_btn = ctk.CTkButton(
            self.head_frame,
            text="❓",
            fg_color="#f39c12",
            text_color="white",
            command=lambda: app.show_module_help("fuzzer")
        )
        self.help_btn.pack(side="right", padx=10)
        self.register_widget(self.help_btn, "button_small")

        self.report_btn = ctk.CTkButton(
            self.head_frame,
            text="📥 Report (PDF)",
            command=lambda: app.save_module_report("Fuzzer")
        )
        self.report_btn.pack(side="right", padx=10)
        self.register_widget(self.report_btn, "button_small")

        # NEW: View Failures button
        self.view_failures_btn = ctk.CTkButton(
            self.head_frame,
            text="📊 View Failures",
            fg_color="#e74c3c",
            command=lambda: app.show_failure_cases()
        )
        self.view_failures_btn.pack(side="right", padx=10)
        self.register_widget(self.view_failures_btn, "button_small")

        # Tabs
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, pady=20)

        #
        # ───────────────────────────────────────────── Targeted Fuzz ─────────────────────────────────────────────
        #
        self.smart_tab = self.tabs.add("Targeted")

        targeted_label = ctk.CTkLabel(self.smart_tab, text="Select Message (Optional):")
        targeted_label.pack(pady=(20, 10))
        self.register_widget(targeted_label, "label")

        self.msg_select = ctk.CTkOptionMenu(
            self.smart_tab,
            values=["No DBC Loaded"],
            command=self.on_msg_select,
            fg_color="#1f538d",
            button_color="#1f538d",
            button_hover_color="#14375e"
        )
        self.msg_select.pack(pady=10, fill="x", padx=20)
        self.register_widget(self.msg_select, "dropdown")

        # Manual ID entry
        manual_label = ctk.CTkLabel(self.smart_tab, text="OR Enter Manual ID:")
        manual_label.pack(pady=(10, 5))
        self.register_widget(manual_label, "label")

        self.tid = ctk.CTkEntry(self.smart_tab, placeholder_text="Target ID (e.g., 0x123)")
        self.tid.pack(pady=5, fill="x", padx=20)
        self.register_widget(self.tid, "entry")

        # Data pattern (TARGETED)
        self.data = ctk.CTkEntry(
            self.smart_tab,
            placeholder_text="Data Pattern (Optional - e.g., 1122..44)"
        )
        self.data.pack(pady=10, fill="x", padx=20)
        self.register_widget(self.data, "entry")

        self.mode = ctk.CTkOptionMenu(
            self.smart_tab,
            values=["brute", "mutate"],
            fg_color="#1f538d",
            button_color="#1f538d",
            button_hover_color="#14375e"
        )
        self.mode.pack(pady=20, fill="x", padx=20)
        self.register_widget(self.mode, "dropdown")

        # Interface checkbox (TARGETED)
        self.interface_frame = ctk.CTkFrame(self.smart_tab, fg_color="transparent")
        self.interface_frame.pack(pady=10, fill="x", padx=20)

        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(
            self.interface_frame,
            text="Use -i vcan0 interface",
            variable=self.use_interface
        )
        self.interface_check.pack()
        self.register_widget(self.interface_check, "checkbox")

        # Launch targeted fuzzing
        self.launch_btn = ctk.CTkButton(
            self.smart_tab,
            text="Start Targeted Fuzzing",
            command=self.run_smart,
            fg_color="#27ae60"
        )
        self.launch_btn.pack(pady=20, fill="x", padx=20)
        self.register_widget(self.launch_btn, "button_large")

        #
        # ───────────────────────────────────────────── Random Fuzz ─────────────────────────────────────────────
        #
        self.rnd_tab = self.tabs.add("Random")

        # Interface checkbox (RANDOM)
        self.random_interface_frame = ctk.CTkFrame(self.rnd_tab, fg_color="transparent")
        self.random_interface_frame.pack(pady=(20, 10), fill="x", padx=20)

        self.random_use_interface = ctk.BooleanVar(value=True)
        self.random_interface_check = ctk.CTkCheckBox(
            self.random_interface_frame,
            text="Use -i vcan0 interface",
            variable=self.random_use_interface
        )
        self.random_interface_check.pack()
        self.register_widget(self.random_interface_check, "checkbox")

        # Data pattern (RANDOM) — FIXED: renamed to avoid overriding self.data
        self.random_data = ctk.CTkEntry(
            self.rnd_tab,
            placeholder_text="Data Pattern (Optional - e.g., 1122..44)"
        )
        self.random_data.pack(pady=10, fill="x", padx=20)
        self.register_widget(self.random_data, "entry")

        self.random_btn = ctk.CTkButton(
            self.rnd_tab,
            text="Start Random Fuzzing",
            fg_color="#c0392b",
            command=self.run_random
        )
        self.random_btn.pack(pady=10, fill="x", padx=20)
        self.register_widget(self.random_btn, "button_large")

    #
    # ───────────────────────────────────────────── Fuzzing Logic ─────────────────────────────────────────────
    #

    def run_smart(self):
        """Run targeted fuzzing with optional interface"""
        tid = self.tid.get().strip()

        if not tid:
            messagebox.showerror("Error", "Please enter a Target ID")
            return

        data = self.data.get().strip()
        mode = self.mode.get()

        cmd = ["fuzzer", mode]

        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])

        cmd.append(tid)

        if data:
            cmd.append(data)

        self.app.run_command(cmd, "Fuzzer")

    def run_random(self):
        """Run random fuzzing with optional interface + optional data"""
        cmd = ["fuzzer", "random"]

        # interface
        if self.random_use_interface.get():
            cmd.extend(["-i", "vcan0"])

        # random data
        random_data = self.random_data.get().strip()
        if random_data:
            cmd.append(random_data)

        self.app.run_command(cmd, "Fuzzer")

    #
    # ───────────────────────────────────────────── Scaling Logic ─────────────────────────────────────────────
    #

    def _apply_scaling(self, scale_factor):
        super()._apply_scaling(scale_factor)

        if hasattr(self.tabs, '_segmented_button'):
            self.tabs._segmented_button.configure(
                font=FontConfig.get_tab_font(scale_factor)
            )

        tab_padding = FontConfig.get_padding(scale_factor)
        self.tabs.pack_configure(pady=tab_padding)

        for tab_name in ["Targeted", "Random"]:
            tab = self.tabs.tab(tab_name)
            for child in tab.winfo_children():
                if isinstance(child, (ctk.CTkFrame, ctk.CTkScrollableFrame)):
                    child.pack_configure(padx=tab_padding, pady=tab_padding)

    #
    # ───────────────────────────────────────────── Helpers ─────────────────────────────────────────────
    #

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

        self.title_label = ctk.CTkLabel(self.head_frame, text="Length Attack", font=FontConfig.get_title_font(1.0))
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("lenattack"))
        self.help_btn.pack(side="right", padx=10)
        self.register_widget(self.help_btn, "button_small")

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("LengthAttack"))
        self.report_btn.pack(side="right", padx=10)
        self.register_widget(self.report_btn, "button_small")

        # NEW: View Failures button
        self.view_failures_btn = ctk.CTkButton(self.head_frame, text="📊 View Failures", 
                      fg_color="#e74c3c", command=lambda: app.show_failure_cases())
        self.view_failures_btn.pack(side="right", padx=10)
        self.register_widget(self.view_failures_btn, "button_small")

        self.card = ctk.CTkFrame(self, corner_radius=12)
        self.card.pack(fill="x", padx=30, pady=30)

        # Row 0: DBC Select (Optional)
        dbc_label = ctk.CTkLabel(self.card, text="DBC Message (Optional):")
        dbc_label.grid(row=0, column=0, padx=20, pady=15)
        self.register_widget(dbc_label, "label")

        self.msg_select = ctk.CTkOptionMenu(self.card, values=["No DBC Loaded"], command=self.on_msg_select,
                                            fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.msg_select.grid(row=0, column=1, padx=20, pady=15, sticky="ew")
        self.register_widget(self.msg_select, "dropdown")

        # Row 1: Target ID (Manual entry - always available)
        target_label = ctk.CTkLabel(self.card, text="OR Enter Target ID (Hex):")
        target_label.grid(row=1, column=0, padx=20, pady=15)
        self.register_widget(target_label, "label")

        self.lid = ctk.CTkEntry(self.card, placeholder_text="0x123")
        self.lid.grid(row=1, column=1, padx=20, pady=15, sticky="ew")
        self.register_widget(self.lid, "entry")

        # Row 2: Extra Args
        args_label = ctk.CTkLabel(self.card, text="Extra Args:")
        args_label.grid(row=2, column=0, padx=20, pady=15)
        self.register_widget(args_label, "label")

        self.largs = ctk.CTkEntry(self.card, placeholder_text="Optional (e.g. -v)")
        self.largs.grid(row=2, column=1, padx=20, pady=15, sticky="ew")
        self.register_widget(self.largs, "entry")

        # Row 3: Interface checkbox
        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(self.card, text="Use -i vcan0 interface",
                                             variable=self.use_interface)
        self.interface_check.grid(row=3, column=0, columnspan=2, padx=20, pady=15, sticky="w")
        self.register_widget(self.interface_check, "checkbox")

        self.card.grid_columnconfigure(1, weight=1)

        self.start_btn = ctk.CTkButton(self, text="START ATTACK", fg_color="#8e44ad", command=self.run_attack)
        self.start_btn.pack(fill="x", padx=50, pady=30)
        self.register_widget(self.start_btn, "button_large")

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        super()._apply_scaling(scale_factor)
        
        # Update card padding
        card_padding = FontConfig.get_padding(scale_factor)
        self.card.pack_configure(padx=card_padding * 1.5, pady=card_padding * 1.5)
        
        # Update grid cell padding
        for child in self.card.winfo_children():
            info = child.grid_info()
            if info:
                child.grid_configure(padx=card_padding, pady=card_padding//1.5)

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

        self.title_label = ctk.CTkLabel(self.head_frame, text="DCM Diagnostics", font=FontConfig.get_title_font(1.0))
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("dcm"))
        self.help_btn.pack(side="right", padx=5)
        self.register_widget(self.help_btn, "button_small")

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("DCM"))
        self.report_btn.pack(side="right", padx=5)
        self.register_widget(self.report_btn, "button_small")

        # NEW: View Failures button
        self.view_failures_btn = ctk.CTkButton(self.head_frame, text="📊 View Failures", 
                      fg_color="#e74c3c", command=lambda: app.show_failure_cases())
        self.view_failures_btn.pack(side="right", padx=5)
        self.register_widget(self.view_failures_btn, "button_small")

        # DCM Action Selection
        action_label = ctk.CTkLabel(self, text="DCM Action:")
        action_label.pack(pady=(20, 10))
        self.register_widget(action_label, "label")

        self.dcm_act = ctk.CTkOptionMenu(self,
                                       values=["discovery", "services", "subfunc", "dtc", "testerpresent"],
                                       fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e",
                                       command=self.on_dcm_action_change)
        self.dcm_act.pack(pady=10, fill="x", padx=20)
        self.dcm_act.set("discovery")
        self.register_widget(self.dcm_act, "dropdown")

        # DBC Message Selection (Optional)
        dbc_label = ctk.CTkLabel(self, text="DBC Message (Optional):")
        dbc_label.pack(pady=(10, 5))
        self.register_widget(dbc_label, "label")

        self.msg_select = ctk.CTkOptionMenu(self, values=["No DBC Loaded"], command=self.on_msg_select,
                                            fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.msg_select.pack(pady=5, fill="x", padx=20)
        self.register_widget(self.msg_select, "dropdown")

        # DCM Parameters Frame
        self.dcm_params_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dcm_params_frame.pack(fill="x", pady=10, padx=20)

        # Target ID (for most DCM commands)
        target_label = ctk.CTkLabel(self.dcm_params_frame, text="Target ID:")
        target_label.pack(anchor="w")
        self.register_widget(target_label, "label")

        self.dcm_tid = ctk.CTkEntry(self.dcm_params_frame, placeholder_text="e.g., 0x733")
        self.dcm_tid.pack(fill="x", pady=5)
        self.register_widget(self.dcm_tid, "entry")

        # Response ID (for services, subfunc, dtc)
        self.dcm_rid_label = ctk.CTkLabel(self.dcm_params_frame, text="Response ID:")
        self.dcm_rid_label.pack(anchor="w")
        self.register_widget(self.dcm_rid_label, "label")

        self.dcm_rid = ctk.CTkEntry(self.dcm_params_frame, placeholder_text="e.g., 0x633")
        self.dcm_rid.pack(fill="x", pady=5)
        self.register_widget(self.dcm_rid, "entry")

        # Additional parameters for subfunc
        self.subfunc_frame = ctk.CTkFrame(self.dcm_params_frame, fg_color="transparent")

        self.subfunc_label = ctk.CTkLabel(self.subfunc_frame, text="Subfunction Parameters:")
        self.subfunc_label.pack(anchor="w")
        self.register_widget(self.subfunc_label, "label")

        self.subfunc_params_frame = ctk.CTkFrame(self.subfunc_frame, fg_color="transparent")

        service_label = ctk.CTkLabel(self.subfunc_params_frame, text="Service:")
        service_label.grid(row=0, column=0, padx=(0, 5))
        self.register_widget(service_label, "label")

        self.dcm_service = ctk.CTkEntry(self.subfunc_params_frame, placeholder_text="0x22", width=80)
        self.dcm_service.grid(row=0, column=1, padx=5)
        self.register_widget(self.dcm_service, "entry")

        subfunc_label = ctk.CTkLabel(self.subfunc_params_frame, text="Subfunc:")
        subfunc_label.grid(row=0, column=2, padx=(10, 5))
        self.register_widget(subfunc_label, "label")

        self.dcm_subfunc = ctk.CTkEntry(self.subfunc_params_frame, placeholder_text="2", width=60)
        self.dcm_subfunc.grid(row=0, column=3, padx=5)
        self.register_widget(self.dcm_subfunc, "entry")

        data_label = ctk.CTkLabel(self.subfunc_params_frame, text="Data:")
        data_label.grid(row=0, column=4, padx=(10, 5))
        self.register_widget(data_label, "label")

        self.dcm_data = ctk.CTkEntry(self.subfunc_params_frame, placeholder_text="3", width=60)
        self.dcm_data.grid(row=0, column=5, padx=5)
        self.register_widget(self.dcm_data, "entry")

        self.subfunc_params_frame.grid_columnconfigure(6, weight=1)

        # DCM Options Frame
        self.dcm_options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dcm_options_frame.pack(fill="x", pady=10, padx=20)

        # Blacklist options
        self.blacklist_label = ctk.CTkLabel(self.dcm_options_frame, text="Blacklist IDs (space separated):")
        self.blacklist_label.pack(anchor="w")
        self.register_widget(self.blacklist_label, "label")

        self.dcm_blacklist = ctk.CTkEntry(self.dcm_options_frame, placeholder_text="0x123 0x456")
        self.dcm_blacklist.pack(fill="x", pady=5)
        self.register_widget(self.dcm_blacklist, "entry")

        # Auto blacklist
        self.autoblacklist_frame = ctk.CTkFrame(self.dcm_options_frame, fg_color="transparent")

        self.autoblacklist_label = ctk.CTkLabel(self.autoblacklist_frame, text="Auto Blacklist Count:")
        self.autoblacklist_label.pack(side="left")
        self.register_widget(self.autoblacklist_label, "label")

        self.dcm_autoblacklist = ctk.CTkEntry(self.autoblacklist_frame, placeholder_text="10", width=80)
        self.dcm_autoblacklist.pack(side="left", padx=10)
        self.register_widget(self.dcm_autoblacklist, "entry")

        # Extra Args
        extra_label = ctk.CTkLabel(self, text="Extra Args:")
        extra_label.pack(pady=(10, 5))
        self.register_widget(extra_label, "label")

        self.dcm_extra_args = ctk.CTkEntry(self, placeholder_text="Additional arguments")
        self.dcm_extra_args.pack(fill="x", pady=5, padx=20)
        self.register_widget(self.dcm_extra_args, "entry")

        # DCM Interface checkbox
        self.dcm_use_interface = ctk.BooleanVar(value=True)
        self.dcm_interface_check = ctk.CTkCheckBox(self, text="Use -i vcan0 interface",
                                                 variable=self.dcm_use_interface)
        self.dcm_interface_check.pack(pady=10, padx=20)
        self.register_widget(self.dcm_interface_check, "checkbox")

        # DCM Execute Button
        self.dcm_execute_btn = ctk.CTkButton(self, text="Execute DCM", command=self.run_dcm, fg_color="#8e44ad")
        self.dcm_execute_btn.pack(pady=20, fill="x", padx=20)
        self.register_widget(self.dcm_execute_btn, "button_large")

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
            self.subfunc_frame.pack(fill="x", pady=8)

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
        super()._apply_scaling(scale_factor)


class UDSFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="UDS Diagnostics", font=FontConfig.get_title_font(1.0))
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("uds"))
        self.help_btn.pack(side="right", padx=5)
        self.register_widget(self.help_btn, "button_small")

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("UDS"))
        self.report_btn.pack(side="right", padx=5)
        self.register_widget(self.report_btn, "button_small")

        # View Failures button
        self.view_failures_btn = ctk.CTkButton(self.head_frame, text="📊 View Failures", 
                      fg_color="#e74c3c", command=lambda: app.show_failure_cases())
        self.view_failures_btn.pack(side="right", padx=5)
        self.register_widget(self.view_failures_btn, "button_small")

        # UDS Action Selection
        action_label = ctk.CTkLabel(self, text="UDS Action:")
        action_label.pack(pady=(20, 10))
        self.register_widget(action_label, "label")

        self.uds_act = ctk.CTkOptionMenu(self,
                                       values=[
                                           "discovery", "services", "subservices", 
                                           "ecu_reset", "testerpresent", "security_seed",
                                           "dump_dids", "read_mem", "read_did"
                                       ],
                                       fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e",
                                       command=self.on_uds_action_change)
        self.uds_act.pack(pady=10, fill="x", padx=20)
        self.uds_act.set("discovery")
        self.register_widget(self.uds_act, "dropdown")

        # DBC Message Selection (Optional)
        dbc_label = ctk.CTkLabel(self, text="DBC Message (Optional):")
        dbc_label.pack(pady=(10, 5))
        self.register_widget(dbc_label, "label")

        self.msg_select = ctk.CTkOptionMenu(self, values=["No DBC Loaded"], command=self.on_msg_select,
                                            fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.msg_select.pack(pady=5, fill="x", padx=20)
        self.register_widget(self.msg_select, "dropdown")

        # UDS Parameters Frame
        self.uds_params_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.uds_params_frame.pack(fill="x", pady=10, padx=20)

        # Target ID (for most UDS commands)
        target_label = ctk.CTkLabel(self.uds_params_frame, text="Target ID:")
        target_label.pack(anchor="w")
        self.register_widget(target_label, "label")

        self.uds_tid = ctk.CTkEntry(self.uds_params_frame, placeholder_text="e.g., 0x733")
        self.uds_tid.pack(fill="x", pady=5)
        self.register_widget(self.uds_tid, "entry")

        # Response ID (for most commands)
        self.uds_rid_label = ctk.CTkLabel(self.uds_params_frame, text="Response ID:")
        self.uds_rid_label.pack(anchor="w", pady=(5, 0))
        self.register_widget(self.uds_rid_label, "label")

        self.uds_rid = ctk.CTkEntry(self.uds_params_frame, placeholder_text="e.g., 0x633")
        self.uds_rid.pack(fill="x", pady=5)
        self.register_widget(self.uds_rid, "entry")

        # ECU Reset Subfunction
        self.ecu_reset_frame = ctk.CTkFrame(self.uds_params_frame, fg_color="transparent")
        
        ecu_reset_label = ctk.CTkLabel(self.ecu_reset_frame, text="Reset Subfunction:")
        ecu_reset_label.pack(anchor="w", pady=(5, 0))
        self.register_widget(ecu_reset_label, "label")

        self.ecu_reset_subfunc = ctk.CTkEntry(self.ecu_reset_frame, placeholder_text="1 for Hard Reset")
        self.ecu_reset_subfunc.pack(fill="x", pady=5)
        self.register_widget(self.ecu_reset_subfunc, "entry")

        # Security Seed Parameters
        self.security_seed_frame = ctk.CTkFrame(self.uds_params_frame, fg_color="transparent")
        
        security_params_frame = ctk.CTkFrame(self.security_seed_frame, fg_color="transparent")
        security_params_frame.pack(fill="x", pady=5)
        
        level_label = ctk.CTkLabel(security_params_frame, text="Level:")
        level_label.grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.register_widget(level_label, "label")
        
        self.security_level = ctk.CTkEntry(security_params_frame, placeholder_text="0x3", width=80)
        self.security_level.grid(row=0, column=1, padx=5, sticky="w")
        self.register_widget(self.security_level, "entry")
        
        subfunc_label = ctk.CTkLabel(security_params_frame, text="Subfunction:")
        subfunc_label.grid(row=0, column=2, padx=(10, 5), sticky="w")
        self.register_widget(subfunc_label, "label")
        
        self.security_subfunc = ctk.CTkEntry(security_params_frame, placeholder_text="0x1", width=80)
        self.security_subfunc.grid(row=0, column=3, padx=5, sticky="w")
        self.register_widget(self.security_subfunc, "entry")
        
        # Security Options
        self.security_options_frame = ctk.CTkFrame(self.security_seed_frame, fg_color="transparent")
        self.security_options_frame.pack(fill="x", pady=5)
        
        self.retry_var = ctk.BooleanVar(value=True)
        self.retry_check = ctk.CTkCheckBox(self.security_options_frame, text="Retry (--r)", 
                                          variable=self.retry_var)
        self.retry_check.pack(side="left", padx=(0, 10))
        self.register_widget(self.retry_check, "checkbox")
        
        delay_label = ctk.CTkLabel(self.security_options_frame, text="Delay:")
        delay_label.pack(side="left", padx=(10, 5))
        self.register_widget(delay_label, "label")
        
        self.security_delay = ctk.CTkEntry(self.security_options_frame, placeholder_text="0.5", width=60)
        self.security_delay.pack(side="left")
        self.register_widget(self.security_delay, "entry")

        # DID Parameters for read_did
        self.did_frame = ctk.CTkFrame(self.uds_params_frame, fg_color="transparent")
        
        did_label = ctk.CTkLabel(self.did_frame, text="DID (Hex):")
        did_label.pack(anchor="w", pady=(5, 0))
        self.register_widget(did_label, "label")
        
        self.did_entry = ctk.CTkEntry(self.did_frame, placeholder_text="0xF190 (VIN)")
        self.did_entry.pack(fill="x", pady=5)
        self.register_widget(self.did_entry, "entry")

        # Memory Read Parameters
        self.memory_frame = ctk.CTkFrame(self.uds_params_frame, fg_color="transparent")
        
        memory_params_frame = ctk.CTkFrame(self.memory_frame, fg_color="transparent")
        memory_params_frame.pack(fill="x", pady=5)
        
        start_addr_label = ctk.CTkLabel(memory_params_frame, text="Start Address:")
        start_addr_label.grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.register_widget(start_addr_label, "label")
        
        self.start_addr = ctk.CTkEntry(memory_params_frame, placeholder_text="0x0200", width=100)
        self.start_addr.grid(row=0, column=1, padx=5, sticky="w")
        self.register_widget(self.start_addr, "entry")
        
        length_label = ctk.CTkLabel(memory_params_frame, text="Length:")
        length_label.grid(row=0, column=2, padx=(10, 5), sticky="w")
        self.register_widget(length_label, "label")
        
        self.mem_length = ctk.CTkEntry(memory_params_frame, placeholder_text="0x10000", width=100)
        self.mem_length.grid(row=0, column=3, padx=5, sticky="w")
        self.register_widget(self.mem_length, "entry")

        # DID Range Parameters for dump_dids
        self.did_range_frame = ctk.CTkFrame(self.uds_params_frame, fg_color="transparent")
        
        did_range_params_frame = ctk.CTkFrame(self.did_range_frame, fg_color="transparent")
        did_range_params_frame.pack(fill="x", pady=5)
        
        min_did_label = ctk.CTkLabel(did_range_params_frame, text="Min DID:")
        min_did_label.grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.register_widget(min_did_label, "label")
        
        self.min_did = ctk.CTkEntry(did_range_params_frame, placeholder_text="0x6300", width=100)
        self.min_did.grid(row=0, column=1, padx=5, sticky="w")
        self.register_widget(self.min_did, "entry")
        
        max_did_label = ctk.CTkLabel(did_range_params_frame, text="Max DID:")
        max_did_label.grid(row=0, column=2, padx=(10, 5), sticky="w")
        self.register_widget(max_did_label, "label")
        
        self.max_did = ctk.CTkEntry(did_range_params_frame, placeholder_text="0x6FFF", width=100)
        self.max_did.grid(row=0, column=3, padx=5, sticky="w")
        self.register_widget(self.max_did, "entry")
        
        timeout_label = ctk.CTkLabel(self.did_range_frame, text="Timeout (seconds):")
        timeout_label.pack(anchor="w", pady=(5, 0))
        self.register_widget(timeout_label, "label")
        
        self.did_timeout = ctk.CTkEntry(self.did_range_frame, placeholder_text="0.1", width=100)
        self.did_timeout.pack(anchor="w", pady=5)
        self.register_widget(self.did_timeout, "entry")

        # UDS Options Frame
        self.uds_options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.uds_options_frame.pack(fill="x", pady=10, padx=20)

        # Blacklist options (for discovery)
        self.blacklist_label = ctk.CTkLabel(self.uds_options_frame, text="Blacklist IDs (space separated):")
        self.blacklist_label.pack(anchor="w", pady=(5, 0))
        self.register_widget(self.blacklist_label, "label")

        self.uds_blacklist = ctk.CTkEntry(self.uds_options_frame, placeholder_text="0x123 0x456")
        self.uds_blacklist.pack(fill="x", pady=5)
        self.register_widget(self.uds_blacklist, "entry")

        # Auto blacklist
        self.autoblacklist_frame = ctk.CTkFrame(self.uds_options_frame, fg_color="transparent")
        
        self.autoblacklist_label = ctk.CTkLabel(self.autoblacklist_frame, text="Auto Blacklist Count:")
        self.autoblacklist_label.pack(side="left")
        self.register_widget(self.autoblacklist_label, "label")

        self.uds_autoblacklist = ctk.CTkEntry(self.autoblacklist_frame, placeholder_text="10", width=80)
        self.uds_autoblacklist.pack(side="left", padx=10)
        self.register_widget(self.uds_autoblacklist, "entry")

        # Extra Args
        extra_label = ctk.CTkLabel(self, text="Extra Args:")
        extra_label.pack(pady=(10, 5))
        self.register_widget(extra_label, "label")

        self.uds_extra_args = ctk.CTkEntry(self, placeholder_text="Additional arguments")
        self.uds_extra_args.pack(fill="x", pady=5, padx=20)
        self.register_widget(self.uds_extra_args, "entry")

        # UDS Interface checkbox
        self.uds_use_interface = ctk.BooleanVar(value=True)
        self.uds_interface_check = ctk.CTkCheckBox(self, text="Use -i vcan0 interface",
                                                 variable=self.uds_use_interface)
        self.uds_interface_check.pack(pady=10, padx=20)
        self.register_widget(self.uds_interface_check, "checkbox")

        # UDS Execute Button
        self.uds_execute_btn = ctk.CTkButton(self, text="Execute UDS", command=self.run_uds, fg_color="#8e44ad")
        self.uds_execute_btn.pack(pady=20, fill="x", padx=20)
        self.register_widget(self.uds_execute_btn, "button_large")

        # Initialize UI based on default action
        self.on_uds_action_change("discovery")

    def on_uds_action_change(self, selection):
        """Update UDS UI based on selected action"""
        # Hide all optional elements first
        self.uds_rid_label.pack_forget()
        self.uds_rid.pack_forget()
        self.ecu_reset_frame.pack_forget()
        self.security_seed_frame.pack_forget()
        self.security_options_frame.pack_forget()
        self.did_frame.pack_forget()
        self.memory_frame.pack_forget()
        self.did_range_frame.pack_forget()
        self.blacklist_label.pack_forget()
        self.uds_blacklist.pack_forget()
        self.autoblacklist_label.pack_forget()
        self.autoblacklist_frame.pack_forget()
        self.uds_autoblacklist.pack_forget()

        # Show common elements
        self.uds_tid.pack(fill="x", pady=5)

        # Action-specific configurations
        if selection == "discovery":
            # Show blacklist options for discovery
            self.blacklist_label.pack(anchor="w", pady=(5, 0))
            self.uds_blacklist.pack(fill="x", pady=5)
            
            self.autoblacklist_label.pack(side="left")
            self.uds_autoblacklist.pack(side="left", padx=10)
            self.autoblacklist_frame.pack(fill="x", pady=5)

        elif selection in ["services", "subservices", "dump_dids", "read_mem", "read_did"]:
            # Show response ID for these commands
            self.uds_rid_label.pack(anchor="w", pady=(5, 0))
            self.uds_rid.pack(fill="x", pady=5)
            
            # Additional parameters for specific commands
            if selection == "dump_dids":
                self.did_range_frame.pack(fill="x", pady=10)
            elif selection == "read_mem":
                self.memory_frame.pack(fill="x", pady=10)
            elif selection == "read_did":
                self.did_frame.pack(fill="x", pady=10)

        elif selection == "ecu_reset":
            # Show response ID and reset subfunction
            self.uds_rid_label.pack(anchor="w", pady=(5, 0))
            self.uds_rid.pack(fill="x", pady=5)
            self.ecu_reset_frame.pack(fill="x", pady=10)

        elif selection == "testerpresent":
            # Only target ID needed for testerpresent
            pass

        elif selection == "security_seed":
            # Show response ID and security parameters
            self.uds_rid_label.pack(anchor="w", pady=(5, 0))
            self.uds_rid.pack(fill="x", pady=5)
            self.security_seed_frame.pack(fill="x", pady=10)

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
        if action in ["services", "subservices", "dump_dids", "read_mem", "read_did", "ecu_reset", "security_seed"]:
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

        elif action == "read_did":
            # Add DID parameter
            did = self.did_entry.get().strip()
            if did:
                cmd.append(did)
            else:
                messagebox.showerror("Error", "DID is required for read_did")
                return

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
        """Apply responsive scaling to all elements"""
        super()._apply_scaling(scale_factor)
        
        # Update padding based on scale
        padding = FontConfig.get_padding(scale_factor)
        
        # Update frame padding
        self.uds_params_frame.pack_configure(pady=padding, padx=padding)
        self.uds_options_frame.pack_configure(pady=padding, padx=padding)
        
        # Update grid cell padding for frames with grid layout
        # Use try-except to handle missing frames gracefully
        try:
            if hasattr(self, 'security_params_frame') and self.security_params_frame.winfo_exists():
                for child in self.security_params_frame.winfo_children():
                    info = child.grid_info()
                    if info:
                        child.grid_configure(padx=padding//2, pady=padding//4)
        except:
            pass  # Frame doesn't exist or isn't visible
        
        try:
            if hasattr(self, 'memory_params_frame') and self.memory_params_frame.winfo_exists():
                for child in self.memory_params_frame.winfo_children():
                    info = child.grid_info()
                    if info:
                        child.grid_configure(padx=padding//2, pady=padding//4)
        except:
            pass
        
        try:
            if hasattr(self, 'did_range_params_frame') and self.did_range_params_frame.winfo_exists():
                for child in self.did_range_params_frame.winfo_children():
                    info = child.grid_info()
                    if info:
                        child.grid_configure(padx=padding//2, pady=padding//4)
        except:
            pass


class AdvancedFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="Advanced", font=FontConfig.get_title_font(1.0))
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        # Buttons (Show help for all advanced modules)
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help(["doip", "xcp", "uds"]))
        self.help_btn.pack(side="right", padx=5)
        self.register_widget(self.help_btn, "button_small")

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("Advanced"))
        self.report_btn.pack(side="right", padx=5)
        self.register_widget(self.report_btn, "button_small")

        # NEW: View Failures button
        self.view_failures_btn = ctk.CTkButton(self.head_frame, text="📊 View Failures", 
                      fg_color="#e74c3c", command=lambda: app.show_failure_cases())
        self.view_failures_btn.pack(side="right", padx=5)
        self.register_widget(self.view_failures_btn, "button_small")

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
        self.register_widget(self.doip_interface_check, "checkbox")

        self.doip_btn = ctk.CTkButton(self.doip_frame, text="DoIP Discovery",
                                    command=self.run_doip)
        self.doip_btn.pack(fill="x", pady=5)
        self.register_widget(self.doip_btn, "button_large")

        # Tab 2: XCP
        self.xcp_tab = self.tabs.add("XCP")

        # XCP Section with interface checkbox
        self.xcp_frame = ctk.CTkFrame(self.xcp_tab, fg_color="transparent")
        self.xcp_frame.pack(fill="x", pady=10, padx=20)

        self.xcp_use_interface = ctk.BooleanVar(value=True)
        self.xcp_interface_check = ctk.CTkCheckBox(self.xcp_frame, text="Use -i vcan0 interface for XCP",
                                                 variable=self.xcp_use_interface)
        self.xcp_interface_check.pack(pady=5)
        self.register_widget(self.xcp_interface_check, "checkbox")

        self.xcp_id = ctk.CTkEntry(self.xcp_frame, placeholder_text="XCP ID (e.g., 0x123)")
        self.xcp_id.pack(pady=5, fill="x")
        self.register_widget(self.xcp_id, "entry")

        self.xcp_btn = ctk.CTkButton(self.xcp_frame, text="XCP Info",
                                   command=self.run_xcp)
        self.xcp_btn.pack(pady=5, fill="x")
        self.register_widget(self.xcp_btn, "button_large")

        # Tab 3: UDS DID Reader
        self.did_tab = self.tabs.add("DID Reader")

        # UDS DID Reader Section
        self.did_frame = ctk.CTkFrame(self.did_tab, fg_color="transparent")
        self.did_frame.pack(fill="both", expand=True, pady=10, padx=20)

        # DID Selection
        did_select_label = ctk.CTkLabel(self.did_frame, text="Select DID to Read:")
        did_select_label.pack(anchor="w", pady=(0, 5))
        self.register_widget(did_select_label, "label")

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
        self.register_widget(self.did_select, "dropdown")

        # Custom DID entry (initially hidden)
        self.custom_did_frame = ctk.CTkFrame(self.did_frame, fg_color="transparent")

        custom_label = ctk.CTkLabel(self.custom_did_frame, text="Custom DID (Hex):")
        custom_label.pack(anchor="w", pady=(0, 5))
        self.register_widget(custom_label, "label")

        self.custom_did_entry = ctk.CTkEntry(self.custom_did_frame, placeholder_text="e.g., F190 (without 0x)")
        self.custom_did_entry.pack(pady=5, fill="x")
        self.register_widget(self.custom_did_entry, "entry")

        # Range scanning options (initially hidden)
        self.range_frame = ctk.CTkFrame(self.did_frame, fg_color="transparent")

        start_label = ctk.CTkLabel(self.range_frame, text="Start DID (Hex):")
        start_label.pack(anchor="w", pady=(0, 5))
        self.register_widget(start_label, "label")

        self.start_did_entry = ctk.CTkEntry(self.range_frame, placeholder_text="F180")
        self.start_did_entry.pack(pady=5, fill="x")
        self.register_widget(self.start_did_entry, "entry")

        end_label = ctk.CTkLabel(self.range_frame, text="End DID (Hex):")
        end_label.pack(anchor="w", pady=(10, 5))
        self.register_widget(end_label, "label")

        self.end_did_entry = ctk.CTkEntry(self.range_frame, placeholder_text="F1FF")
        self.end_did_entry.pack(pady=5, fill="x")
        self.register_widget(self.end_did_entry, "entry")

        # Target ID for UDS request
        target_label = ctk.CTkLabel(self.did_frame, text="Target ECU ID (Hex):")
        target_label.pack(anchor="w", pady=(10, 5))
        self.register_widget(target_label, "label")

        self.uds_target_id = ctk.CTkEntry(self.did_frame, placeholder_text="0x7E0 (default)")
        self.uds_target_id.insert(0, "0x7E0")
        self.uds_target_id.pack(pady=5, fill="x")
        self.register_widget(self.uds_target_id, "entry")

        # Response ID
        response_label = ctk.CTkLabel(self.did_frame, text="Response ID:")
        response_label.pack(anchor="w", pady=(10, 5))
        self.register_widget(response_label, "label")

        self.uds_response_id = ctk.CTkEntry(self.did_frame, placeholder_text="0x7E8 (default)")
        self.uds_response_id.insert(0, "0x7E8")
        self.uds_response_id.pack(pady=5, fill="x")
        self.register_widget(self.uds_response_id, "entry")

        # Timeout option
        timeout_label = ctk.CTkLabel(self.did_frame, text="Timeout (seconds):")
        timeout_label.pack(anchor="w", pady=(10, 5))
        self.register_widget(timeout_label, "label")

        self.timeout_entry = ctk.CTkEntry(self.did_frame, placeholder_text="0.2 (default)")
        self.timeout_entry.insert(0, "0.2")
        self.timeout_entry.pack(pady=5, fill="x")
        self.register_widget(self.timeout_entry, "entry")

        # Interface checkbox for DID reading
        self.did_use_interface = ctk.BooleanVar(value=True)
        self.did_interface_check = ctk.CTkCheckBox(self.did_frame, text="Use -i vcan0 interface for UDS",
                                                 variable=self.did_use_interface)
        self.did_interface_check.pack(pady=10)
        self.register_widget(self.did_interface_check, "checkbox")

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
        self.register_widget(self.did_read_btn, "button_large")

        # NEW: Show Response button
        self.show_response_btn = ctk.CTkButton(self.button_frame, text="📥 Show Response",
                                             command=self.show_did_response, fg_color="#27ae60")
        self.show_response_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))
        self.register_widget(self.show_response_btn, "button_large")

        # NEW: Response display textbox
        self.response_text = ctk.CTkTextbox(self.did_frame, height=200, font=FontConfig.get_mono_font(1.0))
        self.response_text.pack(fill="both", expand=True, pady=(10, 0))
        self.register_widget(self.response_text, "textbox")

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

        input_label = ctk.CTkLabel(input_frame, text="Paste UDS Response (from candump):")
        input_label.pack(anchor="w")
        self.register_widget(input_label, "label")

        # Example formats
        examples_label = ctk.CTkLabel(input_frame,
                                    text="Example format:\nvcan0  7E8   [8]  10 14 62 F1 90 46 55 43",
                                    text_color="#95a5a6",
                                    font=FontConfig.get_label_font(1.0))
        examples_label.pack(anchor="w", pady=(0, 5))
        self.register_widget(examples_label, "label")

        self.uds_response_entry = ctk.CTkTextbox(input_frame, height=120, font=FontConfig.get_mono_font(1.0))
        self.uds_response_entry.pack(fill="x", pady=5)
        self.register_widget(self.uds_response_entry, "textbox")

        # Example buttons
        example_btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        example_btn_frame.pack(fill="x", pady=5)

        self.load_vin_example_btn = ctk.CTkButton(example_btn_frame, text="VIN Example",
                                                command=lambda: self.load_uds_example("vin"),
                                                fg_color="#3498db", width=120)
        self.load_vin_example_btn.pack(side="left", padx=(0, 5))
        self.register_widget(self.load_vin_example_btn, "button_small")

        self.load_boot_example_btn = ctk.CTkButton(example_btn_frame, text="Boot ID Example",
                                                command=lambda: self.load_uds_example("boot"),
                                                fg_color="#3498db", width=120)
        self.load_boot_example_btn.pack(side="left", padx=5)
        self.register_widget(self.load_boot_example_btn, "button_small")

        self.clear_btn = ctk.CTkButton(example_btn_frame, text="Clear",
                                     command=self.clear_uds_input,
                                     fg_color="#7f8c8d", width=80)
        self.clear_btn.pack(side="right")
        self.register_widget(self.clear_btn, "button_small")

        # Analyze button
        self.analyze_btn = ctk.CTkButton(self.analyzer_frame, text="🔍 Analyze Response",
                                       command=self.analyze_uds_response,
                                       fg_color="#27ae60", height=40)
        self.analyze_btn.pack(pady=10)
        self.register_widget(self.analyze_btn, "button_large")

        # Section 2: Results display
        results_frame = ctk.CTkFrame(self.analyzer_frame, fg_color="transparent")
        results_frame.pack(fill="both", expand=True, pady=(10, 0))

        results_label = ctk.CTkLabel(results_frame, text="Analysis Results:")
        results_label.pack(anchor="w")
        self.register_widget(results_label, "label")

        self.results_text = ctk.CTkTextbox(results_frame, font=FontConfig.get_mono_font(1.0))
        self.results_text.pack(fill="both", expand=True, pady=5)
        self.register_widget(self.results_text, "textbox")

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
        super()._apply_scaling(scale_factor)
        
        # Scale tabview fonts
        if hasattr(self.tabs, '_segmented_button'):
            self.tabs._segmented_button.configure(font=FontConfig.get_tab_font(scale_factor))


class SendFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="Send & Replay", font=FontConfig.get_title_font(1.0))
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("send"))
        self.help_btn.pack(side="right", padx=5)
        self.register_widget(self.help_btn, "button_small")

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("SendReplay"))
        self.report_btn.pack(side="right", padx=5)
        self.register_widget(self.report_btn, "button_small")

        # NEW: View Failures button
        self.view_failures_btn = ctk.CTkButton(self.head_frame, text="📊 View Failures", 
                      fg_color="#e74c3c", command=lambda: app.show_failure_cases())
        self.view_failures_btn.pack(side="right", padx=5)
        self.register_widget(self.view_failures_btn, "button_small")

        # Main container
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, pady=10)

        # Send Type Selection
        send_type_label = ctk.CTkLabel(self.main_container, text="Send Type:")
        send_type_label.pack(pady=(10, 5))
        self.register_widget(send_type_label, "label")

        self.send_type = ctk.CTkOptionMenu(self.main_container,
                                         values=["message", "file"],
                                         command=self.on_send_type_change,
                                         fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.send_type.pack(pady=5, fill="x", padx=20)
        self.send_type.set("message")
        self.register_widget(self.send_type, "dropdown")

        # Message Frame
        self.message_frame = ctk.CTkFrame(self.main_container)
        self.message_frame.pack(fill="x", pady=10, padx=20)

        # DBC Message Selection (for message type)
        msg_select_label = ctk.CTkLabel(self.message_frame, text="DBC Message (Optional):")
        msg_select_label.pack(pady=(10, 5))
        self.register_widget(msg_select_label, "label")

        self.msg_select = ctk.CTkOptionMenu(self.message_frame,
                                          values=["No DBC Loaded"],
                                          command=self.on_msg_select,
                                          fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.msg_select.pack(pady=5, fill="x")
        self.register_widget(self.msg_select, "dropdown")

        # Manual ID and Data Entry
        manual_label = ctk.CTkLabel(self.message_frame, text="Manual CAN Frame (ID#DATA):")
        manual_label.pack(pady=(10, 5))
        self.register_widget(manual_label, "label")

        self.manual_frame = ctk.CTkEntry(self.message_frame,
                                       placeholder_text="e.g., 0x7a0#c0.ff.ee.00.11.22.33.44 or 123#de.ad.be.ef")
        self.manual_frame.pack(pady=5, fill="x")
        self.register_widget(self.manual_frame, "entry")

        # Additional Options for message
        self.message_options_frame = ctk.CTkFrame(self.message_frame, fg_color="transparent")
        self.message_options_frame.pack(fill="x", pady=5)

        # Delay option
        delay_label = ctk.CTkLabel(self.message_options_frame, text="Delay (seconds):")
        delay_label.grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.register_widget(delay_label, "label")

        self.delay_entry = ctk.CTkEntry(self.message_options_frame, placeholder_text="0.5", width=80)
        self.delay_entry.grid(row=0, column=1, padx=(0, 20), sticky="w")
        self.register_widget(self.delay_entry, "entry")

        # Periodic option
        self.periodic_var = ctk.BooleanVar()
        self.periodic_check = ctk.CTkCheckBox(self.message_options_frame, text="Periodic send",
                                            variable=self.periodic_var)
        self.periodic_check.grid(row=0, column=2, padx=20, sticky="w")
        self.register_widget(self.periodic_check, "checkbox")

        self.message_options_frame.grid_columnconfigure(2, weight=1)

        # File Frame (initially hidden)
        self.file_frame = ctk.CTkFrame(self.main_container)

        file_label = ctk.CTkLabel(self.file_frame, text="CAN Dump File:")
        file_label.pack(pady=(10, 5))
        self.register_widget(file_label, "label")

        self.file_selection_frame = ctk.CTkFrame(self.file_frame, fg_color="transparent")
        self.file_selection_frame.pack(fill="x", pady=5)

        self.file_path_entry = ctk.CTkEntry(self.file_selection_frame, placeholder_text="Select CAN dump file...")
        self.file_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.register_widget(self.file_path_entry, "entry")

        self.browse_file_btn = ctk.CTkButton(self.file_selection_frame, text="Browse",
                                           command=self.browse_file, width=80)
        self.browse_file_btn.pack(side="right")
        self.register_widget(self.browse_file_btn, "button_small")

        # File options
        file_delay_label = ctk.CTkLabel(self.file_frame, text="File Send Delay (seconds):")
        file_delay_label.pack(pady=(10, 5))
        self.register_widget(file_delay_label, "label")

        self.file_delay_entry = ctk.CTkEntry(self.file_frame, placeholder_text="0.2")
        self.file_delay_entry.pack(pady=5, fill="x")
        self.register_widget(self.file_delay_entry, "entry")

        # Interface checkbox (common for both)
        self.interface_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.interface_frame.pack(fill="x", pady=10, padx=20)

        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(self.interface_frame, text="Use -i vcan0 interface",
                                             variable=self.use_interface)
        self.interface_check.pack()
        self.register_widget(self.interface_check, "checkbox")

        # Send Button
        self.send_btn = ctk.CTkButton(self.main_container, text="Send",
                                    command=self.run_send, fg_color="#27ae60")
        self.send_btn.pack(pady=20, fill="x", padx=20)
        self.register_widget(self.send_btn, "button_large")

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
        super()._apply_scaling(scale_factor)

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")


class MonitorFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.is_monitoring = False

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x", pady=10)

        self.title_label = ctk.CTkLabel(self.head_frame, text="Traffic Monitor", font=FontConfig.get_title_font(1.0))
        self.title_label.pack(side="left")
        self.register_widget(self.title_label, "title")

        self.save_btn = ctk.CTkButton(self.head_frame, text="📥 Save CSV", command=self.save_monitor)
        self.save_btn.pack(side="right")
        self.register_widget(self.save_btn, "button_small")

        self.ctl_frame = ctk.CTkFrame(self)
        self.ctl_frame.pack(fill="x", pady=5)

        self.sim_btn = ctk.CTkButton(self.ctl_frame, text="▶ Simulate", command=self.toggle_sim, fg_color="#27ae60")
        self.sim_btn.pack(side="left", padx=5)
        self.register_widget(self.sim_btn, "button")

        self.clear_btn = ctk.CTkButton(self.ctl_frame, text="🗑 Clear", command=self.clear, fg_color="gray30")
        self.clear_btn.pack(side="right")
        self.register_widget(self.clear_btn, "button_small")

        self.cols = ["Time", "ID", "Name", "Signals", "Raw"]
        self.header = ctk.CTkFrame(self, fg_color="#111")
        self.header.pack(fill="x")
        for i, c in enumerate(self.cols):
            lbl = ctk.CTkLabel(self.header, text=c, font=FontConfig.get_label_font(1.0, bold=True))
            lbl.grid(row=0, column=i, sticky="ew", padx=2)
            self.register_widget(lbl, "label")
            self.header.grid_columnconfigure(i, weight=1)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a")
        self.scroll.pack(fill="both", expand=True)

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
            lbl = ctk.CTkLabel(row, text=v, font=FontConfig.get_mono_font(1.0), anchor="w")
            lbl.grid(row=0, column=i, sticky="ew", padx=2)
            self.register_widget(lbl, "label")
            row.grid_columnconfigure(i, weight=1)

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        super()._apply_scaling(scale_factor)
        
        # Update header height
        header_height = FontConfig.get_height("button_small", scale_factor)
        self.header.configure(height=header_height)