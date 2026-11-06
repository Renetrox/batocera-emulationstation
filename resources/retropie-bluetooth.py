#!/usr/bin/env python3
"""BlueZ adapter for Tarave's native Bluetooth menus; no shell or sudo."""
import argparse
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time

MAC = re.compile(r'^[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}$')
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
STOP = False


class BluetoothError(Exception):
    pass


def run(*args, timeout=8):
    try:
        p = subprocess.run(['bluetoothctl', '--timeout', str(timeout), *args],
                           capture_output=True, text=True, timeout=timeout + 2,
                           env=dict(os.environ, LC_ALL='C'))
    except (OSError, subprocess.TimeoutExpired) as e:
        raise BluetoothError('BLUETOOTH OPERATION FAILED') from e
    text = ANSI.sub('', p.stdout + '\n' + p.stderr)
    if p.returncode != 0 or any(s in text for s in (
            'org.bluez.Error.', 'Failed to ', 'No default controller',
            'not available', 'Invalid command', 'not ready')):
        raise BluetoothError('BLUETOOTH OPERATION FAILED')
    return text


def info(mac):
    if not MAC.fullmatch(mac):
        raise BluetoothError('INVALID BLUETOOTH ADDRESS')
    text = run('info', mac)
    props = {}
    for line in text.splitlines():
        if ':' in line.strip():
            k, v = line.strip().split(':', 1)
            props[k] = v.strip()
    if 'Name' not in props and 'Alias' not in props:
        raise BluetoothError('BLUETOOTH OPERATION FAILED')
    return props


def devices(paired_only=False):
    result = []
    for line in run('devices').splitlines():
        match = re.match(r'^Device ([0-9A-Fa-f:]{17}) (.+)$', line.strip())
        if not match or not MAC.fullmatch(match[1]):
            continue
        props = info(match[1])
        if not paired_only or props.get('Paired') == 'yes' or props.get('Bonded') == 'yes':
            result.append((match[1].upper(), props))
    return result


def attr(value):
    # Existing native menus read attributes by delimiter, without XML decoding.
    return ''.join(c for c in value if c.isprintable()).replace('"', "'").replace('<', '(').replace('>', ')')[:180]


def emit(mac, props, status='added'):
    name = props.get('Alias') or props.get('Name') or mac
    icon = props.get('Icon', 'unknown')
    print(f'<device id="{mac}" name="{attr(name)}" type="{attr(icon)}" '
          f'connected="{props.get("Connected", "no")}" status="{status}" />', flush=True)


def act(action, mac=None):
    if action in ('enable', 'disable'):
        expected = 'yes' if action == 'enable' else 'no'
        run('power', 'on' if action == 'enable' else 'off')
        if f'Powered: {expected}' not in run('show'):
            raise BluetoothError('BLUETOOTH OPERATION FAILED')
        return
    props = info(mac)
    if action == 'pair':
        # New BlueZ pair can remove an existing bond. Never re-pair a paired pad.
        if props.get('Paired') != 'yes' and props.get('Bonded') != 'yes':
            run('--agent', 'NoInputNoOutput', 'pair', mac, timeout=35)
        run('trust', mac)
        if info(mac).get('Trusted') != 'yes':
            raise BluetoothError('BLUETOOTH OPERATION FAILED')
        if info(mac).get('Connected') != 'yes':
            run('connect', mac, timeout=15)
        props = info(mac)
        if (props.get('Paired') != 'yes' and props.get('Bonded') != 'yes') or props.get('Connected') != 'yes':
            raise BluetoothError('BLUETOOTH OPERATION FAILED')
    elif action == 'connect':
        run('connect', mac, timeout=15)
        if info(mac).get('Connected') != 'yes':
            raise BluetoothError('BLUETOOTH OPERATION FAILED')
    elif action == 'disconnect':
        run('disconnect', mac)
        if info(mac).get('Connected') == 'yes':
            raise BluetoothError('BLUETOOTH OPERATION FAILED')
    elif action == 'remove':
        run('remove', mac)
        if any(address == mac.upper() for address, _ in devices()):
            raise BluetoothError('BLUETOOTH OPERATION FAILED')


def scan():
    if 'Powered: yes' not in run('show'):
        raise BluetoothError('ENABLE BLUETOOTH FIRST')
    for mac, props in devices():
        emit(mac, props)
    # Keep this client alive: discovery belongs to its D-Bus session.
    client = subprocess.Popen(['bluetoothctl', '--agent', 'NoInputNoOutput'],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, env=dict(os.environ, LC_ALL='C'))
    selector = selectors.DefaultSelector()
    try:
        client.stdin.write(b'scan on\n')
        client.stdin.flush()
        selector.register(client.stdout, selectors.EVENT_READ)
        pending = ''
        while not STOP:
            for key, _ in selector.select(.2):
                chunk = os.read(key.fileobj.fileno(), 4096)
                if not chunk:
                    raise BluetoothError('BLUETOOTH OPERATION FAILED')
                pending += ANSI.sub('', chunk.decode('utf-8', 'replace'))
                while '\n' in pending:
                    line, pending = pending.split('\n', 1)
                    if any(s in line for s in ('Failed to start discovery', 'No default controller', 'org.bluez.Error.')):
                        raise BluetoothError('BLUETOOTH OPERATION FAILED')
                    match = re.search(r'\[(NEW|DEL|CHG)\] Device ([0-9A-Fa-f:]{17}) (.+)', line)
                    if not match or not MAC.fullmatch(match[2]):
                        continue
                    event, mac, label = match.groups()
                    if event == 'DEL':
                        emit(mac, {'Name': mac}, 'removed')
                    elif event == 'NEW' or label.startswith(('Name: ', 'Alias: ')):
                        if event == 'CHG':
                            label = label.split(': ', 1)[1]
                        emit(mac, {'Name': label})
                if len(pending) > 16384:
                    pending = ''
    finally:
        selector.close()
        # Exiting this client releases only its own discovery session.
        client.terminate()
        try:
            client.wait(timeout=2)
        except subprocess.TimeoutExpired:
            client.kill()
            client.wait()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['enable', 'disable', 'scan', 'list', 'pair', 'connect', 'disconnect', 'remove'])
    parser.add_argument('mac', nargs='?')
    args = parser.parse_args()
    if not shutil.which('bluetoothctl'):
        print('<error key="BLUETOOTH TOOLS NOT FOUND" />', flush=True)
        return 1
    try:
        if args.action in ('pair', 'connect', 'disconnect', 'remove') and not MAC.fullmatch(args.mac or ''):
            raise BluetoothError('INVALID BLUETOOTH ADDRESS')
        if args.action == 'scan':
            scan()
        elif args.action == 'list':
            for mac, props in devices(True):
                emit(mac, props)
        else:
            act(args.action, args.mac)
        return 0
    except (OSError, subprocess.TimeoutExpired):
        print('<error key="BLUETOOTH OPERATION FAILED" />', flush=True)
        return 1
    except BluetoothError as e:
        print(f'<error key="{e}" />', flush=True)
        return 1


def stop(_sig, _frame):
    global STOP
    STOP = True


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    sys.exit(main())
