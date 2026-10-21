#!/usr/bin/env python3
"""Isolated regression tests; never touch installed RetroArch configurations."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "resources" / "retropie-player-order.py"
spec = importlib.util.spec_from_file_location("tarave_player_order", SRC)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class RetroPiePlayerOrderTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.settings = self.root / "es_settings.cfg"
        self.retroarch = self.root / "retroarch.cfg"
        self.retroarch.write_text("# Keep my configuration\nvideo_fullscreen = \"true\"\n", encoding="utf-8")
        self.devices = [
            {"index": 0, "name": "Xbox Controller", "guid": "aaa", "path": "/dev/input/event0"},
            {"index": 1, "name": "Retro Pad", "guid": "bbb", "path": "/dev/input/event1"}
        ]

    def save_preferences(self, **prefs):
        root = ET.Element("config")
        for name, value in prefs.items():
            ET.SubElement(root, "string", name=name, value=str(value))
        ET.ElementTree(root).write(self.settings, encoding="utf-8")

    def test_no_selection_never_changes_existing_config(self):
        self.save_preferences()
        before = self.retroarch.read_bytes()
        self.assertEqual(bridge.saved_players(self.settings), {})
        self.assertFalse(bridge.sync({}, self.devices, self.retroarch))
        self.assertEqual(self.retroarch.read_bytes(), before)

    def test_explicit_player_one_moves_second_device_first(self):
        self.save_preferences(**{"INPUT P1NAME": "Retro Pad", "INPUT P1GUID": "bbb"})
        prefs = bridge.saved_players(self.settings)
        self.assertEqual(bridge.choose_players(prefs, self.devices), {1: 1, 2: 0})
        self.assertTrue(bridge.sync(prefs, self.devices, self.retroarch))
        result = self.retroarch.read_text()
        self.assertIn('input_player1_joypad_index = "1"', result)
        self.assertIn('input_player2_joypad_index = "0"', result)
        self.assertIn("video_fullscreen", result)
        self.assertFalse(bridge.sync(prefs, self.devices, self.retroarch))

    def test_name_assignments_follow_reconnection_order(self):
        prefs = {1: ("Retro Pad", "bbb", "")}
        result_a = bridge.choose_players(prefs, self.devices)
        reordered = [dict(self.devices[1], index=0), dict(self.devices[0], index=1)]
        result_b = bridge.choose_players(prefs, reordered)
        self.assertEqual(result_a, {1: 1, 2: 0})
        self.assertEqual(result_b, {1: 0, 2: 1})

    def test_reverting_default_restores_unrelated_settings(self):
        prefs = {1: ("Retro Pad", "bbb", "")}
        self.assertTrue(bridge.sync(prefs, self.devices, self.retroarch))
        self.assertTrue(bridge.sync({}, self.devices, self.retroarch))
        self.assertEqual(self.retroarch.read_text(),
                         "# Keep my configuration\nvideo_fullscreen = \"true\"\n")

    def test_existing_manual_assignment_is_never_overwritten(self):
        self.retroarch.write_text("input_player1_joypad_index = \"3\"\n", encoding="utf-8")
        before = self.retroarch.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "existing"):
            bridge.sync({1: ("Retro Pad", "bbb", "")}, self.devices, self.retroarch)
        self.assertEqual(self.retroarch.read_bytes(), before)

    def test_manual_override_added_after_tarave_relinquishes_control(self):
        prefs = {1: ("Retro Pad", "bbb", "")}
        bridge.sync(prefs, self.devices, self.retroarch)
        text = self.retroarch.read_text()
        self.retroarch.write_text(text + 'input_player1_joypad_index = "3"\n')
        self.assertTrue(bridge.sync(prefs, self.devices, self.retroarch))
        final = self.retroarch.read_text()
        self.assertNotIn(bridge.BEGIN, final)
        self.assertIn('input_player1_joypad_index = "3"', final)

    def test_duplicate_names_without_a_path_are_rejected(self):
        twins = [
            {"index": 0, "name": "Gamepad", "guid": "aaa", "path": ""},
            {"index": 1, "name": "Gamepad", "guid": "aaa", "path": ""}
        ]
        with self.assertRaisesRegex(RuntimeError, "ambiguous"):
            bridge.choose_players({1: ("Gamepad", "aaa", "")}, twins)

    def test_disconnected_preference_does_not_leave_stale_indexes(self):
        self.assertEqual(bridge.choose_players({1: ("Not connected", "zzz", "")},
                                               self.devices), {1: 0, 2: 1})
        # Old block is safely replaced with available defaults.
        stale = bridge.updated_config("video_fullscreen = \"true\"\n",
                                      {1: 7, 2: 6})
        clean = bridge.updated_config(stale, {1: 0, 2: 1})
        self.assertNotIn('input_player1_joypad_index = "7"', clean)

    def test_missing_permissions_or_symlink_are_non_destructive(self):
        target = self.root / "target.cfg"
        target.write_text("test = true\n", encoding="utf-8")
        self.retroarch.unlink()
        self.retroarch.symlink_to(target)
        self.assertFalse(bridge.sync({1: ("Retro Pad", "bbb", "")},
                                     self.devices, self.retroarch))
        self.assertEqual(target.read_text(), "test = true\n")

    def test_other_joystick_selection_addon_retains_control(self):
        (self.root / "runcommand-onstart.sh").write_text(
            "bash /opt/retropie/supplementary/joystick-selection/js-onstart.sh\n")
        before = self.retroarch.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "joystick-selection"):
            bridge.sync({1: ("Retro Pad", "bbb", "")},
                        self.devices, self.retroarch)
        self.assertEqual(self.retroarch.read_bytes(), before)

    def test_opt_out_clears_only_managed_block(self):
        prefs = {1: ("Retro Pad", "bbb", "")}
        bridge.sync(prefs, self.devices, self.retroarch)
        bridge.sync(prefs, self.devices, self.retroarch, enabled=False)
        self.assertEqual(self.retroarch.read_text(),
                         "# Keep my configuration\nvideo_fullscreen = \"true\"\n")

    def test_frontend_preflight_is_fail_open(self):
        source = (ROOT / "es-app/src/FileData.cpp").read_text()
        self.assertIn(':/retropie-player-order.py', source)
        self.assertIn('" ; exec " + runcommand', source)
        self.assertIn('return runcommand;', source)


if __name__ == "__main__":
    unittest.main()
