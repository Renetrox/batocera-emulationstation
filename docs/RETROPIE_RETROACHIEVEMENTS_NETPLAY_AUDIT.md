# Tarave on RetroPie: RetroAchievements and Netplay integration audit

Status: **design/audit only; no gameplay or credential-handling changes enabled**.
This document describes the non-Batocera Runcommand build used by
`experiment/retropie-standalone-20261013`.

## Executive decision

**RetroPie/RetroArch is the runtime authority. Tarave supplies the user
interface, never a separate emulator configuration or a second netplay engine.**

Do not simply unhide Batocera's existing screens: they currently store settings
in Tarave's private `SystemConf` / `Settings` namespace, which is not the
same as the files RetroPie actually reads. The unmodified Netplay lobby
currently cannot reliably start a RetroPie-hosted or joined session.

Implement in separate, testable stages. Keep Batocera builds unchanged.

## Verified source paths and findings

### RetroAchievements

- Tarave's `GuiRetroAchievementsSettings.cpp` reads/writes settings including
  `global.retroachievements.*` through `SystemConf`.
- In the standalone non-Batocera build, `Paths.cpp` does not establish
  Batocera's `/userdata/system/batocera.conf`. When
  `mSystemConfFilePath` is empty, `SystemConf.cpp` proxies those settings
  to Tarave's private `Settings`, **not** RetroPie's RetroArch configuration.
- The RetroAchievements menu is gated through
  `ApiSystem::RETROACHIVEMENTS`, which currently returns true for that
  script ID only under the optional `CHEEVOS_DEV_LOGIN` macro. The normal
  Linux build doesn't set this by default.
- Tarave's own user-summary/hash UI can be useful independently, but its
  account login flow and API token are not interchangeable with RetroArch's
  credential/token storage. In particular `RetroAchievements::testAccount`
  currently sends the entered password as a URL query parameter to its
  legacy request endpoint. Do **not** adopt that flow for the RetroPie bridge.
- RetroPie documents the global file
  `/opt/retropie/configs/all/retroarch.cfg`; not all emulators support
  achievements, only appropriate libretro cores do.

Recommended supported mapping for a first native RetroPie-facing panel:

| Tarave concept | RetroArch key |
| --- | --- |
| Enabled | `cheevos_enable` |
| Username | `cheevos_username` |
| Password | `cheevos_password` |
| Hardcore | `cheevos_hardcore_mode_enable` |
| Leaderboards | `cheevos_leaderboards_enable` |
| Verbose notifications | `cheevos_verbose_enable` |
| Rich presence | `cheevos_richpresence_enable` |
| Encore | `cheevos_start_active` |
| Automatic screenshot | `cheevos_auto_screenshot` |
| Challenge indicators | `cheevos_challenge_indicators` |
| Unofficial achievements | `cheevos_test_unofficial` |

Use a boolean for `cheevos_unlock_sound_enable` if later exposing the sound
option; Tarave's Batocera custom sound-name selector is **not** equivalent.
Tarave-only visual toggles (e.g. showing a main-menu entry or indexing on
startup) remain in the private frontend settings, not in RetroArch.

### Netplay

- `GuiNetPlaySettings.cpp` uses Tarave's private
  `global.netplay.*` keys; RetroPie Runcommand doesn't read them.
- `GuiNetPlay.cpp` resolves games and compatible cores from Batocera-style
  `SystemData::mEmulators` and launches with a `LaunchGameOptions`
  netplay payload.
- `FileData.cpp::getlaunchCommand` returns early for Runcommand-backed
  systems by invoking
  `/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ SYSTEM ROM`.
  Hence Batocera-specific netplay options in `LaunchGameOptions` are
  **not** translated into RetroPie arguments.
- `SystemData::isNetplayActivated()` depends on emulator/core feature
  metadata; the stock RetroPie `es_systems.cfg` typically doesn't expose
  Batocera's core Netplay declarations. A hidden lobby is therefore expected.
- `GuiMenu.cpp` additionally gates the existing Netplay settings via
  `ApiSystem::NETPLAY`, whose current availability check looks for `7zr`.
  Installing a decompression program is not a valid RetroPie Netplay test.
- RetroPie-Setup's `retronetplay.sh` stores host/client, host IP, port and
  nickname in `/opt/retropie/configs/all/retronetplay.cfg`.
  Its `runcommand.sh` exposes **Z: Launch with netplay enabled** for a
  libretro emulator, then reads that config to append appropriate RetroArch
  arguments.
- Tarave's existing independent RetroPie menu/bootstrap includes the
  `retronetplay.rp` entry when the corresponding RetroPie shortcut is present.
  This is the *working* entrypoint today, including on a TTY.

**Important:** Runcommand sets `NETPLAY=0` inside its normal argument parser
and turns it on via the Z launch-menu action. Exporting `NETPLAY=1` from the
Tarave process or blindly appending Batocera's `-netplaymode` options to the
Runcommand invocation does not provide a reliable equivalent.

