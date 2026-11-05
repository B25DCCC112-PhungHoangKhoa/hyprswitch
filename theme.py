"""
Theme loader for Caelestia color scheme, matching Caelestia shell aesthetic.
Dynamically loads Material 3 tokens from ~/.local/state/caelestia/scheme.json
or ~/.config/hypr/scheme/current.lua.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict

logger = logging.getLogger("hyprswitch.theme")

STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "caelestia"
SCHEME_JSON = STATE_DIR / "scheme.json"
SCHEME_LUA = Path.home() / ".config/hypr/scheme/current.lua"

# Default Material You / Caelestia fallback colors
FALLBACK_COLORS: Dict[str, str] = {
    "background": "120e08",
    "surface": "120e08",
    "surfaceContainerLowest": "000000",
    "surfaceContainerLow": "18130b",
    "surfaceContainer": "211719",
    "surfaceContainerHigh": "281d1f",
    "surfaceContainerHighest": "2f2225",
    "surfaceBright": "332b1f",
    "onSurface": "f7e0e3",
    "onSurfaceVariant": "baa6a9",
    "outline": "837174",
    "outlineVariant": "534447",
    "primary": "f5b6c3",
    "onPrimary": "553b0f",
    "primaryContainer": "744550",
    "onPrimaryContainer": "ffdae0",
    "secondary": "dcc3a1",
    "onSecondary": "4e3d24",
    "secondaryContainer": "493920",
    "onSecondaryContainer": "d4bc9a",
    "error": "f97758",
    "onError": "450900",
    "errorContainer": "85230a",
    "onErrorContainer": "ff9b82",
}

CSS_TEMPLATE = """
window.switcher-window {
    background-color: transparent;
    font-family: "Rubik", "GoogleSansFlex", "Google Sans", "Noto Sans", sans-serif;
}

.main-container {
    background-color: alpha(#%(surfaceContainer)s, 0.72);
    border: 1px solid alpha(#%(outlineVariant)s, 0.28);
    border-radius: 32px;
    box-shadow: 0 24px 64px rgba(0, 0, 0, 0.65);
    padding: 24px 30px;
    margin: 20px;
}

.title-label {
    font-size: 19px;
    font-weight: 600;
    color: #%(onSurface)s;
    letter-spacing: 0.2px;
    margin-bottom: 8px;
}

.status-pill {
    background-color: alpha(#%(surfaceContainerHighest)s, 0.6);
    border: 1px solid alpha(#%(outlineVariant)s, 0.2);
    border-radius: 9999px;
    padding: 5px 18px;
    margin-bottom: 20px;
}

.status-pill-text {
    font-size: 12px;
    font-weight: 500;
    color: #%(onSurfaceVariant)s;
}

.cards-box {
    margin-bottom: 20px;
}

button.mode-card {
    background-color: alpha(#%(surfaceContainerHigh)s, 0.65);
    background-image: none;
    border: 1.5px solid alpha(#%(outlineVariant)s, 0.2);
    border-radius: 24px;
    padding: 16px 16px 18px 16px;
    min-width: 164px;
    min-height: 156px;
    transition: all 180ms ease-in-out;
    outline: none;
    box-shadow: none;
}

button.mode-card:hover {
    background-color: alpha(#%(surfaceContainerHighest)s, 0.85);
    border-color: alpha(#%(primary)s, 0.45);
}

button.mode-card.selected {
    background-color: alpha(#%(primaryContainer)s, 0.65);
    border: 2px solid #%(primary)s;
    box-shadow: 0 0 26px alpha(#%(primary)s, 0.5), 0 0 8px alpha(#%(primary)s, 0.75);
}

.mode-badge {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    background-color: alpha(#%(primary)s, 0.18);
    color: #%(primary)s;
    border: 1px solid alpha(#%(primary)s, 0.35);
    border-radius: 9999px;
    padding: 2px 8px;
    margin-bottom: 6px;
}

button.mode-card.selected .mode-badge {
    background-color: #%(primary)s;
    color: #%(onPrimary)s;
    border-color: #%(primary)s;
}

.mode-icon {
    color: alpha(#%(onSurface)s, 0.75);
    margin-bottom: 12px;
    -gtk-icon-size: 44px;
    transition: color 180ms ease-in-out;
}

button.mode-card:hover .mode-icon {
    color: #%(primary)s;
}

button.mode-card.selected .mode-icon {
    color: #%(onPrimaryContainer)s;
}

.mode-name {
    font-size: 15px;
    font-weight: 600;
    color: #%(onSurface)s;
    margin-bottom: 4px;
}

button.mode-card.selected .mode-name {
    color: #%(onPrimaryContainer)s;
    font-weight: 700;
}

.mode-desc {
    font-size: 11px;
    color: #%(onSurfaceVariant)s;
}

button.mode-card.selected .mode-desc {
    color: alpha(#%(onPrimaryContainer)s, 0.95);
}

.footer-pill {
    background-color: alpha(#%(surfaceContainerHigh)s, 0.55);
    border: 1px solid alpha(#%(outlineVariant)s, 0.2);
    border-radius: 9999px;
    padding: 6px 22px;
}

.footer-label {
    font-size: 12px;
    font-weight: 500;
    color: #%(onSurfaceVariant)s;
}
"""


def load_caelestia_colors() -> Dict[str, str]:
    """Load colors from scheme.json or current.lua or fallback."""
    colors = dict(FALLBACK_COLORS)

    # 1. Try ~/.local/state/caelestia/scheme.json
    if SCHEME_JSON.exists():
        try:
            data = json.loads(SCHEME_JSON.read_text())
            raw_colors = data.get("colours", {})
            for k, v in raw_colors.items():
                colors[k] = str(v).lstrip("#")
            return colors
        except Exception as e:
            logger.debug("Failed to read %s: %s", SCHEME_JSON, e)

    # 2. Try ~/.config/hypr/scheme/current.lua
    if SCHEME_LUA.exists():
        try:
            content = SCHEME_LUA.read_text()
            matches = re.findall(r'(\w+)\s*=\s*["\']#?([a-fA-F0-9]+)["\']', content)
            for k, v in matches:
                colors[k] = v
            return colors
        except Exception as e:
            logger.debug("Failed to read %s: %s", SCHEME_LUA, e)

    return colors


def get_caelestia_css() -> bytes:
    """Generate CSS with Caelestia color scheme."""
    colors = load_caelestia_colors()
    try:
        css = CSS_TEMPLATE % colors
    except Exception as e:
        logger.error("Error formatting CSS template with colors: %s", e)
        css = CSS_TEMPLATE % FALLBACK_COLORS
    return css.encode("utf-8")
