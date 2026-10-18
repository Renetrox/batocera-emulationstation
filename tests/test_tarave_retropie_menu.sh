#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
mkdir -p "$temp/RetroPie-Setup" "$temp/RetroPie/retropiemenu"
touch "$temp/RetroPie-Setup/retropie_packages.sh"
export RETROPIE_SETUP_DIR="$temp/RetroPie-Setup"
export RETROPIE_MENU_DIR="$temp/RetroPie/retropiemenu"

if bash "$root/scripts/tarave-retropie-menu.sh" --check >/dev/null 2>&1; then
    echo "Expected failure without configured menu" >&2
    exit 1
fi
touch "$RETROPIE_MENU_DIR/rpsetup.rp"
bash "$root/scripts/tarave-retropie-menu.sh" --check | grep -q "shortcuts: present"
if bash "$root/scripts/tarave-retropie-menu.sh" --something >/dev/null 2>&1; then
    echo "Expected refusal of unsupported mode" >&2
    exit 1
fi
echo "PASS: RetroPie menu detection is safe and read-only"
