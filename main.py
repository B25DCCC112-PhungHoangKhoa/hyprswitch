#!/usr/bin/env python3
"""
hyprswitch - Hyprland Display Projection & Monitor Switcher
"""

import os
import sys
from pathlib import Path

# Automatically ensure LD_PRELOAD is set for libgtk4-layer-shell if available,
# resolving the GTK4 Wayland linking order requirement cleanly.
LAYER_SHELL_LIB = "/usr/lib/libgtk4-layer-shell.so"
if (
    os.path.exists(LAYER_SHELL_LIB)
    and LAYER_SHELL_LIB not in os.environ.get("LD_PRELOAD", "")
):
    current_preload = os.environ.get("LD_PRELOAD", "")
    new_preload = f"{LAYER_SHELL_LIB}:{current_preload}".strip(":")
    os.environ["LD_PRELOAD"] = new_preload
    try:
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        # Fall back if re-exec fails
        pass

# Ensure local imports work regardless of launch directory
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import logging
from app import HyprswitchApp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


def print_help():
    print("""hyprswitch - Display projection switcher for Hyprland

Usage:
  hyprswitch                     Open switcher OSD or cycle to next mode (Super+P)
  hyprswitch --status            Print connected monitor detection & current mode
  hyprswitch --apply <mode>      Apply mode directly without UI (pc, duplicate, extend, second)
  hyprswitch --help              Show this help message

Display Modes:
  pc        PC Screen Only (built-in eDP only, disable external)
  duplicate Duplicate / Mirror built-in screen onto external monitor
  extend    Extend desktop across both displays side-by-side
  second    Second Screen Only (external only, disable built-in)
""")


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print_help()
        sys.exit(0)

    if "--status" in sys.argv:
        from monitor_manager import MonitorManager, DisplayPreset
        mm = MonitorManager()
        internal, external = mm.get_displays()
        current_mode = mm.detect_current_mode()
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
        sys.exit(0)

    for i, arg in enumerate(sys.argv):
        if arg in ("--apply", "-a") and i + 1 < len(sys.argv):
            from monitor_manager import MonitorManager, DisplayPreset
            mode_str = sys.argv[i + 1].lower()
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
                MonitorManager().apply_mode(preset)
                sys.exit(0)
            else:
                print(f"Unknown mode '{mode_str}'. Valid: pc, duplicate, extend, second")
                sys.exit(1)

    app = HyprswitchApp()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
