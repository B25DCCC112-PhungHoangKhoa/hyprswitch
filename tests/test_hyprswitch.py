"""
Unit and integration tests for hyprswitch.
"""

import unittest
from monitor_manager import DisplayMode, DisplayPreset, MonitorInfo, MonitorManager


class TestMonitorManager(unittest.TestCase):
    def setUp(self):
        self.mgr = MonitorManager()

    def test_parse_mode_string(self):
        m1 = self.mgr.parse_mode_string("1920x1080@144.00Hz")
        self.assertIsNotNone(m1)
        self.assertEqual(m1.width, 1920)
        self.assertEqual(m1.height, 1080)
        self.assertAlmostEqual(m1.refresh_rate, 144.00)

        m2 = self.mgr.parse_mode_string("2560x1440@59.95")
        self.assertIsNotNone(m2)
        self.assertEqual(m2.width, 2560)
        self.assertEqual(m2.height, 1440)
        self.assertAlmostEqual(m2.refresh_rate, 59.95)

        m3 = self.mgr.parse_mode_string("invalid_mode")
        self.assertIsNone(m3)

    def test_internal_name_detection(self):
        self.assertTrue(self.mgr.is_internal_name("eDP-1"))
        self.assertTrue(self.mgr.is_internal_name("EDP-2"))
        self.assertTrue(self.mgr.is_internal_name("LVDS-1"))
        self.assertTrue(self.mgr.is_internal_name("DSI-1"))
        self.assertFalse(self.mgr.is_internal_name("HDMI-A-1"))
        self.assertFalse(self.mgr.is_internal_name("DP-1"))
        self.assertFalse(self.mgr.is_internal_name("DP-3"))

    def test_best_mode_sorting(self):
        modes = [
            DisplayMode(1920, 1080, 60.0, "1920x1080@60.00Hz"),
            DisplayMode(1920, 1080, 144.0, "1920x1080@144.00Hz"),
            DisplayMode(2560, 1440, 60.0, "2560x1440@60.00Hz"),
            DisplayMode(2560, 1440, 165.0, "2560x1440@165.00Hz"),
            DisplayMode(1280, 720, 60.0, "1280x720@60.00Hz"),
        ]
        mon = MonitorInfo(
            id=1,
            name="HDMI-A-1",
            description="",
            make="",
            model="",
            width=1920,
            height=1080,
            refresh_rate=60.0,
            x=0,
            y=0,
            scale=1.0,
            disabled=False,
            mirror_of="",
            available_modes=modes,
            is_internal=False
        )
        best = mon.best_mode
        self.assertIsNotNone(best)
        self.assertEqual(best.width, 2560)
        self.assertEqual(best.height, 1440)
        self.assertEqual(best.refresh_rate, 165.0)

    def test_lua_generation(self):
        # Mock get_displays
        internal = MonitorInfo(
            id=0,
            name="eDP-1",
            description="",
            make="",
            model="",
            width=1920,
            height=1200,
            refresh_rate=144.0,
            x=0,
            y=0,
            scale=1.0,
            disabled=False,
            mirror_of="",
            available_modes=[DisplayMode(1920, 1200, 144.0, "1920x1200@144.00Hz")],
            is_internal=True
        )
        external = MonitorInfo(
            id=1,
            name="HDMI-A-1",
            description="",
            make="",
            model="",
            width=1920,
            height=1080,
            refresh_rate=144.0,
            x=1920,
            y=0,
            scale=1.0,
            disabled=False,
            mirror_of="",
            available_modes=[
                DisplayMode(1920, 1080, 144.0, "1920x1080@144.00Hz"),
                DisplayMode(1920, 1080, 60.0, "1920x1080@60.00Hz")
            ],
            is_internal=False
        )
        self.mgr.get_displays = lambda: (internal, external)

        # 1. PC Only
        lua_pc, eval_pc = self.mgr.generate_lua_config(DisplayPreset.PC_ONLY)
        self.assertTrue(any('output = "eDP-1"' in cmd and 'mode = "preferred"' in cmd for cmd in eval_pc))
        self.assertTrue(any('output = "HDMI-A-1"' in cmd and 'disabled = true' in cmd for cmd in eval_pc))

        # 2. Duplicate
        lua_dup, eval_dup = self.mgr.generate_lua_config(DisplayPreset.DUPLICATE)
        self.assertTrue(any('mirror = "eDP-1"' in cmd for cmd in eval_dup))

        # 3. Extend
        lua_ext, eval_ext = self.mgr.generate_lua_config(DisplayPreset.EXTEND)
        self.assertTrue(any('position = "auto-right"' in cmd and '1920x1080@144.00' in cmd for cmd in eval_ext))

        # 4. Second Only
        lua_sec, eval_sec = self.mgr.generate_lua_config(DisplayPreset.SECOND_ONLY)
        self.assertTrue(any('output = "eDP-1"' in cmd and 'disabled = true' in cmd for cmd in eval_sec))
        self.assertTrue(any('output = "HDMI-A-1"' in cmd and 'position = "0x0"' in cmd for cmd in eval_sec))


if __name__ == "__main__":
    unittest.main()
