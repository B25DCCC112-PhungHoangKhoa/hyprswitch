"""
Application controller for hyprswitch.
Manages Gtk.Application lifecycle, single-instance IPC cycling,
keyboard controls, and 1-second auto-apply timer.
"""

import logging
import sys
import time
from typing import Optional
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gtk, Gdk, Gio, GLib

from monitor_manager import DisplayPreset, MonitorManager
from ui import SwitcherWindow

logger = logging.getLogger("hyprswitch.app")

AUTO_DISMISS_MS = 8000


class HyprswitchApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="org.hyprland.hyprswitch",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        )
        self.monitor_manager = MonitorManager()
        self.window: Optional[SwitcherWindow] = None
        self.selected_mode: int = DisplayPreset.PC_ONLY
        self.last_activity_time: float = 0.0
        self.timer_id: Optional[int] = None
        self.is_held: bool = False

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def do_command_line(self, cmdline: Gio.ApplicationCommandLine) -> int:
        args = cmdline.get_arguments()

        # Handle CLI commands like --status or --apply
        if "--status" in args:
            self._print_status()
            return 0

        for i, arg in enumerate(args):
            if arg in ("--apply", "-a") and i + 1 < len(args):
                mode_str = args[i + 1].lower()
                preset_map = {
                    "pc": DisplayPreset.PC_ONLY,
                    "internal": DisplayPreset.PC_ONLY,
                    "duplicate": DisplayPreset.DUPLICATE,
                    "mirror": DisplayPreset.DUPLICATE,
                    "extend": DisplayPreset.EXTEND,
                    "second": DisplayPreset.SECOND_ONLY,
                    "external": DisplayPreset.SECOND_ONLY,
                }
                preset = preset_map.get(mode_str)
                if preset is not None:
                    print(f"Applying mode: {DisplayPreset.NAMES[preset]}")
                    self.monitor_manager.apply_mode(preset)
                    return 0
                else:
                    print(f"Unknown mode '{mode_str}'. Valid: pc, duplicate, extend, second")
                    return 1

        # Interactive switcher path (Super + P)
        if self.window is None:
            # First instance launched
            if not self.is_held:
                self.hold()
                self.is_held = True

            curr_mode = self.monitor_manager.detect_current_mode()
            # Open with current mode lit up; cycling moves to next
            self.selected_mode = curr_mode
            self._open_window(initial_mode=self.selected_mode)
        else:
            # Multi-instance cycle: secondary call while window is open
            self.cycle_forward()

        return 0

    def _print_status(self):
        internal, external = self.monitor_manager.get_displays()
        current_mode = self.monitor_manager.detect_current_mode()
        print("=== Hyprland Monitors ===")
        if internal:
            best_int = internal.best_mode
            int_res = f"{best_int.width}x{best_int.height}@{best_int.refresh_rate:.2f}Hz" if best_int else "Unknown"
            print(f"Internal Display: {internal.name} (Active: {not internal.disabled}, Best: {int_res})")
        else:
            print("Internal Display: None")

        if external:
            best_ext = external.best_mode
            ext_res = f"{best_ext.width}x{best_ext.height}@{best_ext.refresh_rate:.2f}Hz" if best_ext else "Unknown"
            print(f"External Display: {external.name} (Active: {not external.disabled}, Best: {ext_res})")
            if external.available_modes:
                modes_str = ", ".join(m.mode_str for m in external.available_modes[:5])
                print(f"Available External Modes: {modes_str}...")
        else:
            print("External Display: None detected")

        print(f"Current Mode: {DisplayPreset.NAMES.get(current_mode, 'Unknown')}")

    def _open_window(self, initial_mode: int):
        internal, external = self.monitor_manager.get_displays()

        self.window = SwitcherWindow(
            app=self,
            internal_mon=internal,
            external_mon=external,
            current_mode=initial_mode,
            on_mode_selected=self._on_card_clicked,
            on_cancel=self.close_and_quit
        )

        # Setup key events with CAPTURE phase so window catches keys before any widget
        key_ctrl = Gtk.EventControllerKey.new()
        key_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.window.add_controller(key_ctrl)

        self.window.present()

        # Auto-dismiss timer (closes after inactivity like Windows flyout)
        self._reset_dismiss_timer()

    def _reset_dismiss_timer(self):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
        self.timer_id = GLib.timeout_add(AUTO_DISMISS_MS, self._on_auto_dismiss)

    def _on_auto_dismiss(self) -> bool:
        self.close_and_quit()
        return GLib.SOURCE_REMOVE

    def _on_key_pressed(self, controller, keyval, keycode, state) -> bool:
        # Enter / Space to select and commit!
        iso_enter = getattr(Gdk, "KEY_ISO_Enter", 65076)
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, iso_enter, Gdk.KEY_space):
            self.apply_and_quit()
            return True
        elif keyval == Gdk.KEY_Escape:
            self.close_and_quit()
            return True
        elif keyval in (Gdk.KEY_Right, Gdk.KEY_Down, Gdk.KEY_Tab, Gdk.KEY_p, Gdk.KEY_P):
            self.cycle_forward()
            return True
        elif keyval in (Gdk.KEY_Left, Gdk.KEY_Up, Gdk.KEY_ISO_Left_Tab):
            self.cycle_backward()
            return True
        return False

    def _on_card_clicked(self, preset: int):
        self.selected_mode = preset
        if self.window:
            self.window.set_highlighted_mode(self.selected_mode)
        # Mouse click commits immediately
        self.apply_and_quit()

    def cycle_forward(self):
        self.selected_mode = (self.selected_mode + 1) % 4
        if self.window:
            self.window.set_highlighted_mode(self.selected_mode)
        self._reset_dismiss_timer()

    def cycle_backward(self):
        self.selected_mode = (self.selected_mode - 1) % 4
        if self.window:
            self.window.set_highlighted_mode(self.selected_mode)
        self._reset_dismiss_timer()

    def apply_and_quit(self):
        logger.info("Committing selected mode: %s", DisplayPreset.NAMES.get(self.selected_mode))
        self.monitor_manager.apply_mode(self.selected_mode)
        self.close_and_quit()

    def close_and_quit(self):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None

        if self.window:
            self.window.destroy()
            self.window = None

        if self.is_held:
            self.release()
            self.is_held = False
        self.quit()
