#!/usr/bin/env python3
"""Bridge Tarave's named player assignments to RetroArch on RetroPie.

Called immediately before the normal Runcommand launcher. It changes only a
clearly marked block in the global RetroArch config, never emulator mappings,
RetroPie input configs, or custom Runcommand hooks. Failure must not block games.
"""
import argparse
import ctypes
import ctypes.util
import fcntl
import os
from pathlib import Path
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

BEGIN = "# BEGIN TARAVE PLAYER ORDER (managed)"
END = "# END TARAVE PLAYER ORDER (managed)"
RETROARCH = Path("/opt/retropie/configs/all/retroarch.cfg")
CONFLICT = re.compile(r"(?m)^[ \t]*input_player[1-8]_joypad_index[ \t]*=")
SDL_INIT_JOYSTICK = 0x00000200


def saved_players(settings):
    if not settings.is_file():
        return {}
    root = ET.parse(settings).getroot()
    values = {node.get("name"): node.get("value", "")
              for node in root.findall("string")}
    return {
        slot: (values.get("INPUT P%dNAME" % slot, "DEFAULT"),
               values.get("INPUT P%dGUID" % slot, ""),
               values.get("INPUT P%dPATH" % slot, ""))
        for slot in range(1, 9)
        if values.get("INPUT P%dNAME" % slot, "DEFAULT") not in ("", "DEFAULT")
        or values.get("INPUT P%dPATH" % slot, "")
    }


class SDL_GUID(ctypes.Structure):
    _fields_ = [("data", ctypes.c_uint8 * 16)]


def connected_devices():
    library = ctypes.util.find_library("SDL2-2.0") or ctypes.util.find_library("SDL2")
    if not library:
        raise RuntimeError("SDL2 library not found")
    sdl = ctypes.CDLL(library)
    sdl.SDL_InitSubSystem.argtypes = [ctypes.c_uint32]
    sdl.SDL_InitSubSystem.restype = ctypes.c_int
    sdl.SDL_NumJoysticks.restype = ctypes.c_int
    sdl.SDL_JoystickNameForIndex.argtypes = [ctypes.c_int]
    sdl.SDL_JoystickNameForIndex.restype = ctypes.c_char_p
    sdl.SDL_JoystickGetDeviceGUID.argtypes = [ctypes.c_int]
    sdl.SDL_JoystickGetDeviceGUID.restype = SDL_GUID
    sdl.SDL_JoystickGetGUIDString.argtypes = [SDL_GUID, ctypes.c_void_p, ctypes.c_int]
    path_for_index = getattr(sdl, "SDL_JoystickPathForIndex", None)
    if path_for_index:
        path_for_index.argtypes = [ctypes.c_int]
        path_for_index.restype = ctypes.c_char_p
    if sdl.SDL_InitSubSystem(SDL_INIT_JOYSTICK) != 0:
        raise RuntimeError("SDL2 joystick subsystem unavailable")
    try:
        devices = []
        for index in range(max(0, sdl.SDL_NumJoysticks())):
            name = sdl.SDL_JoystickNameForIndex(index)
            if not name:
                continue
            guid_buf = ctypes.create_string_buffer(33)
            sdl.SDL_JoystickGetGUIDString(sdl.SDL_JoystickGetDeviceGUID(index),
                                          guid_buf, len(guid_buf))
            raw_path = path_for_index(index) if path_for_index else None
            devices.append({
                "index": index,
                "name": name.decode("utf-8", "replace"),
                "guid": guid_buf.value.decode("ascii", "replace"),
                "path": raw_path.decode("utf-8", "replace") if raw_path else ""
            })
        return devices
    finally:
        sdl.SDL_QuitSubSystem.argtypes = [ctypes.c_uint32]
        sdl.SDL_QuitSubSystem(SDL_INIT_JOYSTICK)


def same_path(saved, actual):
    if not saved or not actual:
        return False
    if saved == actual or os.path.realpath(saved) == os.path.realpath(actual):
        return True
    # The frontend saves the parent USB/Bluetooth syspath under udev, whereas
    # SDL often reports /dev/input/eventN. Compare sysfs ancestry as well.
    if saved.startswith("/sys/") and actual.startswith("/dev/input/"):
        event_name = Path(actual).name
        event_sysfs = Path("/sys/class/input") / event_name / "device"
        if event_sysfs.exists():
            parent = os.path.realpath(str(event_sysfs))
            stored = os.path.realpath(saved)
            return parent == stored or parent.startswith(stored + "/")
    return False


