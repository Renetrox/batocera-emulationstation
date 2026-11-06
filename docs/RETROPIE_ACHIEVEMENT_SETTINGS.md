# Native RetroAchievements options for Tarave on RetroPie

The standalone **RetroAchievement Settings** menu now dispatches to a dedicated
RetroPie panel. It reads `/opt/retropie/configs/all/retroarch.cfg`, the global file
used by RetroPie/RetroArch. It does not enable the legacy frontend login/profile
API or write Batocera settings that Runcommand would ignore.

## Using the panel

- The configured global username is shown read-only. Configure the account and
  its credentials in RetroArch; this panel does not expose a password/token editor.
- Ten global options are available: achievements, hardcore, leaderboards,
  verbose notifications, rich presence, encore, automatic screenshots, challenge
  indicators, unofficial achievements and unlock sound.
- Each option has Default / On / Off. Default removes an explicitly changed key
  so RetroArch's normal default/inheritance applies. It does not assume the same
  defaults across RetroArch versions. Merely opening/saving an unchanged panel
  does not add keys.
- **Save** explicitly commits changes. **Back**, closing the menu and ordinary
  frontend settings saves do not commit these options.
- Per-system/core/game overrides or included configs may influence actual game
  settings. The panel edits only the direct global file, not those other files.
- Theme bindings cache achievement state; reload the game list after saving if
  the theme icon has not updated. Saving options does not establish login success,
  per-game achievement support or a working online profile.

## File handling

Only the ten allowlisted boolean keys are editable. Username, password, tokens,
all other keys and unrelated lines remain byte-for-byte unchanged. Changed keys
are normalized at the end of the file; duplicate definitions of changed keys are
removed. Unchanged explicit keys retain their original formatting. Inline comments
on a changed key are removed with that definition; unrelated comments remain.

The editor rejects missing, symlinked, hardlinked or read-only config files. It
uses no sudo and reports failure without silently changing file ownership. The
replacement is staged in the same directory, fsynced and atomically renamed,
preserving the original UID/GID, permission bits and Linux extended attributes
(including ACLs when present). If attributes cannot be preserved, saving fails
without replacing the original. The user therefore needs
both write permission on the config and permission to create/rename files in its
directory.

Before replacement a private `retroarch.cfg.tarave-achievements.bak` (mode 0600)
contains the previous full config. It can contain credentials and must not be
published. An unchanged save creates no backup. Concurrent content changes are
checked before staging and again before replacement; the user is asked to reopen
the menu on conflict. This is optimistic conflict detection, not a lock respected
by every external RetroArch/config editor. Avoid saving from both simultaneously.

## Validation

- `tests/test_tarave_achievement_config.cpp` compiles as C++11 and exercises
  duplicate keys, unchanged saves, forbidden keys/values, credential preservation,
  private backups, permissions, default restoration, stale snapshots, symlinks,
  hardlinks, read-only and missing files. All files are temporary fixtures.
- `tests/test_tarave_retropie_achievements.cpp` verifies existing read-only theme
  status handling.
- Standalone CI runs both before building the complete frontend.
- Hardware validation remains: configure account in RetroArch, change a global
  option in Tarave and explicitly save, verify in RetroArch/game, then change an
  option and Back out to confirm cancellation. Check per-core/game overrides
  when game behavior differs from the global panel.

Profile statistics, earned badges and the old credential-bearing login URL are
outside this panel. They remain separate work and are not activated by exposing
these native options.
