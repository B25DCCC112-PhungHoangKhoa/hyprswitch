"""
Test cycling logic and current mode detection.
"""

import unittest
from monitor_manager import DisplayMode, DisplayPreset, MonitorInfo, MonitorManager


class TestCyclingAndDetection(unittest.TestCase):
    def setUp(self):
        from pathlib import Path
        self.mgr = MonitorManager()
        self.mgr.monitors_lua = Path("/tmp/non_existent_monitors.lua")

    def test_mode_cycling_progression(self):
        modes = [
            DisplayPreset.PC_ONLY,
            DisplayPreset.DUPLICATE,
            DisplayPreset.EXTEND,
            DisplayPreset.SECOND_ONLY
        ]
        # Cycling sequence
        for i in range(len(modes)):
            next_mode = (modes[i] + 1) % 4
            self.assertEqual(next_mode, (i + 1) % 4)

    def test_detect_current_mode(self):
        def make_monitors(int_disabled, ext_disabled, ext_mirror):
            internal = MonitorInfo(
                id=0, name="eDP-1", description="", make="", model="",
                width=1920, height=1200, refresh_rate=144.0, x=0, y=0, scale=1.0,
                disabled=int_disabled, mirror_of="", available_modes=[], is_internal=True
            )
            external = MonitorInfo(
                id=1, name="DP-1", description="", make="", model="",
                width=1920, height=1080, refresh_rate=144.0, x=1920, y=0, scale=1.0,
                disabled=ext_disabled, mirror_of=ext_mirror, available_modes=[], is_internal=False
            )
            return internal, external

        # PC ONLY: external is disabled
        self.mgr.get_displays = lambda: make_monitors(int_disabled=False, ext_disabled=True, ext_mirror="")
        self.assertEqual(self.mgr.detect_current_mode(), DisplayPreset.PC_ONLY)

        # SECOND ONLY: internal is disabled
        self.mgr.get_displays = lambda: make_monitors(int_disabled=True, ext_disabled=False, ext_mirror="")
        self.assertEqual(self.mgr.detect_current_mode(), DisplayPreset.SECOND_ONLY)

        # DUPLICATE: external mirrors eDP-1
        self.mgr.get_displays = lambda: make_monitors(int_disabled=False, ext_disabled=False, ext_mirror="eDP-1")
        self.assertEqual(self.mgr.detect_current_mode(), DisplayPreset.DUPLICATE)

        # EXTEND: both active, no mirror
        self.mgr.get_displays = lambda: make_monitors(int_disabled=False, ext_disabled=False, ext_mirror="")
        self.assertEqual(self.mgr.detect_current_mode(), DisplayPreset.EXTEND)


if __name__ == "__main__":
    unittest.main()
