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

    def test_help_bar_localizes_labels_not_controller_keys(self):
        # Help labels can come pretranslated from screens or as raw English
        # from components. The rendering boundary must support both cases.
        helpbar = read("es-core/src/components/HelpComponent.cpp")
        self.assertIn('#include "LocaleES.h"', helpbar)
        self.assertIn('Utils::String::toUpper(_(it->second))', helpbar)
        self.assertIn('InputConfig::buttonLabel(it->first)', helpbar)

        for name in ("ComponentList", "ComponentTab"):
            source = read(f"es-core/src/components/{name}.cpp")
            self.assertIn('HelpPrompt("up/down", _("CHOOSE"))', source)
            self.assertNotIn('HelpPrompt(_("up/down"), _("CHOOSE"))', source)

        for language in ("es", "es_MX"):
            catalog = read(f"locale/lang/{language}/LC_MESSAGES/emulationstation2.po")
            for key in ("CHOOSE", "SELECT", "BACK", "CLOSE", "SEARCH"):
                self.assertIn(f'msgid "{key}"', catalog)
                self.assertIn(f'msgid "{key}"\nmsgstr "', catalog)

    def test_retropie_cheevos_theme_binding(self):
        systems = read("es-app/src/SystemData.cpp")
        original = read("es-app/src/FileData.cpp")
        adapter = read("es-app/src/RetroPieAchievements.h")
        self.assertIn("RetroPieAchievements::read()", systems)
        self.assertIn('sysData["global.cheevos"] = cheevosEnabled', systems)
        self.assertIn('sysData["cheevos.username"] = cheevosUser', systems)
        self.assertIn('sysData["system.cheevos"] = cheevosEnabled', systems)
        self.assertIn('core.compare(0, 3, "lr-") == 0', systems)
        self.assertIn("MetaDataId::CheevosId", original)
        self.assertIn("if (key != \"cheevos_enable\" && key != \"cheevos_username\")", adapter)
        self.assertNotIn("cheevos_password", adapter)
        self.assertNotIn("cheevos_token", adapter)

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
