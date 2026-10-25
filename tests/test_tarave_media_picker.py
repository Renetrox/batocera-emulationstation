#!/usr/bin/env python3
"""Source regressions for Tarave's metadata media picker (no hardware required)."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MediaPickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.editor = (ROOT / "es-app/src/guis/GuiMetaDataEd.cpp").read_text()
        cls.browser = (ROOT / "es-app/src/guis/GuiFileBrowser.cpp").read_text()

    def test_empty_field_browses_the_game_system(self):
        self.assertIn('filePath.empty() ? relativePath :', self.editor)
        self.assertIn('Utils::FileSystem::isDirectory(dir)', self.editor)
        self.assertIn('new GuiFileBrowser(mWindow, dir, filePath, type, updateVal, title)', self.editor)

    def test_media_is_selected_without_invoking_scraper(self):
        self.assertIn('ed->setValue(newVal.empty() ? "" :', self.editor)
        self.assertIn('Utils::FileSystem::createRelativePath(newVal, relativePath, true)', self.editor)
        self.assertIn('row.makeAcceptInputHandler', self.editor)
        self.assertIn('mMetaData->set(key, val)', self.editor)

    def test_uppercase_media_extensions_are_accepted(self):
        self.assertIn('Utils::String::toLower(Utils::FileSystem::getExtension(file.path))', self.browser)
        for extension in ('.jpg', '.jpeg', '.png', '.gif', '.svg'):
            self.assertIn('"' + extension + '"', self.browser)

    def test_select_shortcut_ignores_button_release(self):
        self.assertIn('config->isMappedTo("select", input) && input.value != 0', self.browser)


if __name__ == "__main__":
    unittest.main()
