# Tarave X-TRAS: RetroPie platform availability

The active browser is `GuiBatoceraStore`, backed by `TaraveXtrasService`.
The old `GuiTaraveXtras` is not compiled and is deliberately left unchanged.

Ports and Bezel Project now carry a separate availability state (-1 unknown,
0 disabled, 1 enabled) plus their module flags. Installed status remains separate.
Disabled entries show a Font Awesome warning triangle and salmon title, with an
explicit translated label. Accept opens details instead of queueing installation.
The service also rechecks before executing an installation, covering direct calls
and queued jobs whose platform availability may have changed.

The query reuses the installed RetroPie-Setup platform/OS/compiler discovery and
module registration rules, including ordered flags and version comparisons. It
runs once per catalog load through the store's existing GuiLoading worker, with a
20-second timeout. Post-install refresh now uses that same asynchronous loader.
No setup_env, sudo, dependency installation, key import or framebuffer switch is
used for discovery; legacy Pi pkgconfig cleanup is suppressed. The login home is
passed explicitly so Tarave's private --home does not change platform discovery.
Failed queries leave availability unknown, with a visible unverified label.

Official modules win over duplicate external IDs. Vendor/file ordering is sorted.
Free games, English tab/filter identities, native Batocera store behavior and the
installer remain unchanged. New labels use gettext (Spanish and Mexican Spanish
translations included; other locales fall back to English).

## Validation

`python3 tests/test_tarave_xtras.py` checks existing native integration (9 tests).
`python3 tests/test_tarave_xtras_availability.py` compiles the actual backend with
minimal API/filesystem stubs and exercises catalog states, duplicate precedence,
Bezel Project, unaffected free games, failed queries and refusal before sudo.
The real PacmanPackage struct is used, including installed-state handling.

The existing standalone workflow runs both suites before compiling the full UI.
On-device visual validation is still needed: compare with Setup's disabled entries,
inspect details, switch tabs, refresh, and verify normal installation on a supported
module. Availability reflects Setup policy, not runtime/performance guarantees.

Changes belong to `experiment/retropie-standalone-20261013`, the existing installer
branch; `master` and the RetroPie-Extra installer are not modified.