### Configuration and security

- The RetroPie config files can be user-owned or root-owned; the GUI must
  detect writability and report failures, not silently escalate via `sudo`.
- Treat RetroAchievements credentials/tokens as secrets. Never echo values
  to logs, include them in exceptions, print them in test fixtures, or copy
  credentials into Tarave's normal frontend configuration or gamelists.
- A safe config editor must preserve unrelated lines, comments, quotes,
  existing auth tokens and any core-specific overrides. Write **only changed
  keys**, take a private backup, use atomic same-directory replace, and
  preserve ownership/permissions. Password fields remain masked and unchanged
  unless explicitly edited.
- RetroPie's `retronetplay.cfg` is a *sourced shell fragment*. Never write
  arbitrary untrusted names, hostnames, command substitutions or shell
  metacharacters into it. A native editor requires strict validation/quoting
  and tests. Avoid changing the global RetroPie netplay file merely to join
  a one-off external lobby.
- Do not touch `~/.emulationstation`, `/userdata`, RetroPie's Runcommand
  scripts, or ES-X settings; the frontends coexist.
- RetroArch may use per-system/per-core overrides in addition to the global
  config. Display the actual source of a setting when applicable.

## Recommended implementation sequence

### 0. Preserve the working fallback (no code changes)

Keep **RetroPie → RetroArch** for achievements and **RetroPie → RetroArch Net
Play** for host/client settings. For a game using an `lr-*` emulator,
Runcommand's launch dialog offers **Z** to start Netplay. Never show a
Tarave-native Netplay action that will silently launch an offline game.

### 1. Native RetroAchievements settings, read-through then safe write

Create a focused `RetroPieRetroArchConfig` helper in the non-Batocera
frontend; it reads the real global `retroarch.cfg` and maps only the keys
above. First prove read-only display and unchanged file on cancel. Then
support explicit saves using an atomic, permission-preserving editor.
Dispatch `GuiMenu::openRetroachievementsSettings` to the RetroPie variant
when `RetroPieRuncommand::enabled()`. Do **not** turn on
`CHEEVOS_DEV_LOGIN` as a workaround. Defer Tarave's own API profile screen
until account authentication is carefully separated from emulator config.

### 2. Native RetroPie Netplay *settings*, not a false lobby

Use a separate RetroPie-specific settings adapter that reads existing
`retronetplay.cfg` values (H/C, port, host address, nickname). Validate
inputs before writing the RetroPie-owned file. Explain in the UI that the
Runcommand **Z** action is currently required when launching a libretro game.
Keep Batocera native settings for Batocera builds only. When the config file
or a compatible libretro install is missing, leave a useful explanation and
access to the original RetroPie dialog.

### 3. Optional native lobby after proven end-to-end launch support

Only expose **Join / Host / Spectate** in Tarave's lobby once tests demonstrate
a real Runcommand/RetroArch command bridge with matching selected `lr-*`
core, game CRC/content, version, session, and IP/port. Do not modify
RetroPie-Setup's global Runcommand file just to make UI buttons clickable.
Prefer an upstream-supported explicit per-launch mechanism or a narrowly
isolated, opt-in wrapper that maintains Runcommand configuration resolution.
Preserve the official RetroArch lobby as an alternative. Test normal launches
after any Netplay experiment.

## Acceptance tests before exposing any new control

1. Linux desktop build and CI tests pass with no change to Batocera mode.
2. With a fixture `retroarch.cfg`, read every mapped flag; cancel causes
   zero file writes; saving one flag changes only that flag.
3. Existing comments, aliases, core settings and `cheevos_token` survive;
   credentials and passwords never appear in debug logs.
4. Read-only/root-owned config yields a helpful error without corruption or
   an unattended permission escalation.
5. Existing `retronetplay.cfg` is faithfully parsed (including quoting);
   invalid host/nickname/port cannot become shell content.
6. RetroPie and Tarave views agree after a real edit made in RetroArch or
   the RetroPie dialog.
7. On Orange Pi 4A, an `lr-*` game launches normally; achievements work
   with the corresponding core, and Runcommand **Z** host/client works in
   at least one real controlled session.
8. A normal non-libretro emulator (e.g. standalone N64) remains unaffected.
9. Theme management, X-TRAS, gamepad input and the separate ES-X install
   remain unchanged.

## Upstream sources

- https://github.com/RetroPie/RetroPie-Docs/blob/master/docs/RetroAchievements.md
- https://github.com/RetroPie/RetroPie-Setup/blob/master/scriptmodules/supplementary/retronetplay.sh
- https://github.com/RetroPie/RetroPie-Setup/blob/master/scriptmodules/supplementary/runcommand/runcommand.sh
- https://github.com/RetroPie/RetroPie-Setup/blob/master/scriptmodules/supplementary/retropiemenu.sh
- https://github.com/libretro/RetroArch/blob/master/retroarch.cfg
- https://docs.libretro.com/guides/netplay-getting-started/
