#!/usr/bin/env python3
"""Experimental single-game bridge. Never writes the live gamelist."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET


def run(platform, root, rom, output, videos=False, language='en'):
    binary = shutil.which('Skyscraper')
    if not binary:
        raise RuntimeError('Skyscraper is not installed or is not in PATH')
    root, rom = Path(root).resolve(), Path(rom).resolve()
    rom.relative_to(root)
    if not rom.is_file():
        raise RuntimeError('ROM does not exist')
    # Keep generated XML isolated; media paths are absolute for native import.
    with tempfile.TemporaryDirectory(prefix='batocera-skyscraper-') as temporary:
        common = [binary, '-p', platform, '-i', str(root), '-g', temporary,
                  '-o', str(root / 'media'), '-f', 'emulationstation',
                  '--lang', language]
        flags = 'unattend' + (',videos' if videos else '')
        # Config/cache/artwork remain those of the real user, as in ES-X.
        for stage in (['-s', 'screenscraper'], []):
            subprocess.run(common + stage + ['--flags', flags, str(rom)],
                           check=True, stdin=subprocess.DEVNULL)
        generated = Path(temporary) / 'gamelist.xml'
        tree = ET.parse(generated)
        selected = None
        for game in tree.getroot().findall('game'):
            candidate = Path(game.findtext('path', ''))
            if not candidate.is_absolute():
                candidate = root / candidate
            if candidate.resolve() == rom:
                selected = game
                break
        result = ET.Element('gameList')
        if selected is not None:
            for field in ('path', 'image', 'thumbnail', 'marquee', 'video', 'fanart', 'manual'):
                element = selected.find(field)
                if element is not None and element.text:
                    path = Path(element.text)
                    if not path.is_absolute():
                        element.text = str((root / path).resolve())
            result.append(selected)
        ET.ElementTree(result).write(output, encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for key in ('platform', 'root', 'rom', 'output'):
        parser.add_argument(key)
    parser.add_argument('--videos', action='store_true')
    parser.add_argument('--language', default='en')
    args = parser.parse_args()
    try:
        run(args.platform, args.root, args.rom, args.output, args.videos, args.language)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, ET.ParseError) as exc:
        parser.exit(1, 'Skyscraper bridge failed: ' + str(exc) + '\n')
