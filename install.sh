#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
TARGET_LINK="$BIN_DIR/hyprswitch"

echo "=== Installing hyprswitch ==="

# 1. Dependency checks
echo "Checking dependencies..."
MISSING_DEPS=()

if ! command -v python3 &>/dev/null; then
    MISSING_DEPS+=("python3")
fi

if ! command -v hyprctl &>/dev/null; then
    echo "Notice: 'hyprctl' command not found. Hyprland may not be running or not in PATH."
fi

if ! python3 -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk" &>/dev/null; then
    MISSING_DEPS+=("python-gobject / gtk4")
fi

if [ ! -f "/usr/lib/libgtk4-layer-shell.so" ] && [ ! -f "/usr/local/lib/libgtk4-layer-shell.so" ] && [ ! -f "/usr/lib64/libgtk4-layer-shell.so" ]; then
    echo "Warning: libgtk4-layer-shell.so was not found in standard library paths. Hyprswitch will fall back to a floating window if layer shell is unavailable."
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo "Error: Missing required dependencies: ${MISSING_DEPS[*]}"
    echo "Please install them via your distribution package manager (e.g. pacman -S python-gobject gtk4 gtk4-layer-shell)."
    exit 1
fi

echo "✓ All core dependencies found."

# 2. Symlink binary
mkdir -p "$BIN_DIR"
chmod +x "$SCRIPT_DIR/main.py"
ln -sf "$SCRIPT_DIR/main.py" "$TARGET_LINK"
echo "✓ Created symlink: $TARGET_LINK -> $SCRIPT_DIR/main.py"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "Notice: $BIN_DIR is not in your current PATH. Consider adding it to your ~/.bashrc or ~/.zshrc."
fi

# 3. Setup monitors.lua in hyprland.lua if not present
HYPR_LUA="$HOME/.config/hypr/hyprland.lua"
if [ -f "$HYPR_LUA" ]; then
    if ! grep -q 'monitors' "$HYPR_LUA"; then
        echo "Adding 'pcall(require, \"monitors\")' to $HYPR_LUA..."
        echo -e '\n-- Automatically load display mode managed by hyprswitch\npcall(require, "monitors")' >> "$HYPR_LUA"
        echo "✓ Updated $HYPR_LUA"
    else
        echo "✓ $HYPR_LUA already references monitors configuration."
    fi
fi

# 4. Setup keybind in ~/.config/hypr/hyprland/keybinds.lua if not present
KEYBINDS_LUA="$HOME/.config/hypr/hyprland/keybinds.lua"
if [ -f "$KEYBINDS_LUA" ]; then
    if ! grep -q 'hyprswitch' "$KEYBINDS_LUA"; then
        echo "Adding Super+P keybind to $KEYBINDS_LUA..."
        echo -e '\n-- Display switcher (hyprswitch)\nhl.bind("SUPER, P", hl.dsp.exec_cmd("hyprswitch"))' >> "$KEYBINDS_LUA"
        echo "✓ Added 'SUPER, P' bind to $KEYBINDS_LUA"
    else
        echo "✓ $KEYBINDS_LUA already contains hyprswitch bind."
    fi
fi

# 5. Setup layer rules in ~/.config/hypr/hyprland/rules.conf if present
RULES_CONF="$HOME/.config/hypr/hyprland/rules.conf"
if [ -f "$RULES_CONF" ]; then
    if ! grep -q 'match:namespace hyprswitch' "$RULES_CONF"; then
        echo "Adding hyprswitch layer rules to $RULES_CONF..."
        echo -e '\n# hyprswitch\nlayerrule = animation popin 85%, match:namespace hyprswitch\nlayerrule = blur true, match:namespace hyprswitch\nlayerrule = ignorealpha 0.2, match:namespace hyprswitch' >> "$RULES_CONF"
        echo "✓ Added hyprswitch layer rules to $RULES_CONF"
    else
        echo "✓ $RULES_CONF already contains hyprswitch layer rules."
    fi
fi

# 6. Reload Hyprland configuration if active
if command -v hyprctl &>/dev/null && [ -n "$HYPRLAND_INSTANCE_SIGNATURE" ]; then
    hyprctl reload config-only >/dev/null 2>&1 || true
    echo "✓ Reloaded Hyprland configuration."
fi

echo ""
echo "hyprswitch installed successfully!"
echo "Run 'hyprswitch --status' to inspect your monitors."
echo "Press Super + P to open the switcher and cycle display modes."
