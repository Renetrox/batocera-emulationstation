#!/usr/bin/env python3
"""Regression guards for the standalone RetroPie menu and PO wiring.

These source-level checks supplement the C++ Runcommand unit tests. The full
frontend must still be built and smoke-tested on the target Linux machine.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


class StandaloneMenuTests(unittest.TestCase):
    def test_power_after_metadata_cleanup(self):
        main = read("es-app/src/main.cpp")
        platform = read("es-core/src/utils/Platform.cpp")
        self.assertIn('systemctl --no-ask-password poweroff', platform)
        self.assertIn('systemctl --no-ask-password reboot', platform)
        self.assertIn('SystemData::deleteSystems();', main)
        self.assertLess(main.index("SystemData::deleteSystems();"),
                        main.index("Utils::Platform::processQuitMode();"))
        self.assertIn('if (runShutdownCommand() != 0)', platform)
        self.assertIn('if (runRestartCommand() != 0)', platform)

    def test_standalone_restart(self):
        menu = read("es-app/src/guis/GuiMenu.cpp")
        main = read("es-app/src/main.cpp")
        platform = read("es-core/src/utils/Platform.cpp")
        self.assertIn('s->addEntry(_("RESTART EMULATIONSTATION")', menu)
        self.assertIn("QuitMode::RESTART", menu)
        self.assertIn("bool isRestartRequested()", platform)
        self.assertIn('execv("/proc/self/exe", argv);', main)
        self.assertIn("TARAVE_PORTABLE_LOCALE", main)

    def test_translations_reuse_bundled_po(self):
        cmake = read("CMakeLists.txt")
        locale = read("es-core/src/LocaleES.cpp")
        header = read("es-core/src/LocaleES.h")
        spanish = read("locale/lang/es/LC_MESSAGES/emulationstation2.po")
        self.assertIn("add_definitions(-DTARAVE_PORTABLE_LOCALE)", cmake)
        self.assertIn('Paths::getExePath() + "/locale/lang/"', locale)
        self.assertIn('mCurrentLanguage.substr(0, sep)', locale)
        self.assertIn('EsLocale::getText(x)', header)
        self.assertIn('msgid "RESTART EMULATIONSTATION"', spanish)
        self.assertIn('msgstr "REINICIAR EMULATIONSTATION"', spanish)
        self.assertIn('msgid "RESTART SYSTEM"', spanish)
        self.assertIn('msgstr "REINICIAR SISTEMA"', spanish)


if __name__ == "__main__":
    unittest.main()
