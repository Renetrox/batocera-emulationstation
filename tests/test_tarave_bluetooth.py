#!/usr/bin/env python3
"""BlueZ operations are mocked: tests never pair/remove physical devices."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bt', ROOT/'resources/retropie-bluetooth.py')
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)
MAC = '01:23:45:67:89:AB'


class BlueZTests(unittest.TestCase):
    def test_validated_addresses_cannot_be_commands(self):
        with patch.object(bt, 'run') as run:
            with self.assertRaises(bt.BluetoothError):
                bt.act('pair', MAC+'; touch /tmp/injected')
            run.assert_not_called()

    def test_noninteractive_invocation_and_exit_zero_errors(self):
        result = subprocess.CompletedProcess([], 0, 'Failed to connect: org.bluez.Error.Failed', '')
        with patch.object(bt.subprocess, 'run', return_value=result) as run:
            with self.assertRaises(bt.BluetoothError):
                bt.run('connect', MAC)
            self.assertIsInstance(run.call_args.args[0], list)
            self.assertNotIn('shell', run.call_args.kwargs)

    def test_existing_bond_is_not_repaired(self):
        props = dict(Name='Pad', Paired='yes', Trusted='yes', Connected='yes')
        with patch.object(bt, 'info', return_value=props), patch.object(bt, 'run') as run:
            bt.act('pair', MAC)
            run.assert_called_once_with('trust', MAC)

    def test_pair_trust_connect_and_verify(self):
        initial = dict(Name='Pad', Paired='no', Connected='no')
        paired = dict(Name='Pad', Paired='yes', Trusted='yes', Connected='no')
        ready = dict(paired, Connected='yes')
        with patch.object(bt, 'info', side_effect=[initial, paired, paired, ready]), patch.object(bt, 'run') as run:
            bt.act('pair', MAC)
            self.assertEqual([x.args[:2] for x in run.call_args_list],
                             [('--agent', 'NoInputNoOutput'), ('trust', MAC), ('connect', MAC)])

    def test_connect_requires_actual_connected_state(self):
        with patch.object(bt, 'info', return_value={'Name':'Pad', 'Connected':'no'}), patch.object(bt, 'run'):
            with self.assertRaises(bt.BluetoothError): bt.act('connect', MAC)

    def test_removal_checks_that_device_disappeared(self):
        with patch.object(bt, 'info', return_value={'Name':'Pad'}), patch.object(bt, 'run'), patch.object(bt, 'devices', return_value=[(MAC, {})]):
            with self.assertRaises(bt.BluetoothError): bt.act('remove', MAC)

    def test_list_filters_paired_and_keeps_state(self):
        other = '11:22:33:44:55:66'
        with patch.object(bt, 'run', return_value=f'Device {MAC} Pad\nDevice {other} Phone'), patch.object(bt, 'info', side_effect=[{'Name':'Pad','Paired':'yes','Connected':'yes'}, {'Name':'Phone','Paired':'no'}]):
            self.assertEqual(bt.devices(True), [(MAC, {'Name':'Pad','Paired':'yes','Connected':'yes'})])

    def test_scan_requires_power_without_turning_it_on(self):
        with patch.object(bt, 'run', return_value='Powered: no') as run:
            with self.assertRaises(bt.BluetoothError): bt.scan()
            run.assert_called_once_with('show')

    def test_device_names_cannot_break_menu_protocol(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            bt.emit(MAC, {'Name':'Pad "x"\n<device id="bad">'})
        line = stream.getvalue()
        self.assertEqual(line.count('<device '), 1)
        self.assertEqual(line.count('\n'), 1)
        self.assertIn(f'id="{MAC}"', line)

    def test_power_reports_real_failure(self):
        with patch.object(bt, 'run', return_value='Powered: no'):
            with self.assertRaises(bt.BluetoothError): bt.act('enable')


@unittest.skipUnless(shutil.which('g++'), 'g++ required')
class NativeBridgeTests(unittest.TestCase):
    def test_scoped_cancellation_and_argument_passing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'resources').mkdir(); (root/'utils').mkdir()
            shutil.copy(ROOT/'es-app/src/RetroPieBluetooth.h', root/'RetroPieBluetooth.h')
            (root/'resources/ResourceManager.h').write_text('''#pragma once
#include <cstdlib>
#include <string>
class ResourceManager { public:
static ResourceManager* getInstance(){static ResourceManager r;return &r;}
std::string getResourcePath(const std::string&){return std::getenv("TEST_BT_HELPER");}
};''')
            (root/'utils/FileSystemUtil.h').write_text('''#pragma once
#include <string>
#include <sys/stat.h>
namespace Utils { namespace FileSystem {
inline bool isRegularFile(const std::string& p){ struct stat s;return stat(p.c_str(),&s)==0&&S_ISREG(s.st_mode); }
}}''')
            helper=root/'helper.py'
            helper.write_text('''import sys,time
if sys.argv[1]=='scan':
 print('<device id="01:23:45:67:89:AB" name="Pad" />',flush=True)
 time.sleep(30)
elif sys.argv[2]!='01:23:45:67:89:AB': sys.exit(2)
''')
            (root/'main.cpp').write_text('''#include "RetroPieBluetooth.h"
#include <thread>
int main(){
if(!RetroPieBluetooth::run("connect","01:23:45:67:89:AB"))return 1;
RetroPieBluetooth::prepareScan();
std::atomic<bool> seen{false};
std::thread worker([&](){RetroPieBluetooth::run("scan","",[&](const std::string&){seen=true;});});
std::this_thread::sleep_for(std::chrono::milliseconds(200));
RetroPieBluetooth::stopScan();worker.join();return seen?0:2;
}''')
            subprocess.run(['g++','-std=c++11','-pthread','-I'+tmp,str(root/'main.cpp'),'-o',str(root/'test')],check=True)
            subprocess.run([str(root/'test')],env=dict(os.environ,TEST_BT_HELPER=str(helper)),check=True,timeout=3)


if __name__=='__main__': unittest.main()
