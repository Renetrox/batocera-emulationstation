#!/usr/bin/env python3
"""Standalone import tests: no changes to legacy frontend or shared catalog."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

TOOL = Path(__file__).resolve().parents[1] / "resources/tarave-import-legacy-systems.py"
spec = importlib.util.spec_from_file_location("tarave_import", TOOL)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class ImportTests(unittest.TestCase):
    def test_one_time_import_private_and_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "user"
            legacy = home / ".emulationstation"
            legacy.mkdir(parents=True)
            custom = legacy / "es_systems_custom.cfg"
            custom.write_text(
                '<systemList><system><name>wine</name><path>~/RetroPie/roms/wine</path>'
                '<extension>.sh</extension><command>mywine %ROM%</command></system>'
                '<system><name>kodi</name><path>~/RetroPie/roms/kodi</path>'
                '<extension>.sh</extension><command>kodi %ROM%</command></system>'
                '<system><name>nes</name><path>~/nes</path>'
                '<extension>.nes</extension><command>nes %ROM%</command></system></systemList>'
            )
            shared = Path(directory) / "global.cfg"
            shared.write_text('<systemList><system><name>kodi</name></system></systemList>')
            original = custom.read_bytes()
            base = shared.read_bytes()
            output = home / ".local/share/batocera-es-test/.emulationstation/es_systems_legacy_import.cfg"
            names = app.import_systems(home, output, shared)
            self.assertEqual(names, ["nes", "wine"])
            self.assertIn(b"<name>wine</name>", output.read_bytes())
            self.assertIn(b"<name>nes</name>", output.read_bytes())
            self.assertEqual(custom.read_bytes(), original)
            self.assertEqual(shared.read_bytes(), base)
            self.assertEqual(app.import_systems(home, output, shared), [])

    def test_append_new_missing_system_without_overwriting_prior_import(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            legacy = home / ".emulationstation"
            legacy.mkdir(parents=True)
            original = legacy / "es_systems_custom.cfg"
            original.write_text(
                '<systemList><system><name>wine</name><path>~/RetroPie/roms/wine</path>'
                '<extension>.sh</extension><command>wine %ROM%</command></system></systemList>')
            catalog = home / "shared.cfg"
            catalog.write_text("<systemList/>")
            target = home / "tarave/es_systems_legacy_import.cfg"
            self.assertEqual(app.import_systems(home, target, catalog), ["wine"])
            tree = ET.parse(target)
            tree.find("./system/command").text = "custom Tarave override"
            tree.write(target)
            original.write_text(
                '<systemList><system><name>wine</name><path>~/RetroPie/roms/wine</path>'
                '<extension>.sh</extension><command>new wine</command></system>'
                '<system><name>openbor</name><path>~/RetroPie/roms/openbor</path>'
                '<extension>.pak</extension><command>openbor %ROM%</command></system>'
                '</systemList>')
            self.assertEqual(app.import_systems(home, target, catalog), ["openbor"])
            result = ET.parse(target)
            by_name = {system.findtext("name"): system for system in result.findall("system")}
            self.assertEqual(by_name["wine"].findtext("command"), "custom Tarave override")
            self.assertEqual(by_name["openbor"].findtext("command"), "openbor %ROM%")

    def test_absent_prior_frontend_no_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            output = base / "private/es_systems_legacy_import.cfg"
            self.assertEqual(app.import_systems(base, output, base / "missing.cfg"), [])
            self.assertFalse(output.exists())

    def test_broken_xml_does_not_create_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / ".emulationstation"
            source.mkdir()
            (source / "es_systems.cfg").write_text("<broken")
            target = base / "private/es_systems_legacy_import.cfg"
            with self.assertRaises(Exception):
                app.import_systems(base, target, base / "absent")
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
