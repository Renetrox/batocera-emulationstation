# Experimental X-TRAS for Tarave on RetroPie

This is a **test branch**, not a replacement for the active Tarave release.

## What has been ported

The X-TRAS browser from `Renetrox/EmulationStation-X` is exposed as
**Main menu → Updates & Downloads → X-TRAS** in the standalone, non-Batocera
RetroPie build. Batocera's built-in themes downloader remains unchanged.

- Discover modules from RetroPie-Setup `scriptmodules/ports`, including
  compatible third-party modules in `ext/*/scriptmodules/ports`.
- Include the **Bezel Project** RetroPie-Extra supplementary module explicitly
  from `ext/*/scriptmodules/supplementary/bezelproject.sh`, when present.
  This triggers RetroPie-Setup's installer, **not** Batocera's bezel manager.
- The initial catalog `resources/xtras-free-games.ini` is copied from ES-X.
  Show only entries marked `ready=yes` and with a direct download URL.
- Download games into `$HOME/RetroPie/roms/<system>/`. Existing files are
  overwritten only after a successful nonempty download to a `.part` file.
  Removal requires GUI confirmation.
- Install and remove ports using the installed RetroPie-Setup module manager
  with `sudo -n`. A passwordless sudo setup is required to use these buttons;
  Tarave does not attempt an interactive password prompt inside the GUI.
- Store Tarave X-TRAS's logs in its **private** configuration folder. The
  optional user catalog override is
  `<Tarave private .emulationstation>/xtras/xtras-free-games.ini`.
  If absent, the bundled catalog is used. No ES-X installation is required.

**Limits:** The Bezel Project uses its own RetroPie utility. This change does
**not** add Batocera's automatic 4:3 bezel hiding; aspect-ratio policies require
a separate emulator-side integration. The browser does not install the
Batocera content store or change Runcommand.

## Install and test via the existing RetroPie-Extra module

The source is part of the **active Tarave experiment**:
`experiment/retropie-standalone-20261013`. The existing RetroPie-Extra
module `experiment/batocera-es-standalone-module-20261013` already
points to that source branch. No separate installer source branch is needed.
**Do not switch Git branches to install X-TRAS.**

From the normal login account on the RetroPie computer (not root):

```bash
test -f "$HOME/RetroPie-Setup/ext/RetroPie-Extra/scriptmodules/supplementary/batocera-es-test.sh"
grep '^rp_module_repo=' "$HOME/RetroPie-Setup/ext/RetroPie-Extra/scriptmodules/supplementary/batocera-es-test.sh"
cd "$HOME/RetroPie-Setup"
sudo -v
sudo env TARAVE_INSTALL_SIDE_BY_SIDE=1 \
  ./retropie_packages.sh batocera-es-test _source_
```

The module must already be registered in RetroPie-Setup. If the paths above
are different, first locate the existing module checkout, do not clone or
replace a user's RetroPie-Extra installation blindly. The source installer
compiles and installs the updated frontend while preserving the ordinary
RetroPie EmulationStation launcher when side-by-side mode is requested.
The `tarave-install` helper is optional and may not exist on an installation
that has never completed the Tarave configure step.

Then start `batocera-es-test` and check:
1. **Updates & Downloads → X-TRAS** is visible.
2. Licensed `ready=yes` homebrew entries appear without requiring ES-X.
3. RetroPie-Setup ports are listed.
4. Bezel Project appears if RetroPie-Extra has registered its supplementary module.
5. A selected game's download appears in `$HOME/RetroPie/roms/<system>/`.
6. The original Themes downloader still works.
7. Ports require working `sudo -n true` before GUI installs.

Do not assume that a 4:3 overlay policy has been implemented: Tarave leaves
Bezel Project's own RetroPie setup and emulator config policies untouched.

## Rollback

To revert, install an older confirmed Tarave revision through the usual
RetroPie-Setup workflow, or restore the previously installed frontend entrypoint
using the module's supported restore procedure. A side-by-side installation
does not replace the default launcher. Original ROMs, Runcommand configs
and ES-X settings are not migrated.
Downloaded games remain in the user's ROM folders unless explicitly removed.
