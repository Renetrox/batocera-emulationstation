#!/usr/bin/env python3
"""Structural regression checks for the optional RetroPie-only X-TRAS experiment."""
from pathlib import Path
import configparser
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TaraveXtrasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = (ROOT / "es-app/src/guis/GuiTaraveXtras.cpp").read_text()
        cls.header = (ROOT / "es-app/src/guis/GuiTaraveXtras.h").read_text()
        cls.menu = (ROOT / "es-app/src/guis/GuiMenu.cpp").read_text()
        cls.cmake = (ROOT / "es-app/CMakeLists.txt").read_text()

    def test_uses_taraves_isolated_home_not_esx(self):
        self.assertIn('Paths::getUserEmulationStationPath() + "/xtras/', self.code)
        self.assertNotIn('"/.emulationstation/esx/', self.code)
        self.assertNotIn('~/.emulationstation', self.code)

    def test_catalog_bundled_and_licensed(self):
        path = ROOT / "resources/xtras-free-games.ini"
        self.assertTrue(path.is_file())
        catalog = configparser.ConfigParser(interpolation=None)
        catalog.read(path)
        ready = 0
        for section in catalog.sections():
            ent = catalog[section]
            if ent.get('ready') == 'yes':
                ready += 1
                for key in ('title', 'system', 'filename', 'author', 'license', 'download', 'license_url'):
                    self.assertTrue(ent.get(key), (section, key))
            self.assertIn(ent.get('ready'), ('yes', 'no'))
        self.assertGreaterEqual(ready, 5)
        self.assertIn(':/xtras-free-games.ini', self.code)

    def test_catalog_does_not_require_retropie_setup(self):
        self.assertIn("const bool hasRetroPieSetup = findRetroPieSetup()", self.code)
        self.assertIn("if (hasRetroPieSetup)", self.code)
        self.assertIn("loadFreeGames();", self.code)
        self.assertNotIn("if (!findRetroPieSetup())\n        return false;", self.code)

    def test_ports_and_retro_pie_extra_supplementary(self):
        self.assertIn('"/scriptmodules/ports"', self.code)
        self.assertIn('"/scriptmodules/supplementary"', self.code)
        self.assertIn('"/bezelproject.sh"', self.code)
        self.assertIn('port.id', self.code)
        self.assertIn(' _autoupdate_ >> ', self.code)

    def test_copy_installed_with_frontend(self):
        self.assertIn("src/guis/GuiTaraveXtras.h", self.cmake)
        self.assertIn("src/guis/GuiTaraveXtras.cpp", self.cmake)
        self.assertIn('GuiTaraveXtras', self.header)

    def test_menu_is_retro_pie_only_and_themes_remain(self):
        menu = self.menu
        self.assertIn('#if !defined(BATOCERA) && !defined(RETROBAT) && !defined(WIN32)', menu)
        self.assertIn('updateGui->addEntry("X-TRAS"', menu)
        self.assertIn('mWindow->pushGui(new GuiTaraveXtras(mWindow))', menu)
        self.assertIn('mWindow->pushGui(new GuiThemeInstaller(mWindow))', menu)
        self.assertIn('mWindow->pushGui(new GuiBatoceraStore(mWindow))', menu)

    def test_installs_are_explicit_and_remove_requires_confirmation(self):
        self.assertIn('canUseSudo()', self.code)
        self.assertIn('sudo -n ', self.code)
        self.assertIn('new GuiMsgBox(', self.code)
        self.assertIn('".part"', self.code)
        self.assertIn('::rename(tmp.c_str(), dst.c_str())', self.code)


if __name__ == "__main__":
    unittest.main()
