# hyprswitch

A modern **Python + GTK4** on-screen display (OSD) projection switcher for Hyprland that replaces manual editing of `hyprland.lua`. Designed to be triggered with **`Super + P`** (matching the Windows projection flyout workflow), it provides fast multi-instance cycling across standard display modes with zero screen flickering during navigation, auto-detects external monitors' optimal resolutions and refresh rates, and features a frosted-glass **Caelestia shell aesthetic**.

---

## Features

- **Caelestia Shell Aesthetic & Material 3 Styling**:
  - Dynamically extracts Material 3 color tokens from `~/.local/state/caelestia/scheme.json` (with fallback to `~/.config/hypr/scheme/current.lua`).
  - Frosted translucent glass background with deep drop shadows and smooth 32px corner rounding.
  - Hyprland layer-shell blur (`layerrule = blur true, match:namespace hyprswitch` and `ignorealpha 0.2`) to blur wallpaper behind the switcher window.
  - Active/selected mode lights up with a vibrant neon primary glowing border (`#primary` / `#f5b6c3`) and tinted container fill.
  - Status display and footer controls styled in Caelestia pill chips (`border-radius: 9999px`).
- **Auto-Detection of External Resolutions & Refresh Rates**:
  - Automatically queries connected monitors and their supported modes from `hyprctl -j monitors all`.
  - Intelligently determines internal panel (`eDP-1`, `LVDS`, `DSI`) vs external monitors (`HDMI-A-1`, `DP-1`, etc.).
  - Selects the highest supported native resolution and peak refresh rate (e.g. `1920x1080@144Hz`, `2560x1440@165Hz`).
- **4 Display Projection Modes**:
  1. **PC Screen Only**: Built-in monitor active; external monitor disabled.
  2. **Duplicate**: Mirror built-in display onto external monitor at preferred aspect ratio.
  3. **Extend**: Dual-screen desktop spans across displays side-by-side at optimal resolutions and refresh rates.
  4. **Second Screen Only**: External monitor active; built-in display disabled (with auto-failsafe if no external screen is present).
- **Fast Single-Instance IPC Cycling & Enter-to-Select**:
  - Uses `Gtk.Application` IPC: pressing `Super + P` opens the OSD highlighting the current mode; repeated presses cycle forward instantly.
  - **Zero Screen Flicker**: No monitor reconfiguration is triggered while cycling through choices.
  - Press **`Enter`** (or **`Space`**, or click any card) to commit and apply immediately.
  - Press **`Escape`** to dismiss without making changes.
- **Hyprland Lua Integration & Wildcard Fallbacks**:
  - Applies settings live and atomically via `hyprctl eval "hl.monitor(...)"`.
  - Persists configuration cleanly to `~/.config/hypr/monitors.lua`.
  - Uses Hyprland's `output = ""` wildcard fallback rules so Duplicate, Extend, and Second Screen modes configure any external screen whether plugged in now or later.

---

## Installation & Setup

Run the installer:
```bash
./install
```
*(Alternatively: `./install.sh`)*

The installation script will:
1. Verify required dependencies (`python3`, `python-gobject`, `gtk4`, `gtk4-layer-shell`, `hyprctl`).
2. Symlink `main.py` into `~/.local/bin/hyprswitch`.
3. Add `pcall(require, "monitors")` to `~/.config/hypr/hyprland.lua`.
4. Add the `SUPER + P` keybind (`hl.bind("SUPER +  P", hl.dsp.exec_cmd("hyprswitch"))`) to `~/.config/hypr/hyprland/keybinds.lua`.
5. Add layer rules (blur, popin animation, ignorealpha) to `~/.config/hypr/hyprland/rules.conf`.
6. Reload the active Hyprland configuration automatically.

---

## Controls

| Key / Action | Description |
| --- | --- |
| `Super + P` | Open switcher OSD / Cycle forward to next mode |
| `Right` / `Down` / `Tab` | Cycle forward |
| `Left` / `Up` / `Shift + Tab` | Cycle backward |
| `Enter` / `Space` | Apply highlighted mode immediately and close |
| `Escape` | Cancel and dismiss without changes |
| Mouse Click | Click any card to apply immediately and close |

---

## CLI Usage

`hyprswitch` can also be queried or scripted directly from the terminal without opening the UI:

```bash
# Open switcher OSD / cycle mode (called by Super + P)
hyprswitch

# Check monitor auto-detection and current active mode
hyprswitch --status

# Apply a mode directly via CLI
hyprswitch --apply pc
hyprswitch --apply duplicate
hyprswitch --apply extend
hyprswitch --apply second
```

---

## Dependencies

- **Python 3** (`python >= 3.10`)
- **PyGObject** (`python-gobject`)
- **GTK4** (`gtk4`)
- **GTK4 Layer Shell** (`gtk4-layer-shell`)
- **Hyprland** (`hyprctl`)

On Arch Linux:
```bash
sudo pacman -S python-gobject gtk4 gtk4-layer-shell
```

---

## Running Tests

Run the unit test suite:
```bash
python3 -m unittest discover -s tests
```
