> Updated standalone flow: automatic detection does not fire configuration
> events or onfinish hooks. Manual confirmation invokes only the emulator bridge,
> without reloading the native mapping or running legacy onfinish commands.
> Dispatcher selection prefers an installed ES-X configurator and falls back to
> stock RetroPie, requiring its configscripts directory. The frontend writer
> remains excluded. Existing XML files are not automatically repaired.
> Fifteen tests pass, including compiled native dispatch tests with process
> stand-ins. Physical controller/full GUI validation remains pending.

# Tarave-ES: experimental RetroPie controller bridge

On standalone Linux builds, confirming a manual controller mapping now invokes
`resources/retropie-input-bridge.py` if the stock RetroPie dispatcher exists at:
`/opt/retropie/supplementary/emulationstation/scripts/inputconfiguration.sh`.
Automatic SDL controller recognition does not invoke this new bridge.

The native mapping stays in the configured frontend directory. The bridge reads
its single-device `es_last_input.cfg`, translates names, derives opposite axis
or hat directions, and temporarily supplies the real user's
`~/.emulationstation/es_temporaryinput.cfg` to the installed RetroPie dispatcher.
The previous temporary file is restored after success or failure; if absent,
the bridge removes its temporary export. It rejects unsupported or conflicting
mappings and a symlink at the temporary target. A per-user lock serializes bridge
invocations. Other programs invoking RetroPie independently do not share this lock.

The dispatcher now runs with a private configscripts list that excludes
RetroPie's emulationstation.sh frontend writer. Emulator modules remain the
installed ones. This prevents a shared/native es_input.cfg from being rewritten
with RetroPie names or A/B swaps.

The bridge does not rewrite the main RetroPie es_input.cfg or copy mappings for
other devices. Installed RetroPie configurators do update emulator settings;
those updates are not transactional and are not rolled back on a partial failure.
Names/GUIDs and available SDL vendor/product IDs are exported. Explicit disabled
hotkeys (`key`, id 0) are preserved. Stock dispatcher disable settings remain in
effect. Python paths/arguments are passed without a shell.

Standalone onfinish XML commands are not executed: the explicit bridge replaces
them. Custom controller hooks must be reviewed before reconnecting them.
Distribution BATOCERA builds and Windows retain their native hook behavior.

## Tests and remaining validation

Seven bridge tests pass: button translation/source preservation, both analog
axis signs, hat opposites, disabled hotkey, restoration on success/failure,
cleanup, invalid analog rejection, and a real Bash subprocess receiving the
translated XML. Together with the four Skyscraper tests, 11 tests pass.
`git diff --check` passes.

C++ compilation, physical devices, and actual RetroPie configurators have not
been run in this environment. Python 3.8+ and the installed RetroPie dependencies
(including xmlstarlet) are required. Failures are logged; the existing synchronous
onfinish model means the mapping screen waits for configurators to finish.
Player ordering, Bluetooth pairing, kernel drivers, and emulator launch/exit
behavior are separate work. The bridge configures only emulators covered by the
installed RetroPie scripts. This does not guarantee a universal exit hotkey.

After compiling/installing the experimental branch and its resources, configure
one pad from the native menu and confirm OK. Check the terminal/frontend log,
then verify its RetroArch autoconfiguration and an actual game. Keep the working
frontend installed until those on-device tests pass.

Regression check: a real Bash fixture confirms that the frontend writer is
excluded while the emulator configurator still executes. All 12 Python tests pass.
