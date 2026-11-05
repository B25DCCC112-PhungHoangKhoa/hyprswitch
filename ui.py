"""
GTK4 UI for hyprswitch with Layer Shell integration,
Caelestia color scheme (matching caelestia-connect), and modern cards.
"""

import logging
from typing import Callable, List, Optional
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib

try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False

from monitor_manager import DisplayPreset, MonitorInfo
from theme import get_caelestia_css

logger = logging.getLogger("hyprswitch.ui")


class ModeCardWidget(Gtk.Button):
    def __init__(
        self,
        preset: int,
        title: str,
        subtitle: str,
        icon_name: str,
        on_clicked: Callable[[int], None]
    ):
        super().__init__()
        self.preset = preset
        self.on_clicked = on_clicked

        self.add_css_class("mode-card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_child(box)

        # Icon
        self.icon = Gtk.Image.new_from_icon_name(icon_name)
        self.icon.set_pixel_size(44)
        self.icon.add_css_class("mode-icon")
        box.append(self.icon)

        # Title
        self.title_label = Gtk.Label(label=title)
        self.title_label.add_css_class("mode-name")
        self.title_label.set_justify(Gtk.Justification.CENTER)
        box.append(self.title_label)

        # Subtitle
        self.desc_label = Gtk.Label(label=subtitle)
        self.desc_label.add_css_class("mode-desc")
        self.desc_label.set_wrap(True)
        self.desc_label.set_max_width_chars(18)
        self.desc_label.set_justify(Gtk.Justification.CENTER)
        box.append(self.desc_label)

        self.connect("clicked", lambda btn: self.on_clicked(self.preset))

    def set_selected(self, selected: bool):
        if selected:
            self.add_css_class("selected")
        else:
            self.remove_css_class("selected")


class SwitcherWindow(Gtk.ApplicationWindow):
    def __init__(
        self,
        app: Gtk.Application,
        internal_mon: Optional[MonitorInfo],
        external_mon: Optional[MonitorInfo],
        current_mode: int,
        on_mode_selected: Callable[[int], None],
        on_cancel: Callable[[], None]
    ):
        super().__init__(application=app)
        self.internal_mon = internal_mon
        self.external_mon = external_mon
        self.current_mode = current_mode
        self.on_mode_selected = on_mode_selected
        self.on_cancel = on_cancel

        self.cards: List[ModeCardWidget] = []

        self._setup_layer_shell()
        self._load_css()
        self._build_ui()

    def _setup_layer_shell(self):
        self.add_css_class("switcher-window")
        if HAS_LAYER_SHELL:
            Gtk4LayerShell.init_for_window(self)
            Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
            Gtk4LayerShell.set_namespace(self, "hyprswitch")
            Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.EXCLUSIVE)
            # Center on screen
            for edge in (
                Gtk4LayerShell.Edge.TOP,
                Gtk4LayerShell.Edge.BOTTOM,
                Gtk4LayerShell.Edge.LEFT,
                Gtk4LayerShell.Edge.RIGHT
            ):
                Gtk4LayerShell.set_anchor(self, edge, False)
        else:
            self.set_title("Display Projection")
            self.set_default_size(720, 220)

    def _load_css(self):
        provider = Gtk.CssProvider()
        css_data = get_caelestia_css()
        provider.load_from_data(css_data)
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10
            )

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.add_css_class("main-container")
        self.set_child(main_box)

        # Header Title
        title = Gtk.Label(label="Display Projection")
        title.add_css_class("title-label")
        title.set_halign(Gtk.Align.CENTER)
        main_box.append(title)

        # Status pill with detected monitors
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status_box.add_css_class("status-pill")
        status_box.set_halign(Gtk.Align.CENTER)

        status_text = self._format_status_text()
        self.status_label = Gtk.Label(label=status_text)
        self.status_label.add_css_class("status-pill-text")
        status_box.append(self.status_label)
        main_box.append(status_box)

        # Cards horizontal box
        cards_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        cards_box.add_css_class("cards-box")
        cards_box.set_halign(Gtk.Align.CENTER)
        main_box.append(cards_box)

        presets = [
            DisplayPreset.PC_ONLY,
            DisplayPreset.DUPLICATE,
            DisplayPreset.EXTEND,
            DisplayPreset.SECOND_ONLY
        ]

        for p in presets:
            sub = self._get_preset_subtext(p)
            card = ModeCardWidget(
                preset=p,
                title=DisplayPreset.NAMES[p],
                subtitle=sub,
                icon_name=DisplayPreset.ICONS[p],
                on_clicked=self.on_mode_selected
            )
            self.cards.append(card)
            cards_box.append(card)

        # Footer pill
        footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        footer_box.add_css_class("footer-pill")
        footer_box.set_halign(Gtk.Align.CENTER)

        self.footer_label = Gtk.Label(
            label="Enter to select   •   Win+P to cycle   •   Esc to cancel"
        )
        self.footer_label.add_css_class("footer-label")
        footer_box.append(self.footer_label)
        main_box.append(footer_box)

        # Update initial selection
        self.set_highlighted_mode(self.current_mode)

    def _format_status_text(self) -> str:
        int_desc = (
            f"Internal: {self.internal_mon.name} ({self.internal_mon.width}x{self.internal_mon.height}@{self.internal_mon.refresh_rate:.0f}Hz)"
            if self.internal_mon else "Internal: None"
        )
        if self.external_mon:
            ext_best = self.external_mon.best_mode
            ext_mode = f"{ext_best.width}x{ext_best.height}@{ext_best.refresh_rate:.0f}Hz" if ext_best else "Auto"
            ext_desc = f"External: {self.external_mon.name} ({ext_mode})"
        else:
            ext_desc = "External: No external display detected"
        return f"{int_desc}   |   {ext_desc}"

    def _get_preset_subtext(self, preset: int) -> str:
        int_name = self.internal_mon.name if self.internal_mon else "Built-in"
        ext_name = self.external_mon.name if self.external_mon else "External"

        if preset == DisplayPreset.PC_ONLY:
            return f"Built-in ({int_name}) only"
        elif preset == DisplayPreset.DUPLICATE:
            return f"Mirror {int_name} to {ext_name}"
        elif preset == DisplayPreset.EXTEND:
            if self.external_mon and self.external_mon.best_mode:
                best = self.external_mon.best_mode
                return f"Dual Screen ({best.width}x{best.height}@{best.refresh_rate:.0f}Hz)"
            return "Extend side-by-side"
        elif preset == DisplayPreset.SECOND_ONLY:
            return f"{ext_name} only"
        return ""

    def set_highlighted_mode(self, preset: int):
        self.current_mode = preset
        for card in self.cards:
            is_sel = (card.preset == preset)
            card.set_selected(is_sel)
            if is_sel:
                card.grab_focus()
        mode_name = DisplayPreset.NAMES.get(preset, "Mode")
        self.footer_label.set_text(
            f"Enter to select '{mode_name}'   •   Win+P to cycle   •   Esc to cancel"
        )
