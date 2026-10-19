# Tarave: RetroPie installation audit and independent resource layout

Target: `batocera-es-test` in `Renetrox/RetroPie-Extra` experimental branch.
This is a **RetroPie module**, not yet a generic Debian package or an
independent emulator-discovery backend. Tarave is independent of ES-X, not of
RetroPie when using Runcommand.

## Comparison with official EmulationStation (RetroPie-Setup)

| Official `emulationstation.sh` | Tarave `batocera-es-test.sh` |
| --- | --- |
| Installs executable and `resources/` | Own executable, `resources/`, shaders, fonts and `locale/` |
| Installs a default Carbon theme via `esthemes` in global `/etc/emulationstation/themes` | Keeps users' theme choice, uses installed RetroPie theme if available, otherwise seeds a tiny offline theme in Tarave's private folder |
| `moveConfigDir` binds `~/.emulationstation` to `/opt/retropie/configs/all/emulationstation` | **Never** moves, replaces or links the main `~/.emulationstation` directory; uses `~/.local/share/batocera-es-test/.emulationstation` |
| RetroPie system catalog and runcommand | Read-only symlink from private Tarave config to `/opt/retropie/configs/all/emulationstation/es_systems.cfg` if present; otherwise system catalog from `/etc/emulationstation` |
| RetroPie `retropiemenu` gamelist generated in global RetroPie config (names, descriptions, absolute PNG icons) | At configure time imports missing files from previous `gamelists/` (Wine, Kodi, Ports and all systems), then merges official RetroPie Setup menu metadata into Tarave's **private** `gamelists/retropie/gamelist.xml`. User edits and old files are retained. |
| Installs input configuration hooks and configurators | Native controller configuration stays private. Its explicit bridge uses stock RetroPie configurators when available; does not change/overwrite ES-X `es_input.cfg`. |
| Owns `/usr/bin/emulationstation`, RetroPie desktop entry | `/usr/local/bin/batocera-es-test`, separate desktop entry; optional user-requested switch to default with previous launcher backup and rollback |
| EmulationStation uses RetroPie-provided shell launch wrapper | Tarave invokes its installed executable with isolated `--home` and preserves original command args; standalone restart re-execs itself |
| Retains `README`, themes and metadata docs | Packages user docs, resources, locale, scripts and original font licenses |

## Installation paths

- Binary/resources: `/opt/retropie/supplementary/batocera-es-test/`.
- CLI: `/usr/local/bin/batocera-es-test`.
- Settings, downloaded themes, gamelists, input and music:
  `~/.local/share/batocera-es-test/.emulationstation/`.
- Shared RetroPie ROMs: `~/RetroPie/roms/`.
- Shared RetroPie emulators and Runcommand: `/opt/retropie/`.
- Global system definitions: `/etc/emulationstation/es_systems.cfg`.
- User RetroPie system overrides, when configured:
  `/opt/retropie/configs/all/emulationstation/es_systems.cfg`.

Do not use `moveConfigDir`, `configure_emulationstation`, or the
`esthemes` install function directly in the Tarave module: they are intended
for the main RetroPie frontend and can alter ES-X's directories, controllers,
or default theme.

## Previous RetroPie gamelists and missing system definitions

On installation/configuration, the Tarave module copies **all missing regular
files** in previous `~/.emulationstation/gamelists/` and
`/opt/retropie/configs/all/emulationstation/gamelists/` into the Tarave private
folder. It never overwrites existing files. Symlinked individual files and
directories are skipped for safety; the main legacy folder may be a RetroPie
symlink. A clean installation with no prior gamelists still tries to import
`gamelists/retropie/gamelist.xml` from the installed RetroPie menu, including
the RetroPie Setup entry and PNG icon paths.

Only **at install/configure time** (not on every frontend launch), Tarave
reads the older `es_systems_custom.cfg` and `es_systems.cfg` to import
missing complete system definitions, not just Wine/Kodi; custom names in
the base RetroPie system catalog remain authoritative. It writes only:
`~/.local/share/batocera-es-test/.emulationstation/es_systems_legacy_import.cfg`.
If the private file already exists, additional missing definitions may be
merged, but existing user-defined entries are never replaced.

Run `batocera-es-test --sync-gamelists` to refresh all missing gamelists
without rebuilding Tarave, or `--sync-retropie-menu` for just the RetroPie
Setup metadata. Use `batocera-es-test --import-legacy-systems` to refresh
missing user systems. All three commands preserve the original source files.

The frontend prefers **private gamelists first** and writes metadata there;
if no private file exists for a system it can still read an existing ROM-folder
gamelist. This separation does not duplicate ROMs or emulators.

`batocera-es-test --retropie-menu-check` checks existing official RetroPie
configuration-menu shortcuts. It makes no changes. The bundled
`scripts/tarave-retropie-menu.sh --configure` is an optional explicit
RetroPie-side action requiring administrator permissions; it is **not** run
during Tarave installation.

## Remaining release gates

- Full native TTY/DRM/EGL validation on Orange Pi 4A (desktop X11 build does
  not automatically prove headless GLES2 compatibility).
- Verify Wine/Kodi launch on supported systems with their actual launch scripts
  installed and test the private optional importer.
- Physical controller validation (especially unusual Bluetooth gamepads),
  without installing Sixaxis/sixad or replacing drivers.
- Compare RAM, VRAM, startup and input latency against ES-X.
- For a generic *Debian-without-RetroPie* package, ship separate editable
  system definitions and launch-command configuration that do not depend on
  `/opt/retropie`; this is a different packaging target.
- Rename the public command/data directory only with an explicit migration
  plan; never silently discard existing `batocera-es-test` user data.

The official RetroPie package's `inputconfiguration.sh` and optional
retropiemenu system remain owned by RetroPie. Tarave must reuse public
interfaces, not copy or overwrite those global resources.
