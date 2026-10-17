import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location('bridge', Path(__file__).parents[1] / 'resources/skyscraper-batocera.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

class BridgeTests(unittest.TestCase):
    def test_selection_paths_and_live_gamelist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ROMs with spaces ' $"
            root.mkdir()
            rom = root / "A $(touch nope).zip"
            rom.touch()
            live = root / 'gamelist.xml'
            live.write_text('<gameList><sentinel/></gameList>')
            calls = []
            def execute(args, **kwargs):
                calls.append(args)
                if '-s' not in args:
                    doc = ET.Element('gameList')
                    for filename in ('other.zip', rom.name):
                        game = ET.SubElement(doc, 'game')
                        ET.SubElement(game, 'path').text = './' + filename
                        ET.SubElement(game, 'name').text = filename
                        ET.SubElement(game, 'image').text = './media/a.png'
                    ET.ElementTree(doc).write(Path(args[args.index('-g')+1]) / 'gamelist.xml')
            out = Path(tmp) / 'result.xml'
            with patch.object(bridge.shutil, 'which', return_value='/bin/Skyscraper'), patch.object(bridge.subprocess, 'run', side_effect=execute):
                bridge.run('snes', root, rom, out, True, 'es')
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0][-1], str(rom))
            self.assertIn('screenscraper', calls[0])
            self.assertNotIn('-s', calls[1])
            self.assertIn('unattend,videos', calls[1])
            games = ET.parse(out).getroot().findall('game')
            self.assertEqual(len(games), 1)
            self.assertEqual(games[0].findtext('path'), str(rom))
            self.assertEqual(games[0].findtext('image'), str(root / 'media/a.png'))
            self.assertEqual(live.read_text(), '<gameList><sentinel/></gameList>')

    def test_gather_failure_prevents_generate(self):
        with tempfile.TemporaryDirectory() as tmp:
            rom = Path(tmp) / 'a.zip'
            rom.touch()
            with patch.object(bridge.shutil, 'which', return_value='/bin/Skyscraper'), patch.object(bridge.subprocess, 'run', side_effect=bridge.subprocess.CalledProcessError(1, 'Skyscraper')) as process:
                with self.assertRaises(bridge.subprocess.CalledProcessError):
                    bridge.run('snes', tmp, rom, Path(tmp)/'result.xml')
                self.assertEqual(process.call_count, 1)

    def test_outside_rom_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(bridge.shutil, 'which', return_value='/bin/Skyscraper'):
            with self.assertRaises(ValueError):
                bridge.run('snes', tmp, '/outside.zip', '/unused')

    def test_missing_binary(self):
        with patch.object(bridge.shutil, 'which', return_value=None):
            with self.assertRaises(RuntimeError):
                bridge.run('snes', '/tmp', '/tmp/a', '/tmp/b')

if __name__ == '__main__':
    unittest.main()
