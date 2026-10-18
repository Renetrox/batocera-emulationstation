# Tarave / RetroPie Runcommand integration (experimental)

Branch: `experiment/retropie-runcommand-bridge`.

## Overview

Tarave keeps its native launcher and emulator settings unless the
`TARAVE_USE_RETROPIE_RUNCOMMAND=1` environment variable is present **and**
the system has a RetroPie `emulators.cfg`.

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

### Launching

Set this variable in Tarave's *startup* environment (not RetroPie's):

```sh
TARAVE_USE_RETROPIE_RUNCOMMAND=1 batocera-es-test
```

If the installed frontend binary has a different name, use that name instead.
Leave the variable unset to restore the original frontend behavior.

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
2. Run Tarave with the environment toggle enabled.
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
8. Launch Tarave without the environment toggle and verify the native
   emulator/core menus and launching return unchanged.

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
- The C++ integration has **not** been compiled or smoke-tested on the
  Orange Pi yet. This branch is not merged into the original experiment.
