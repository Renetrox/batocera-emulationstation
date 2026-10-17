import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location('inputbridge', Path(__file__).parents[1]/'resources/retropie-input-bridge.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

class InputBridgeTests(unittest.TestCase):
    def source(self, folder, inputs, kind='joystick'):
        root=ET.Element('inputList')
        device=ET.SubElement(root, 'inputConfig', type=kind, deviceName='Generic & pad', deviceGUID='test', vendorId='123', productId='456')
        for name, input_type, identifier, value in inputs:
            ET.SubElement(device, 'input', name=name, type=input_type, id=str(identifier), value=str(value))
        path=Path(folder)/'native.xml'
        ET.ElementTree(root).write(path)
        return path

    def test_complete_mapping_and_source_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            source=self.source(folder, [('pageup','button',4,1),('pagedown','button',5,1),('l2','axis',2,1),('r2','axis',5,1),('l3','button',8,1),('r3','button',9,1),('hotkey','button',10,1),('a','button',1,1),('joystick1up','axis',1,-1),('joystick1left','axis',0,1),('joystick2up','axis',4,-1),('joystick2left','axis',3,-1)])
            original=source.read_bytes()
            device=ET.fromstring(bridge.translate(source)).find('inputConfig')
            entries={item.get('name'):item.attrib for item in device}
            for name in ['leftshoulder','rightshoulder','lefttrigger','righttrigger','leftthumb','rightthumb','hotkeyenable']:
                self.assertIn(name,entries)
            self.assertEqual(entries['leftanalogdown']['value'],'1')
            self.assertEqual(entries['leftanalogright']['value'],'-1')
            self.assertEqual(entries['rightanalogright']['id'],'3')
            self.assertEqual(entries['a']['id'],'1')
            self.assertEqual(device.get('vendorId'),'123')
            self.assertEqual(source.read_bytes(),original)

    def test_hat_opposites(self):
        with tempfile.TemporaryDirectory() as folder:
            source=self.source(folder,[('joystick1up','hat',0,1)])
            device=ET.fromstring(bridge.translate(source)).find('inputConfig')
            self.assertEqual(device.find("input[@name='leftanalogdown']").get('value'),'4')

    def test_disabled_hotkey_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            source=self.source(folder,[('hotkey','key',0,1)])
            item=ET.fromstring(bridge.translate(source)).find('inputConfig/input')
            self.assertEqual(item.attrib,dict(name='hotkeyenable',type='key',id='0',value='1'))

    def test_apply_and_restore_on_success_and_failure(self):
        for fail in (False,True):
            with self.subTest(fail=fail),tempfile.TemporaryDirectory() as folder:
                source=self.source(folder,[('hotkey','button',6,1)])
                target=Path(folder)/'.emulationstation/es_temporaryinput.cfg'
                target.parent.mkdir()
                target.write_bytes(b'old temporary contents')
                def execute(script):
                    self.assertEqual(script,Path('/test/configure.sh'))
                    self.assertEqual(ET.parse(target).getroot().find('inputConfig/input').get('name'),'hotkeyenable')
                    if fail: raise subprocess.CalledProcessError(1,str(script))
                with patch.object(bridge,'run_configurators',side_effect=execute):
                    if fail:
                        with self.assertRaises(subprocess.CalledProcessError): bridge.apply(source,folder,Path('/test/configure.sh'))
                    else: bridge.apply(source,folder,Path('/test/configure.sh'))
                self.assertEqual(target.read_bytes(),b'old temporary contents')

    def test_temporary_removed_if_previously_absent(self):
        with tempfile.TemporaryDirectory() as folder:
            source=self.source(folder,[('up','button',1,1)])
            with patch.object(bridge,'run_configurators'): bridge.apply(source,folder,Path('/test/configure.sh'))
            self.assertFalse((Path(folder)/'.emulationstation/es_temporaryinput.cfg').exists())

    def test_real_shell_receives_translation(self):
        with tempfile.TemporaryDirectory() as folder:
            source=self.source(folder,[('hotkey','button',6,1),('pageup','button',4,1)])
            script=Path(folder)/'configurator.sh'
            (Path(folder)/'configscripts').mkdir()
            target=Path(folder)/'.emulationstation/es_temporaryinput.cfg'
            # Harmless stand-in for the installed dispatcher, executed by real bash.
            import shlex
            script.write_text("#!/bin/bash\npython3 - " + shlex.quote(str(target)) + " <<'CHECK'\nimport sys, xml.etree.ElementTree as ET\nnames={i.get('name') for i in ET.parse(sys.argv[1]).getroot().findall('inputConfig/input')}\nassert names == {'hotkeyenable','leftshoulder'}, names\nCHECK\n")
            bridge.apply(source,folder,script)
            self.assertFalse(target.exists())

    def test_frontend_writer_excluded_from_real_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            modules=root/'configscripts'
            modules.mkdir()
            dispatcher=root/'inputconfiguration.sh'
            dispatcher.write_text('#!/bin/bash\nfor module in "$(dirname "$0")"/configscripts/*.sh; do source "$module"; done\n')
            frontend=root/'frontend-touched'
            emulator=root/'emulator-configured'
            import shlex
            (modules/'emulationstation.sh').write_text('touch '+shlex.quote(str(frontend)))
            (modules/'retroarch.sh').write_text('touch '+shlex.quote(str(emulator)))
            bridge.run_configurators(dispatcher)
            self.assertFalse(frontend.exists())
            self.assertTrue(emulator.exists())

    def test_dispatcher_selection_and_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            first=root/'esx/inputconfiguration.sh'
            second=root/'stock/inputconfiguration.sh'
            for candidate in (first,second):
                candidate.parent.mkdir()
                candidate.write_text('#!/bin/bash')
                (candidate.parent/'configscripts').mkdir()
            self.assertEqual(bridge.select_dispatcher([first,second]),first)
            first.unlink()
            self.assertEqual(bridge.select_dispatcher([first,second]),second)
            second.unlink()
            with self.assertRaises(ValueError): bridge.select_dispatcher([first,second])

    def test_invalid_analog_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source=self.source(folder,[('joystick1up','button',1,1)])
            with self.assertRaises(ValueError): bridge.translate(source)

if __name__=='__main__': unittest.main()