def choose_players(preferences, devices):
    """Return SDL indices per player, or None on an ambiguous match."""
    available = list(devices)
    assigned = {}
    # Follow Tarave InputManager priority: PATH, then GUID+NAME, then NAME.
    for criterion in ("path", "guid", "name"):
        for slot in sorted(preferences):
            if slot in assigned:
                continue
            name, guid, path = preferences[slot]
            if criterion == "path" and path:
                matches = [dev for dev in available if same_path(path, dev["path"])]
            elif criterion == "guid" and name and guid:
                matches = [dev for dev in available
                           if dev["name"] == name and dev["guid"].lower() == guid.lower()]
            elif criterion == "name" and name:
                matches = [dev for dev in available if dev["name"] == name]
            else:
                continue
            if len(matches) > 1:
                # Two identical controllers require a resolvable physical path.
                if criterion == "name":
                    raise RuntimeError("ambiguous controllers named %r" % name)
                continue
            if len(matches) == 1:
                chosen = matches[0]
                assigned[slot] = chosen["index"]
                available.remove(chosen)
    # Assign remaining available controllers without duplicating an explicit
    # slot. Unplugged controllers simply stop claiming a player.
    for slot in range(1, 9):
        if slot not in assigned and available:
            assigned[slot] = available.pop(0)["index"]
    return assigned


def strip_managed(content):
    if BEGIN not in content and END not in content:
        return content, False
    if content.count(BEGIN) != 1 or content.count(END) != 1:
        raise RuntimeError("malformed Tarave block; not changing RetroArch config")
    start = content.find(BEGIN)
    stop = content.find(END)
    if stop < start:
        raise RuntimeError("misordered Tarave block; not changing RetroArch config")
    stop += len(END)
    if stop < len(content) and content[stop] == "\n":
        stop += 1
    return content[:start] + content[stop:], True


def updated_config(original, assignments, enabled=True):
    base, has_block = strip_managed(original)
    if not enabled or not assignments:
        return base if has_block else original
    # An existing manual mapping or joystick-selection add-on wins. Never
    # replace a user's independently managed input_playerN_joypad_index.
    if CONFLICT.search(base):
        raise RuntimeError("existing RetroArch player-index overrides; leaving untouched")
    body = "\n".join('input_player%d_joypad_index = "%d"' % (n, index)
                     for n, index in sorted(assignments.items()))
    separator = "" if not base or base.endswith("\n") else "\n"
    return base + separator + BEGIN + "\n" + body + "\n" + END + "\n"


def sync(preferences, devices, config_path=RETROARCH, enabled=True):
    if not config_path.is_file() or config_path.is_symlink():
        return False
    # Avoid stomping on an installed joystick-selection package's Runcommand
    # hooks; that package already owns RetroArch player assignments.
    hook = config_path.parent / "runcommand-onstart.sh"
    if enabled and preferences and hook.is_file() and "joystick-selection" in hook.read_text(errors="replace").lower():
        raise RuntimeError("RetroPie joystick-selection hook detected; leaving it in control")
    config_path = Path(config_path)
    lock_path = config_path.parent / ".tarave-player-order.lock"
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        old = config_path.read_text(encoding="utf-8")
        assignments = choose_players(preferences, devices) if enabled and preferences else {}
        new = updated_config(old, assignments, enabled=enabled)
        if old == new:
            return False
        stat = config_path.stat()
        fd, temp = tempfile.mkstemp(prefix=".tarave-joypads-", dir=config_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                os.fchmod(output.fileno(), stat.st_mode & 0o777)
                output.write(new)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp, config_path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--retroarch", type=Path, default=RETROARCH)
    args = parser.parse_args()
    enabled = os.environ.get("TARAVE_RETROPIE_PLAYER_ORDER", "1") != "0"
    try:
        preferences = saved_players(args.settings) if enabled else {}
        # No SDL access needed if there are no explicit selections.
        devices = connected_devices() if preferences else []
        changed = sync(preferences, devices, args.retroarch, enabled=enabled)
        if changed:
            print("Tarave: RetroArch player order updated", file=sys.stderr)
    except (OSError, ValueError, ET.ParseError, RuntimeError) as error:
        print("Tarave: player order not applied: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
