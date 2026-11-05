# hyprswitch

A native **Python + GTK4** on-screen display (OSD) switcher for Hyprland that replaces manual editing of `hyprland.lua`. Designed to be triggered by `Super + P`, it provides fast multi-instance cycling across the 4 standard display modes with zero screen flickering during navigation, auto-detects external monitors' optimal resolutions and refresh rates, and automatically applies the chosen mode after a 1-second idle timeout.

## Features

- **Auto-Detection of External Resolutions & Refresh Rates**:
  - Automatically parses connected monitors and their supported modes from `hyprctl -j monitors all`.
  - Intelligently determines internal panel (`eDP-1`, `LVDS`, `DSI`) vs external monitors (`HDMI-A-1`, `DP-1`, etc.).
  - Selects the highest supported native resolution and peak refresh rate (e.g. `1920x1080@144Hz`, `2560x1440@165Hz`).
- **4 Display Projection Modes**:
  1. **PC Screen Only**: Internal monitor active; external monitor disabled.
  2. **Duplicate**: Mirror internal display onto the external screen.
  3. **Extend**: Desktop spans across displays side-by-side at optimal resolutions and refresh rates.
  4. **Second Screen Only**: External monitor active; internal display disabled.
- **Multi-Instance Cycling & Timeout Auto-Apply**:
  - Uses `Gtk.Application` IPC: pressing `Super + P` repeatedly cycles the highlighted mode immediately.
  - **Zero Screen Flicker**: No monitor reconfiguration is dispatched while cycling keys.
  - A subtle 1-second countdown commits the chosen mode only after you stop pressing keys.
- **Fast Keyboard & Mouse Controls**:
  - `Super + P`, `Right`, `Down`, `Tab`: Cycle forward.
  - `Left`, `Up`, `Shift + Tab`: Cycle backward.
  - `Enter` / `Space`: Commit immediately without waiting for timer.
  - `Escape`: Cancel and dismiss.
  - Mouse Click: Click any card to apply immediately.
- **Hyprland Lua Integration**:
  - Applies settings live with `hyprctl eval "hl.monitor(...)"`.
  - Persists configuration cleanly to `~/.config/hypr/monitors.lua`.

## Installation & Setup

Run the installation script:
```bash
./install.sh
```

This will:
1. Symlink `hyprswitch` into `~/.local/bin/hyprswitch`.
2. Add `pcall(require, "monitors")` to `~/.config/hypr/hyprland.lua`.
3. Bind `Super + P` to `hyprswitch` in `~/.config/hypr/hyprland/keybinds.lua`.

## CLI Usage

```bash
# Open switcher OSD / cycle mode (called by Super+P)
hyprswitch

# Check monitor auto-detection and current mode
hyprswitch --status

# Apply a mode directly via CLI without UI
hyprswitch --apply pc
hyprswitch --apply duplicate
hyprswitch --apply extend
hyprswitch --apply second
```

## Running Tests

```bash
python3 -m unittest discover -s tests
```
