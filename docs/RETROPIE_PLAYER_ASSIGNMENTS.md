# Tarave → RetroPie player assignments (experimental)

The installer in **RetroPie-Extra** tracks `experiment/retropie-standalone-20261013`.
This bridge is intended for that non-Batocera build and is not an alternative
emulator launcher. **Runcommand remains authoritative**.

## What connects

Tarave already lets the user select named controllers for P1, P2, etc.
in `GuiControllersSettings.cpp`. It stores the selected controller name,
GUID, and physical path in the **private Tarave** `es_settings.cfg`.
These choices previously affected only Tarave's frontend-side player order.

Before invoking the original Runcommand `_SYS_` launch, Tarave now invokes a
small helper at `resources/retropie-player-order.py`:

- **Only if a player was explicitly assigned:** inspect connected SDL2
  controllers, prioritize the saved physical path, then GUID/name.
- Synchronize the resolved positions with
  `/opt/retropie/configs/all/retroarch.cfg` using
  `input_playerN_joypad_index`, without changing buttons, hotkeys, or
  autoconfigs.
- Maintain only a clearly marked, removable Tarave block; leave existing
  manually defined player-index keys untouched. Skip if RetroPie's
  joystick-selection Runcommand hook is present.
- Detect duplicate indistinguishable gamepad names and fail safely.
- If assignments return to **DEFAULT**, remove the Tarave-managed block at
  the next game launch.
- **Failure is nonfatal:** even if SDL, permissions, or the config are
  unavailable, the original Runcommand launch still runs.

The global RetroArch config is **shared by other RetroPie frontends**,
including ES-X. This feature deliberately applies a RetroPie-wide controller
order after a user explicitly chooses a slot in Tarave. Do not activate it
if separate RetroArch controller orders are required between frontends.
No automatic writes occur for default/empty player assignments.

## Scope and limitations

- RetroArch/libretro emulators only; standalone emulators retain their own
  controller ordering.
- The helper uses SDL's index enumeration, as established by the existing
  RetroPie joystick-selection add-on. On devices where RetroArch's selected
  joypad driver enumerates devices in a different order, verify and adjust
  it **on the hardware**; a successful build alone does not prove matching.
- System/core/ROM-specific RetroArch configs may override global settings.
- The global RetroArch config must exist, be a regular file (not a symlink),
  and be writable by the login user. Tarave does **not** invoke sudo.
- An existing `input_playerN_joypad_index` setting or
  joystick-selection hook takes precedence. No overwrite is attempted.
- This does not install Bluetooth, joystick drivers, or OS-wide services.

## Safety switch

Set `TARAVE_RETROPIE_PLAYER_ORDER=0` when launching Tarave to **disable**
synchronization. On the next RetroPie game launch the helper also removes
its own previously managed block (if present), leaving other settings intact.
The setting is not a substitute for a backup of user-customized configs.

## Hardware smoke test

1. Connect two distinguishable pads. Assign a different P1/P2 order in
   Tarave's controller menu and exit the menu to save.
2. Start a libretro game through Runcommand; verify player order in-game.
3. Inspect only the marked block in `/opt/retropie/configs/all/retroarch.cfg`.
4. Disconnect/reconnect in the opposite order and start the same game again.
5. Change both Tarave assignments to DEFAULT; start a game and confirm the
   block has disappeared and unrelated RetroArch settings remain.
6. Launch an ordinary standalone emulator and confirm it still works.

## Automated tests

```sh
python3 -m unittest discover -s tests -p test_retropie_player_order.py -v
```

Tests cover player preference resolution, reconnection, cleanup, duplicate
names, pre-existing manual values, third-party hooks and symlink safety.
