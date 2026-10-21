#!/usr/bin/env python3
"""Tarave native X-TRAS store integration regressions (no hardware required)."""
import configparser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TaraveXtrasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = (ROOT / "es-app/src/TaraveXtrasService.cpp").read_text()
        cls.menu = (ROOT / "es-app/src/guis/GuiMenu.cpp").read_text()
        cls.store = (ROOT / "es-app/src/guis/GuiBatoceraStore.cpp").read_text()
        cls.api = (ROOT / "es-app/src/ApiSystem.cpp").read_text()
        cls.cmake = (ROOT / "es-app/CMakeLists.txt").read_text()
        cls.source_old = (ROOT / "es-app/src/guis/GuiTaraveXtras.cpp").read_text()

    def test_reuses_native_store_and_buttons(self):
        self.assertIn('mWindow->pushGui(new GuiBatoceraStore(mWindow))', self.menu)
        self.assertNotIn('mWindow->pushGui(new GuiTaraveXtras(mWindow))', self.menu)
        self.assertIn('config->isMappedTo(BUTTON_BACK, input)', self.store)
        self.assertIn('mList->getHelpPrompts()', self.store)
        self.assertIn('mWindow->pushGui(msgBox)', self.store)
        self.assertIn('GuiBatoceraStoreEntry', self.store)
        self.assertIn('RetroPieRuncommand::enabled() ? "X-TRAS"', self.store)

    def test_no_classic_browser_compiled(self):
        self.assertIn("src/TaraveXtrasService.cpp", self.cmake)
        self.assertIn("src/TaraveXtrasService.h", self.cmake)
        self.assertNotIn("src/guis/GuiTaraveXtras.cpp", self.cmake)
        self.assertNotIn("src/guis/GuiTaraveXtras.h", self.cmake)

    def test_bundle_and_private_catalog(self):
        catalog = configparser.ConfigParser(interpolation=None)
        catalog.read(ROOT / "resources/xtras-free-games.ini")
        ready = [x for x in catalog.sections() if catalog[x].get("ready") == "yes"]
        self.assertGreaterEqual(len(ready), 5)
        for item in ready:
            for field in ("title", "system", "license", "download", "filename"):
                self.assertTrue(catalog[item].get(field), (item, field))
        self.assertIn('Paths::getUserEmulationStationPath() + "/xtras/xtras-free-games.ini"', self.service)
        self.assertIn(':/xtras-free-games.ini', self.service)

    def test_login_home_independent_from_frontend_home(self):
        self.assertIn("getpwuid(getuid())", self.service)
        self.assertIn('loginHome() + "/RetroPie-Setup"', self.service)
        self.assertIn('loginHome() + "/RetroPie/roms/"', self.service)
        self.assertIn('"TARAVE_RETROPIE_SETUP"', self.service)
        self.assertIn('"RETROPIE_SETUP_DIR"', self.service)

    def test_ports_bezel_project_with_setup(self):
        self.assertIn('"/scriptmodules/ports"', self.service)
        self.assertIn('"/scriptmodules/supplementary/bezelproject.sh"', self.service)
        self.assertIn('p.name = "module:bezelproject"', self.service)
        self.assertIn('"/retropie_packages.sh"', self.service)
        self.assertIn('sudo -n ', self.service)

    def test_no_batocera_daemon_for_retro_pie(self):
        self.assertIn('if (RetroPieRuncommand::enabled()) return TaraveXtrasService::list();', self.api)
        self.assertIn('if (RetroPieRuncommand::enabled()) return TaraveXtrasService::install(name, func);', self.api)
        self.assertIn('if (RetroPieRuncommand::enabled()) return TaraveXtrasService::remove(name, func);', self.api)
        self.assertIn('if (RetroPieRuncommand::enabled()) return; // Never run batocera-store update', self.api)
        self.assertIn('mWindow->pushGui(new GuiThemeInstaller(mWindow));', self.menu)

    def test_non_destructive_download_and_cleanup(self):
        self.assertIn('".tarave-part"', self.service)
        self.assertIn('std::rename(tmp.c_str(), dst.c_str())', self.service)
        self.assertIn('std::remove(tmp.c_str())', self.service)
        self.assertIn("if (!token(moduleId))", self.service)
        self.assertIn("if (!token(id) || !token(system) || !filename(file)", self.service)


if __name__ == "__main__":
    unittest.main()
