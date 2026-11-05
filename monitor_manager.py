"""
Monitor Manager for Hyprland.
Handles detection of monitors, parsing available modes and refresh rates,
identifying the 4 display modes, and applying settings live via Lua IPC and persisting to disk.
"""

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("hyprswitch.monitor_manager")


@dataclass
class DisplayMode:
    width: int
    height: int
    refresh_rate: float
    mode_str: str

    @property
    def pixels(self) -> int:
        return self.width * self.height


@dataclass
class MonitorInfo:
    id: int
    name: str
    description: str
    make: str
    model: str
    width: int
    height: int
    refresh_rate: float
    x: int
    y: int
    scale: float
    disabled: bool
    mirror_of: str
    available_modes: List[DisplayMode]
    is_internal: bool = False

    @property
    def best_mode(self) -> Optional[DisplayMode]:
        """Returns the highest resolution and highest refresh rate mode."""
        if not self.available_modes:
            if self.width > 0 and self.height > 0:
                return DisplayMode(
                    width=self.width,
                    height=self.height,
                    refresh_rate=self.refresh_rate,
                    mode_str=f"{self.width}x{self.height}@{self.refresh_rate:.2f}Hz"
                )
            return None
        # Sort by resolution (descending), then refresh rate (descending)
        return sorted(
            self.available_modes,
            key=lambda m: (m.pixels, m.refresh_rate),
            reverse=True
        )[0]


class DisplayPreset:
    PC_ONLY = 0       # Internal only
    DUPLICATE = 1     # Mirror internal onto external
    EXTEND = 2        # Side-by-side
    SECOND_ONLY = 3   # External only

    NAMES = {
        PC_ONLY: "PC Screen Only",
        DUPLICATE: "Duplicate",
        EXTEND: "Extend",
        SECOND_ONLY: "Second Screen Only"
    }

    DESCRIPTIONS = {
        PC_ONLY: "Use built-in display only and disable external monitor",
        DUPLICATE: "Mirror the built-in display onto external monitor",
        EXTEND: "Extend desktop across both displays side-by-side",
        SECOND_ONLY: "Use external monitor only and disable built-in display"
    }

    ICONS = {
        PC_ONLY: "video-single-display-symbolic",
        DUPLICATE: "video-joined-displays-symbolic",
        EXTEND: "view-paged-symbolic",
        SECOND_ONLY: "preferences-desktop-display-symbolic"
    }


