#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
TARGET_LINK="$BIN_DIR/hyprswitch"

echo "=== Installing hyprswitch ==="

mkdir -p "$BIN_DIR"
ln -sf "$SCRIPT_DIR/main.py" "$TARGET_LINK"
chmod +x "$SCRIPT_DIR/main.py"

echo "✓ Created symlink: $TARGET_LINK -> $SCRIPT_DIR/main.py"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "Notice: $BIN_DIR is not in your current PATH. Consider adding it to your ~/.bashrc or ~/.zshrc."
fi

# Setup monitors.lua in hyprland.lua if not present
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

# Setup keybind in ~/.config/hypr/hyprland/keybinds.lua if not present
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

# Setup layer rules in ~/.config/hypr/hyprland/rules.conf if present
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

echo ""
echo "hyprswitch installed successfully!"
echo "Run 'hyprswitch --status' to inspect your monitors."
echo "Press Super + P to cycle display modes."
