#!/usr/bin/env python3
"""Explicit, one-time import of selected systems into Tarave's PRIVATE catalog.

Never modify the source EmulationStation/ES-X XML, RetroPie's system catalog,
or existing Tarave user files. The default list is intentionally small:
optional systems sometimes defined only in a user's legacy config.
"""
import argparse
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

DEFAULT_SYSTEMS = ("wine", "kodi")
SOURCE_NAMES = ("es_systems_custom.cfg", "es_systems.cfg")


def parse_systems(path):
    if not path.is_file():
        return []
    document = ET.parse(path)
    if document.getroot().tag != "systemList":
        raise ValueError(f"Expected <systemList> in {path}")
    return [node for node in document.getroot().findall("system")]


def system_id(node):
    return (node.findtext("name") or "").strip().lower()


def import_systems(source_home, target_cfg, shared_catalog, names=DEFAULT_SYSTEMS):
    source_home = Path(source_home)
    target_cfg = Path(target_cfg)
    wanted = set(names)
    if not wanted or any(not item.isalnum() for item in wanted):
        raise ValueError("Invalid system selection")
    if target_cfg.is_symlink() or target_cfg.exists():
        raise FileExistsError(f"Refusing to replace existing Tarave file: {target_cfg}")

    base_ids = set()
    if shared_catalog and Path(shared_catalog).is_file():
        base_ids = {system_id(node) for node in parse_systems(Path(shared_catalog))}

    definitions = {}
    for filename in SOURCE_NAMES:
        path = source_home / ".emulationstation" / filename
        for node in parse_systems(path):
            name = system_id(node)
            if name not in wanted or name in base_ids or name in definitions:
                continue
            if not all((node.findtext(x) or "").strip() for x in ("path", "extension", "command")):
                continue
            definitions[name] = node

    if not definitions:
        return []

    # Only after successful parsing create the destination, exclusively.
    # No replace(), symlink following, or writes to the old frontend.
    target_cfg.parent.mkdir(parents=True, exist_ok=True)
    root = ET.Element("systemList")
    for node in definitions.values():
        root.append(node)
    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    fd = os.open(str(target_cfg), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
    except BaseException:
        target_cfg.unlink(missing_ok=True)
        raise
    return sorted(definitions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-home", default=str(Path.home()))
    parser.add_argument("--destination", required=True)
    parser.add_argument("--catalog", default="/etc/emulationstation/es_systems.cfg")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as your regular user, not root")
    try:
        imported = import_systems(args.source_home, args.destination, args.catalog)
    except (OSError, ValueError, ET.ParseError) as exc:
        parser.error(str(exc))
    if imported:
        print("Tarave: imported " + ", ".join(imported) + " to " + args.destination)
        print("Restart Tarave to load these systems. No existing file was changed.")
    else:
        print("Tarave: no additional Wine/Kodi system definitions to import.")


if __name__ == "__main__":
    main()