class MonitorManager:
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or (Path.home() / ".config" / "hypr")
        self.monitors_lua = self.config_dir / "monitors.lua"

    @staticmethod
    def parse_mode_string(raw: str) -> Optional[DisplayMode]:
        """Parse mode strings like '1920x1080@144.00Hz' or '2560x1440@59.95'"""
        clean = raw.strip()
        match = re.match(r"^(\d+)x(\d+)(?:@([\d\.]+))?(?:Hz)?$", clean, re.IGNORECASE)
        if not match:
            return None
        w = int(match.group(1))
        h = int(match.group(2))
        rr = float(match.group(3)) if match.group(3) else 60.0
        return DisplayMode(width=w, height=h, refresh_rate=rr, mode_str=clean)

    @staticmethod
    def is_internal_name(name: str) -> bool:
        """Determines if output name corresponds to a built-in display."""
        upper = name.upper()
        return (
            upper.startswith("EDP")
            or upper.startswith("LVDS")
            or upper.startswith("DSI")
        )

    def get_monitors(self) -> List[MonitorInfo]:
        """Query hyprctl monitors all -j and parse monitor data."""
        try:
            res = subprocess.run(
                ["hyprctl", "monitors", "all", "-j"],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(res.stdout)
        except Exception as e:
            logger.error("Failed to query hyprctl monitors all: %s", e)
            return []

        monitors = []
        for item in data:
            modes = []
            for m in item.get("availableModes", []):
                parsed = self.parse_mode_string(m)
                if parsed:
                    modes.append(parsed)

            name = item.get("name", "")
            is_internal = self.is_internal_name(name)

            # Mirror of can be "none" or monitor name
            mirror_of = item.get("mirrorOf", "")
            if mirror_of.lower() == "none":
                mirror_of = ""

            mon = MonitorInfo(
                id=item.get("id", 0),
                name=name,
                description=item.get("description", ""),
                make=item.get("make", ""),
                model=item.get("model", ""),
                width=item.get("width", 0),
                height=item.get("height", 0),
                refresh_rate=float(item.get("refreshRate", 0.0)),
                x=item.get("x", 0),
                y=item.get("y", 0),
                scale=float(item.get("scale", 1.0)),
                disabled=bool(item.get("disabled", False)),
                mirror_of=mirror_of,
                available_modes=modes,
                is_internal=is_internal
            )
            monitors.append(mon)

        # Fallback: if no monitor matched internal name, designate the first monitor as internal
        if monitors and not any(m.is_internal for m in monitors):
            monitors[0].is_internal = True

        return monitors

    def get_displays(self) -> Tuple[Optional[MonitorInfo], Optional[MonitorInfo]]:
        """Returns (internal_monitor, primary_external_monitor)."""
        monitors = self.get_monitors()
        internal = next((m for m in monitors if m.is_internal), None)
        external = next((m for m in monitors if not m.is_internal), None)
        return internal, external

    def detect_current_mode(self) -> int:
        """Detect which of the 4 modes is currently active in Hyprland or saved in monitors.lua."""
        # 1. Check saved configuration file first for accurate state tracking
        if self.monitors_lua.exists():
            try:
                for line in self.monitors_lua.read_text().splitlines():
                    if line.startswith("-- Mode:"):
                        mode_name = line.split(":", 1)[1].strip()
                        for p, name in DisplayPreset.NAMES.items():
                            if name.lower() == mode_name.lower():
                                return p
            except Exception as e:
                logger.debug("Failed to read mode from %s: %s", self.monitors_lua, e)

        # 2. Live detection fallback
        internal, external = self.get_displays()
        if not internal or not external:
            return DisplayPreset.PC_ONLY

        if external.disabled and not internal.disabled:
            return DisplayPreset.PC_ONLY
        elif internal.disabled and not external.disabled:
            return DisplayPreset.SECOND_ONLY
        elif external.mirror_of == internal.name or (internal.mirror_of == external.name):
            return DisplayPreset.DUPLICATE
        else:
            return DisplayPreset.EXTEND

    def generate_lua_config(self, preset: int) -> Tuple[str, List[str]]:
        """
        Generates:
        1. A full Lua configuration string to save in ~/.config/hypr/monitors.lua
        2. A list of Lua commands to execute dynamically via hyprctl eval
        """
        internal, external = self.get_displays()
        if not internal:
            return "-- No display found", []

        int_name = internal.name
        int_mode_str = "preferred"

        eval_cmds: List[str] = []
        lua_lines: List[str] = [
            "-- Generated automatically by hyprswitch",
            f"-- Mode: {DisplayPreset.NAMES.get(preset, 'Custom')}",
            ""
        ]

        # Use detected external monitor name, or fallback "" (matches any external output in Hyprland)
        ext_name = external.name if external else ""
        if external and external.best_mode:
            ext_best = external.best_mode
            ext_mode_str = f"{ext_best.width}x{ext_best.height}@{ext_best.refresh_rate:.2f}"
        else:
            ext_mode_str = "preferred"

        if preset == DisplayPreset.PC_ONLY:
            cmd_int = f'hl.monitor({{ output = "{int_name}", mode = "{int_mode_str}", position = "0x0", scale = 1 }})'
            cmd_ext = f'hl.monitor({{ output = "{ext_name}", disabled = true }})'
            eval_cmds.extend([cmd_int, cmd_ext])
            lua_lines.extend([cmd_int, cmd_ext])

        elif preset == DisplayPreset.DUPLICATE:
            cmd_int = f'hl.monitor({{ output = "{int_name}", mode = "{int_mode_str}", position = "0x0", scale = 1 }})'
            cmd_ext = f'hl.monitor({{ output = "{ext_name}", mode = "preferred", position = "0x0", scale = 1, mirror = "{int_name}" }})'
            eval_cmds.extend([cmd_int, cmd_ext])
            lua_lines.extend([cmd_int, cmd_ext])

        elif preset == DisplayPreset.EXTEND:
            cmd_int = f'hl.monitor({{ output = "{int_name}", mode = "{int_mode_str}", position = "0x0", scale = 1 }})'
            cmd_ext = f'hl.monitor({{ output = "{ext_name}", mode = "{ext_mode_str}", position = "auto-right", scale = 1 }})'
            eval_cmds.extend([cmd_int, cmd_ext])
            lua_lines.extend([cmd_int, cmd_ext])

        elif preset == DisplayPreset.SECOND_ONLY:
            cmd_ext = f'hl.monitor({{ output = "{ext_name}", mode = "{ext_mode_str}", position = "0x0", scale = 1 }})'
            eval_cmds.append(cmd_ext)
            lua_lines.append(cmd_ext)

            # Only disable internal monitor live if an external display is physically present
            if external:
                cmd_int = f'hl.monitor({{ output = "{int_name}", disabled = true }})'
                eval_cmds.append(cmd_int)
                lua_lines.append(cmd_int)
            else:
                # If no external monitor is plugged in yet, keep internal active so screen does not go black
                cmd_int = f'hl.monitor({{ output = "{int_name}", mode = "{int_mode_str}", position = "0x0", scale = 1 }})'
                eval_cmds.append(cmd_int)

        return "\n".join(lua_lines) + "\n", eval_cmds

    def apply_mode(self, preset: int) -> bool:
        """
        Executes the Lua commands live with hyprctl eval atomically and writes to monitors.lua.
        """
        lua_content, eval_cmds = self.generate_lua_config(preset)
        if not eval_cmds:
            return True

        logger.info("Applying mode %s immediately", DisplayPreset.NAMES.get(preset))
        combined_cmd = " ".join(eval_cmds)

        success = True
        try:
            res = subprocess.run(
                ["hyprctl", "eval", combined_cmd],
                capture_output=True,
                text=True,
                check=False
            )
            if res.returncode != 0:
                logger.warning("hyprctl eval error: %s (stderr: %s)", res.stdout, res.stderr)
                success = False
        except Exception as e:
            logger.error("Failed to execute hyprctl eval: %s", e)
            success = False

        # Persist to ~/.config/hypr/monitors.lua
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.monitors_lua.write_text(lua_content)
            logger.info("Saved configuration to %s", self.monitors_lua)
        except Exception as e:
            logger.error("Failed to write to %s: %s", self.monitors_lua, e)

        return success
