# Tarave / RetroPie Runcommand bridge (experimental)

Branch: `experiment/retropie-runcommand-bridge`.

Tarave normally executes the launch command from `es_systems.cfg` (or
a matching emulator/core override). This is preserved by default.

## Opt-in

Build this branch, then launch Tarave with:

```sh
TARAVE_USE_RETROPIE_RUNCOMMAND=1 batocera-es-test
```

Set the variable in the **Tarave startup environment** if a wrapper starts
the frontend. It is not a global RetroPie setting. Leave it unset to restore
the original launch path.

When enabled, Tarave uses:

```sh
/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ SYSTEM ROM
```

for systems that have both the installed Runcommand script and
`/opt/retropie/configs/SYSTEM/emulators.cfg`. It passes an escaped ROM
path and the original RetroPie system ID, and waits for Runcommand to exit
before reinitializing the Tarave window.

When these files are unavailable, or the system name cannot be safely
used as a shell argument, the original system command is retained.
This allows custom commands, ports and non-RetroPie setups to continue
working.

## What this bridges

- Uses the RetroPie system's `emulators.cfg` and its default emulator.
- Allows the ordinary Runcommand launch dialog to choose an alternative.
- Retains the current game-start/game-end lifecycle in Tarave.
- Does not overwrite `es_systems.cfg`, RetroPie settings, or gamepads.
- Avoids invoking the Batocera emulator launcher on RetroPie systems.

## What it does NOT do

This does *not* synchronize Tarave's in-menu emulator/core selection with
RetroPie's `emulators.cfg`. A Tarave core or emulator selection for a
Runcommand-backed system is ignored while this bridge is enabled.
Treat Tarave's own emulator menu as out-of-scope for this initial test.

## Smoke test on the Orange Pi

1. Ensure the chosen system has
   `/opt/retropie/configs/SYSTEM/emulators.cfg` and that Runcommand exists.
2. Start the rebuilt frontend with
   `TARAVE_USE_RETROPIE_RUNCOMMAND=1`.
3. Launch a ROM under that system. The Tarave log should include
   `Tarave: launching SYSTEM with RetroPie runcommand`.
4. If Runcommand fails, examine `/dev/shm/runcommand.log`.
5. Verify the game exits back to Tarave, input still works, and that
   the selected emulator in Runcommand is respected.
6. Test one system that lacks `emulators.cfg` to confirm the original
   command is retained.
7. Relaunch with the variable unset to compare original behavior.

This is source-level and static-reviewed only; it has not yet been compiled
or smoke-tested on the Orange Pi hardware.
