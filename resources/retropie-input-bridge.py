#!/usr/bin/env python3
"""Translate one native Batocera mapping for installed RetroPie configurators."""
import argparse
import copy
import fcntl
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

DISPATCHERS = (
    Path('/opt/retropie/supplementary/emulationstation-es-x/scripts/inputconfiguration.sh'),
    Path('/opt/retropie/supplementary/emulationstation/scripts/inputconfiguration.sh'),
)


def select_dispatcher(candidates=None):
    for script in DISPATCHERS if candidates is None else candidates:
        script = Path(script)
        if script.is_file() and (script.parent / 'configscripts').is_dir():
            return script
    raise ValueError('No installed RetroPie/ES-X controller dispatcher with configscripts was found')

NAMES = {'pageup':'leftshoulder', 'pagedown':'rightshoulder',
         'l2':'lefttrigger', 'r2':'righttrigger', 'l3':'leftthumb',
         'r3':'rightthumb', 'hotkey':'hotkeyenable',
         'joystick1up':'leftanalogup', 'joystick1left':'leftanalogleft',
         'joystick2up':'rightanalogup', 'joystick2left':'rightanalogleft'}
OPPOSITES = {'leftanalogup':'leftanalogdown', 'leftanalogleft':'leftanalogright',
             'rightanalogup':'rightanalogdown', 'rightanalogleft':'rightanalogright'}


def translate(source):
    devices = ET.parse(source).getroot().findall('inputConfig')
    if len(devices) != 1:
        raise ValueError('Expected exactly one newly configured device')
    device = copy.deepcopy(devices[0])
    if device.get('type') not in ('joystick', 'keyboard', 'cec'):
        raise ValueError('Unsupported device type')
    used = set()
    for item in device.findall('input'):
        name = NAMES.get(item.get('name'), item.get('name'))
        if not name or name in used:
            raise ValueError('Missing or conflicting input name')
        used.add(name)
        item.set('name', name)
        kind = item.get('type')
        if kind not in ('axis', 'hat', 'button', 'key'):
            raise ValueError('Unsupported input type')
        int(item.get('id', ''))
        value = int(item.get('value', ''))
        if name in OPPOSITES:
            opposite = copy.deepcopy(item)
            opposite.set('name', OPPOSITES[name])
            if kind == 'axis' and value in (-1, 1):
                opposite.set('value', str(-value))
            elif kind == 'hat' and value in (1, 2, 4, 8):
                opposite.set('value', str({1:4, 4:1, 2:8, 8:2}[value]))
            else:
                raise ValueError('Cannot infer opposite analog direction')
            device.append(opposite)
    root = ET.Element('inputList')
    root.append(device)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def atomic_write(path, data, mode=0o600):
    fd, temporary = tempfile.mkstemp(prefix='.tarave-input-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def run_configurators(script):
    script = Path(script)
    modules = script.parent / 'configscripts'
    if not script.is_file() or not modules.is_dir():
        raise ValueError('RetroPie dispatcher or configscripts directory is missing')
    # The stock dispatcher resolves configscripts relative to $0. Give it a
    # private module list that excludes its frontend writer, while keeping all
    # installed emulator configurators and the installed dispatcher itself.
    with tempfile.TemporaryDirectory(prefix='tarave-configurators-') as directory:
        bundle = Path(directory)
        dispatcher = bundle / 'inputconfiguration.sh'
        shutil.copy2(script, dispatcher)
        selected = bundle / 'configscripts'
        selected.mkdir()
        for module in modules.glob('*.sh'):
            if module.name != 'emulationstation.sh' and module.is_file():
                (selected / module.name).symlink_to(module.resolve())
        subprocess.run(['bash', str(dispatcher)], check=True)


def apply(source, home, script=None):
    data = translate(source)
    script = select_dispatcher() if script is None else script
    target = Path(home) / '.emulationstation' / 'es_temporaryinput.cfg'
    target.parent.mkdir(parents=True, exist_ok=True)
    with (target.parent / '.tarave-input.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if target.is_symlink():
            raise ValueError('Refusing a symbolic temporary input file')
        previous = target.read_bytes() if target.exists() else None
        mode = target.stat().st_mode & 0o777 if previous is not None else 0o600
        try:
            atomic_write(target, data)
            run_configurators(script)
        finally:
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                atomic_write(target, previous, mode)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--output', help='Translate only; do not configure emulators')
    args = parser.parse_args()
    try:
        if args.output:
            atomic_write(Path(args.output), translate(args.source))
        else:
            if os.getuid() == 0:
                raise ValueError('Run as the RetroPie user, not root')
            script = select_dispatcher()
            print('Tarave: configuring emulators using ' + str(script), flush=True)
            apply(args.source, pwd.getpwuid(os.getuid()).pw_dir, script)
    except (OSError, ValueError, ET.ParseError, subprocess.CalledProcessError) as error:
        parser.exit(1, 'RetroPie controller setup failed: ' + str(error) + '\n')
