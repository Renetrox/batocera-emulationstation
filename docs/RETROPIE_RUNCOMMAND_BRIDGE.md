# Tarave / RetroPie Runcommand integration (experimental)

Source branch consumed by the unchanged RetroPie-Extra installer:
`experiment/retropie-standalone-20261013`.

## Overview

When built by the existing RetroPie-Extra installer (non-Batocera mode), Tarave
automatically uses Runcommand if the script is present and the system has a
RetroPie `emulators.cfg`. The install module does not need changes.
The environment setting `TARAVE_USE_RETROPIE_RUNCOMMAND=0` explicitly turns
the bridge **off**. `=1` forces it **on** for tests.

For configured systems Tarave:
- launches via `/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ SYSTEM ROM`;
- reads available emulator IDs from `/opt/retropie/configs/SYSTEM/emulators.cfg`;
- displays and writes the system-level `default` emulator there;
- reads and writes game overrides in `/opt/retropie/configs/all/emulators.cfg`
  using Runcommand's `clean_name("${SYSTEM}_${ROM_BN}")` convention;
- hides *unconnected* Batocera emulator/core/advanced-feature options from
  Runcommand-backed system and game menus, including save-state-manager
  launches and Batocera-specific netplay commands not handled by Runcommand;
- suppresses the unrelated global Batocera game-settings screen and hides
  emulator/core metadata-editor selectors for Runcommand-backed games;
- keeps separate settings for systems without a RetroPie config, as well as
  gamepad settings, scraper, themes, and the normal game lifecycle.

No RetroPie configuration is touched merely by opening Tarave or an options
menu. Writing occurs when a *different* emulator is selected. Changes preserve
other emulator entries and comments, and use a same-directory atomic rename.
The `AUTO` option in per-game settings removes the ROM-specific override so
that Runcommand inherits the system setting.

## RetroPie settings menu (Bluetooth, Runcommand, RetroPie Setup)

The `retropie` carousel system comes from RetroPie-Setup's official
`retropiemenu` package, **not** from EmulationStation or Runcommand.
It creates `~/RetroPie/retropiemenu/*.rp` shortcuts and a corresponding
entry in the EmulationStation systems list.

In RetroPie mode, Tarave now imports the **already installed** menu into
the *in-memory* systems list when its usual systems configuration does not
contain `retropie`. It requires both
`~/RetroPie/retropiemenu/rpsetup.rp` and
`~/RetroPie-Setup/retropie_packages.sh`. It never writes to the user's
system XML and does not duplicate an existing entry.

Check its installation:

```sh
bash scripts/tarave-retropie-menu.sh --check
```

If RetroPie-Setup is already installed but the menu shortcuts are missing,
the user may **explicitly** configure the original module:

```sh
bash scripts/tarave-retropie-menu.sh --configure
```

This invokes `retropie_packages.sh retropiemenu configure`. It does not
install `sixaxis`, `sixad`, or new Bluetooth drivers. Bluetooth settings
opened *by the user* within RetroPie are otherwise managed by RetroPie
as usual.

RetroPie settings shortcuts (`.rp`) must **not** be routed through the
generic `_SYS_` Runcommand launcher; nor should ports (`_PORT_` semantics
are different). The bridge excludes system names `retropie` and `ports`.

### Launching

The unchanged RetroPie-Extra installer launches Tarave normally:

```sh
batocera-es-test
```

The Runcommand bridge is detected automatically. To compare with Tarave's
original behavior, use:

```sh
TARAVE_USE_RETROPIE_RUNCOMMAND=0 batocera-es-test
```

Do not add export statements to the installer or modify its launch script.

### Verification

The backend is header-only and has a standalone C++ regression test:

```sh
g++ -std=c++11 -Wall -Wextra -pedantic \
    tests/test_retropie_runcommand_bridge.cpp -o /tmp/tarave-runcommand-test
/tmp/tarave-runcommand-test
```

A local build using the existing Tarave build script, followed by hardware
testing on the Orange Pi, is **still required**.

1. Inspect `/opt/retropie/configs/n64/emulators.cfg` and confirm the usual
   default and installed emulator IDs are present.
2. Run Tarave with the unchanged `batocera-es-test` launcher.
3. Open **Emulator Settings → Nintendo 64**. Select a different ID, close,
   and confirm only `default = "..."` changed in the N64 `emulators.cfg`.
4. Open a game's **Advanced Game Options**, choose a different emulator, close,
   and inspect `/opt/retropie/configs/all/emulators.cfg` for the ROM key.
5. Reopen the game menu and choose **AUTO**; the override key should disappear,
   leaving the system default intact.
6. Launch the ROM, check Runcommand's selected emulator and menu, exit, and
   verify Tarave returns with working input and sound.
7. Launch a system without a RetroPie `emulators.cfg` and verify the
   original Tarave command still works.
8. Launch Tarave with `TARAVE_USE_RETROPIE_RUNCOMMAND=0` and verify that
   native emulator/core menus and launching return unchanged.

### Boundaries

- Runcommand is the **sole authority** for emulator selection on a configured
  RetroPie system. Tarave does not translate its own Batocera core list.
- Advanced Batocera video, shader, autosave and emulator-feature settings are
  hidden for Runcommand-backed systems. Any equivalent functionality remains
  configurable through RetroPie or the emulator's own configuration.
- Settings for systems **not** backed by Runcommand remain native to Tarave.
- Per-ROM keys follow Runcommand's filename-derived convention. ROMs with
  identical sanitized stems in a single system share a key by Runcommand
  design; Tarave cannot disambiguate them without changing Runcommand.
- Port launchers and systems with nonstandard Runcommand layouts may need a
  separate adapter. The current adapter uses `_SYS_`, not `_PORT_`.
- If an `emulators.cfg` file has no valid emulator IDs, the GUI presents an
  error instead of inventing entries.
- The standalone C++ backend test is covered by CI, but the **full frontend**
  still needs compilation and smoke testing on the Orange Pi. The RetroPie
  installer script stays unchanged.
