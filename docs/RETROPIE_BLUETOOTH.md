# Tarave Bluetooth on standalone RetroPie

The standalone frontend now uses BlueZ's `bluetoothctl` through the bundled
`resources/retropie-bluetooth.py`, instead of calling `batocera-bluetooth`.
Native Batocera/Retrobat backends retain their original dispatch.

## Supported flow

1. Open Controller & Bluetooth Settings. The Bluetooth section appears when
   bluetoothctl and the bundled helper exist.
2. Choose Enable Bluetooth if the adapter is off. This requests power through
   BlueZ under the current user, without sudo, service installation or rfkill
   changes. Existing BlueZ policy permissions apply.
3. Put the controller in pairing mode, then choose Pair a Bluetooth Device
   Manually. Nearby and cached devices appear in Tarave's native selection menu.
4. Select the controller. The helper pairs (only if not already bonded), trusts,
   connects and verifies actual state. No automatic pairing of arbitrary nearby
   devices is attempted. Devices requiring typed PIN/passkey confirmation are
   outside this first gamepad-oriented NoInputNoOutput flow.
5. Bluetooth Device List shows paired devices and connection state. Its existing
   Connect, Disconnect and Forget actions now call BlueZ. List loading is
   asynchronous on standalone RetroPie.
6. After pairing, configure the controller in Tarave's normal input wizard.
   Pairing does not generate emulator button mappings by itself.

The existing retropie-input-bridge translates an explicit input configuration
through RetroPie configurators. The P1/P2 helper applies explicit player choices
for RetroArch/libretro. These features remain separate from Bluetooth and do not
install missing kernel modules or configure every standalone emulator.

## Lifetime and errors

- Closing the pairing menu cancels only its helper process group, joins its
  worker and invalidates queued UI callbacks. An old callback cannot populate a
  newly opened scan window.
- BlueZ discovery stays owned by its persistent bluetoothctl client. Exiting that
  client releases its own discovery session, without stopping another manager.
- Commands use argument vectors, validate MAC addresses and never invoke a shell
  or sudo. Pairing/connection results are verified through BlueZ device state;
  textual errors with a zero process exit code are treated as failures.
- Ordinary operations have subprocess timeouts and a bounded C++ watchdog.
- Failures are visible instead of silently closing an action as successful.
- Bulk forgetting is not exposed on standalone RetroPie: remove the selected
  device explicitly. Existing bonds are never removed just to run Pair again.
- The default BlueZ adapter is used. Multiple-adapter selection, legacy PS3
  provisioning, PIN entry, audio routing and service/permission installation are
  not included. Existing system tools remain available for these tasks.

If no adapter is available, the service is stopped, rfkill blocks it, or policy
rejects an operation, Tarave reports failure. The UI cannot replace absent
Bluetooth/HID kernel support on boards such as the Orange Pi 4A.

## Validation

- `python3 tests/test_tarave_bluetooth.py`: 11 tests, including native C++11 helper
  cancellation, command arguments, existing bond preservation, actual connected
  state, error exit handling and menu-protocol escaping. No physical device is
  paired, disconnected or removed by the tests.
- Input bridge (9), player order (12) and input dispatch (1) regression tests pass.
- The standalone CI workflow runs these before building the complete frontend.
- Hardware validation is still required: scan/cancel/reopen, pair a real gamepad,
  verify input in Tarave and a RetroArch game, reconnect, and test P1/P2 with two
  distinct pads. Automated tests do not establish driver compatibility.

Reference: BlueZ's official bluetoothctl manual:
https://github.com/bluez/bluez/blob/master/doc/bluetoothctl.rst
