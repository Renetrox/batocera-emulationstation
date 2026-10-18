#!/usr/bin/env bash
# Optional installation/check of RetroPie's *official* retropiemenu.
# Does not install Bluetooth drivers or touch an existing controller pairing.
set -euo pipefail
mode="${1:---check}"
case "$mode" in
    --check|--configure) ;;
    *) echo "Usage: $0 [--check|--configure]" >&2; exit 2 ;;
esac

setup="${RETROPIE_SETUP_DIR:-$HOME/RetroPie-Setup}"
menu="${RETROPIE_MENU_DIR:-$HOME/RetroPie/retropiemenu}"
packages="$setup/retropie_packages.sh"

if [[ ! -f "$packages" ]]; then
    echo "RetroPie-Setup not found: $packages" >&2
    exit 1
fi

if [[ "$mode" == "--configure" ]]; then
    echo "Configuring official RetroPie menu (no sixaxis/sixad modifications)."
    sudo bash "$packages" retropiemenu configure
fi

echo "RetroPie Setup: $packages"
if [[ -f "$menu/rpsetup.rp" ]]; then
    printf 'RetroPie settings shortcuts: present (%s)\n' "$menu"
    echo "Tarave automatically detects RetroPie Runcommand when installed."
    echo "Set TARAVE_USE_RETROPIE_RUNCOMMAND=0 only to disable that integration."
else
    echo "RetroPie settings shortcuts: missing"
    echo "Use: bash $0 --configure"
    exit 1
fi
