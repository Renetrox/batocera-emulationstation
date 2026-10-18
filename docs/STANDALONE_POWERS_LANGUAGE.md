# Standalone RetroPie menus, reboot and languages

This applies to the existing `experiment/retropie-standalone-20261013`
source branch consumed by the **unchanged**
`RetroPie-Extra/scriptmodules/supplementary/batocera-es-test.sh` installer.

## Quit / restart / power

* **Quit EmulationStation** exits Tarave, preserving the original RetroPie
  frontend and its shell/desktop.
* **Restart EmulationStation** (standalone Linux only) gracefully saves metadata,
  closes SDL and re-execs the same running binary using `/proc/self/exe` with
  its original arguments (including the installer's isolated `--home`).
  It does not require a Batocera supervisor or a `/tmp/restart.please` flag.
* **Restart system / Shutdown system / Fast shutdown** request the action
  through `systemctl --no-ask-password reboot|poweroff`, after normal shutdown
  and metadata saving. Fast shutdown retains its explicit skip-save semantics.
  Existing local systemd-logind/polkit permissions apply. Tarave does **not**
  install sudoers rules, enable unauthenticated root privileges, or modify
  Bluetooth drivers.
* A missing `systemctl` is reported in the UI. Permission rejection after
  exiting is recorded in the frontend log. If reboot or shutdown still fails,
  verify `systemctl reboot` / `systemctl poweroff` under the same user account,
  but **do not** run those commands merely to diagnose without intending to
  reboot/power off.

## Language on desktop Linux

The original Linux build required gettext development tools and pointed to
system locale catalogs, although the unchanged installer distributes raw
`locale/lang/<language>/LC_MESSAGES/emulationstation2.po` alongside the
executable. This made `Language` settings ineffective on some Debian setups.

The non-Batocera, non-Retrobat Linux build now reuses Tarave's existing PO
runtime parser, previously used on Windows. It finds Spanish `es` catalogs
when the user selects `es_ES`, supports other shipped languages, and reloads
when `Settings.Language` changes. No gettext installation or new installer
steps are needed for runtime translations. Theme-authored hard-coded text may
remain English independently of menu translations.

## Verification

On the installed frontend:

1. Choose `System Settings → Language → Español` and close/reopen the menu.
   Menu headings such as `QUIT` should translate.
2. Choose `Quit → Restart EmulationStation` and confirm: Tarave should return
   with the same config and games.
3. Only if you intend to turn off/reboot the computer, test those power
   actions and note any permission errors. The original ES-X frontend is
   not affected.
4. Test a normal RetroPie Runcommand ROM and return to Tarave, to confirm the
   frontend restart and menu changes don't interfere with launching.

Build regression CI: `.github/workflows/build-tarave-standalone.yml`.
Standalone source checks: `tests/test_tarave_standalone_menus.py`.
The Ubuntu desktop CI build is **not** an Orange Pi hardware test.
