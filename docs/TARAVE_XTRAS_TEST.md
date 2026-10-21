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

## How to test the branch

The active source branch remains
`experiment/retropie-standalone-20261013`.

To opt in, the corresponding *separate* RetroPie-Extra module branch is
`experiment/tarave-xtras-module-20261021`, which points at
`experiment/tarave-xtras-20261021` in the Tarave source repository.
Switch to that branch in your existing RetroPie-Extra checkout **only
for the test**, then use your normal `tarave-install` installer.

For a side-by-side install that does not replace the normal RetroPie frontend
entrypoint, use `TARAVE_INSTALL_SIDE_BY_SIDE=1` with your installation
command; it still updates Tarave's own installed binary.

Example, adjusting the path to the RetroPie-Extra checkout you actually use:

```bash
cd ~/RetroPie-Setup/ext/RetroPie-Extra
git fetch origin experiment/tarave-xtras-module-20261021
git switch --track origin/experiment/tarave-xtras-module-20261021
TARAVE_INSTALL_SIDE_BY_SIDE=1 tarave-install
```

The path and remote must be checked locally; some RetroPie setups have the
module checked out under a differently named `ext/` folder.

When installed, open **Updates & Downloads → X-TRAS** and verify:
1. Homebrew catalog entries appear even if RetroPie-Setup cannot be found.
2. Entries from RetroPie-Setup and RetroPie-Extra ports are shown.
3. Bezel Project is shown if RetroPie-Extra's supplementary module is present.
4. A `ready=yes` game downloads and is detected under its ROM directory.
5. Installed content is removable only after confirmation.
6. The original Themes downloader still works.

Do **not** test automated port installs unless `sudo -n true` works and
you intend to install/update that software.

## Rollback

Switch the RetroPie-Extra checkout back to its previous branch
(`git switch -` if that is the original branch), then reinstall the
stable Tarave source through `tarave-install`.

The experimental source branch is not merged into the active installer target.
Original ROMs, Runcommand configs and ES-X settings are not migrated.
Downloaded games remain in the user's ROM folders unless explicitly removed.
