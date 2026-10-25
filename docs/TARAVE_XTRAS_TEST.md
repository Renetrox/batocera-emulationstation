# Experimental X-TRAS for Tarave on RetroPie

This integration is part of the **existing experimental Tarave branch** used by
its RetroPie-Extra installer; it is not merged into the upstream/default branch.

## What has been ported

Tarave uses **Batocera-ES's native Content Downloader interface** (tabs,
search, queue notifications, correct BUTTON_OK/BUTTON_BACK, theme-dependent
styling) to display the X-TRAS catalogue under
**Main menu → Updates & Downloads → X-TRAS**. Only the service backend changes;
Batocera's built-in themes downloader remains unchanged.

- Discover modules from RetroPie-Setup `scriptmodules/ports`, including
  compatible third-party modules in `ext/*/scriptmodules/ports`.
- Include the **Bezel Project** RetroPie-Extra supplementary module explicitly
  from `ext/*/scriptmodules/supplementary/bezelproject.sh`, when present.
  This triggers RetroPie-Setup's installer, **not** Batocera's bezel manager.
- The initial catalog `resources/xtras-free-games.ini` is copied from ES-X.
  Show only entries marked `ready=yes` and with a direct download URL.
- Download games into `$HOME/RetroPie/roms/<system>/`. Existing files are
  overwritten only after a successful nonempty download to a `.tarave-part` file.
  Removal requires GUI confirmation.
- Install and remove ports using the installed RetroPie-Setup module manager
  with `sudo -n`. A passwordless sudo setup is required to use these buttons;
  Tarave does not attempt an interactive password prompt inside the GUI.
- Store Tarave X-TRAS's logs in its **private** configuration folder. The
  optional user catalog override is
  `<Tarave private .emulationstation>/xtras/xtras-free-games.ini`.
  If absent, the bundled catalog is used. No ES-X installation is required.

**Progress (experimental test):** The native Content Downloader now receives
RetroPie-Setup installation stages from its captured output. When the active
CMake/make build prints `[ NN%]`, X-TRAS displays `COMPILANDO NN%` for **that
build stage only**, not a made-up overall port-installation percentage. Other
stages (dependencies, download, extraction, installation) use an indeterminate
indicator. Homebrew ROM downloads do not yet expose a live transfer percentage.
Output is also kept in Tarave's private `xtras/xtras.log`. Noninteractive
`sudo -n` authorization is still required for port installs; this is not a
replacement for interactive RetroPie-Setup. This does not add job cancellation.

**Limits:** The Bezel Project uses its own RetroPie utility. The service
looks up RetroPie-Setup using the OS login user's actual home directory,
not Tarave's private --home path. If ports still do not appear, check
`$HOME/RetroPie-Setup` and the paths set via `TARAVE_RETROPIE_SETUP` or
`RETROPIE_SETUP_DIR`, as well as Tarave's log messages prefixed `X-TRAS:`. This change does
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
3. The store's **PORTS** tab shows RetroPie-Setup and RetroPie-Extra ports.
4. The **HERRAMIENTAS** tab includes Bezel Project if RetroPie-Extra has
   registered its supplementary module.
5. A selected game's download appears in `$HOME/RetroPie/roms/<system>/`.
6. A/confirm and B/back follow the same mappings as the rest of Tarave,
   including switching tabs, confirming entries, dismissing dialogs and Back.
7. The original Themes downloader still works.
8. Ports require working `sudo -n true` before GUI installs.

Do not assume that a 4:3 overlay policy has been implemented: Tarave leaves
Bezel Project's own RetroPie setup and emulator config policies untouched.

## Rollback

To revert, install an older confirmed Tarave revision through the usual
RetroPie-Setup workflow, or restore the previously installed frontend entrypoint
using the module's supported restore procedure. A side-by-side installation
does not replace the default launcher. Original ROMs, Runcommand configs
and ES-X settings are not migrated.
Downloaded games remain in the user's ROM folders unless explicitly removed.
