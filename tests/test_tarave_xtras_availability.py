#!/usr/bin/env python3
"""Compile the actual X-TRAS service against filesystem/UI stubs and run fixtures."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('g++'), 'g++ required')
class AvailabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        b = cls.base
        (b / 'utils').mkdir()
        (b / 'resources').mkdir()
        # Compile the production implementation, including catalog and execute paths.
        shutil.copy(ROOT / 'es-app/src/TaraveXtrasService.cpp', b / 'TaraveXtrasService.cpp')
        shutil.copy(ROOT / 'es-app/src/TaraveXtrasService.h', b / 'TaraveXtrasService.h')
        api = (ROOT / 'es-app/src/ApiSystem.h').read_text()
        package = api[api.index('struct PacmanPackage'):api.index('struct PadInfo')]
        (b / 'ApiSystem.h').write_text('#pragma once\n#include <string>\n#include <vector>\n' + package)
        (b / 'Paths.h').write_text('''#pragma once
#include <cstdlib>
#include <string>
namespace Paths {
inline std::string getHomePath() { return std::getenv("TEST_HOME"); }
inline std::string getUserEmulationStationPath() { return getHomePath(); }
}
''')
        (b / 'Log.h').write_text('#pragma once\n#include <iostream>\n#define LOG(x) std::cerr\n')
        (b / 'resources/ResourceManager.h').write_text('''#pragma once
#include "Paths.h"
class ResourceManager { public:
static ResourceManager* getInstance() { static ResourceManager r; return &r; }
std::string getResourcePath(const std::string&) { return Paths::getHomePath()+"/catalog.ini"; }
};
''')
        (b / 'utils/FileSystemUtil.h').write_text('''#pragma once
#include <filesystem>
#include <list>
#include <string>
namespace Utils { namespace FileSystem {
inline bool isRegularFile(const std::string& p) { return std::filesystem::is_regular_file(p); }
inline bool isDirectory(const std::string& p) { return std::filesystem::is_directory(p); }
inline std::list<std::string> getDirContent(const std::string& p) {
std::list<std::string> result;
for(auto& e:std::filesystem::directory_iterator(p)) result.push_back(e.path());
return result;
}
inline std::string getExtension(const std::string& p) { return std::filesystem::path(p).extension(); }
inline std::string getFileName(const std::string& p) { return std::filesystem::path(p).filename(); }
inline std::string getParent(const std::string& p) { return std::filesystem::path(p).parent_path(); }
inline void createDirectory(const std::string& p) { std::filesystem::create_directories(p); }
}}
''')
        (b / 'main.cpp').write_text('''#include "TaraveXtrasService.h"
#include <iostream>
int main(int argc,char** argv) {
if(argc>1) { auto r=TaraveXtrasService::install("module:blocked"); std::cout<<r.first; return r.second==1 ? 0:1; }
for(auto p:TaraveXtrasService::list()) std::cout<<p.name<<"|"<<p.description<<"|"<<p.retropieAvailability<<"|"<<p.status<<"\\n";
}
''')
        subprocess.run(['g++', '-std=c++17', '-I'+str(b), str(b/'TaraveXtrasService.cpp'),
                        str(b/'main.cpp'), '-o', str(b/'query')], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.fixture = tempfile.TemporaryDirectory()
        self.addCleanup(self.fixture.cleanup)
        self.home = Path(self.fixture.name)
        (self.home/'bin').mkdir()
        (self.home/'bin/lsb_release').write_text('#!/bin/sh\nexit 0\n')
        (self.home/'bin/lsb_release').chmod(0o755)
        self.setup = self.home / 'setup'
        self.mods = self.setup / 'scriptmodules'
        (self.mods / 'ports').mkdir(parents=True)
        (self.mods / 'supplementary').mkdir()
        (self.setup / 'retropie_packages.sh').write_text('exit 99\n')
        (self.mods/'system.sh').write_text('''
test_chroot() { :; }
get_platform() { :; }
get_os_version() { getDepends lsb-release; rm forbidden-cleanup; }
conf_memory_vars() { :; }
conf_build_vars() { :; }
setup_env() { exit 99; }
''')
        (self.mods/'helpers.sh').write_text('getDepends() { exit 99; }\n')
        (self.mods/'inifuncs.sh').write_text('')
        self.package_script = '''declare -A __mod_info
rp_registerAllModules() {
__mod_id=(supported blocked bezelproject)
for id in "${__mod_id[@]}"; do __mod_info[$id/type]=ports; done
__mod_info[supported/enabled]=1
__mod_info[blocked/enabled]=0
__mod_info[bezelproject/enabled]=0
}
'''
        (self.mods/'packages.sh').write_text(self.package_script)
        for module in ['supported', 'blocked']:
            (self.mods/'ports'/f'{module}.sh').write_text(
                f'rp_module_id="{module}"\nrp_module_desc="Official {module}"\nrp_module_flags="!all x86"\n')
        (self.mods/'supplementary/bezelproject.sh').write_text(
            'rp_module_id="bezelproject"\nrp_module_desc="Bezel Project"\n')
        extra = self.setup/'ext/Extra/scriptmodules/ports'
        extra.mkdir(parents=True)
        (extra/'blocked.sh').write_text('rp_module_id="blocked"\nrp_module_desc="Duplicate"\n')
        (self.home/'catalog.ini').write_text('''[homebrew]
ready=yes
system=nes
filename=demo.nes
title=Demo
download=https://example.org/demo.nes
''')

    def run_query(self, *args):
        env = dict(os.environ, TEST_HOME=str(self.home), TARAVE_RETROPIE_SETUP=str(self.setup),
                   PATH=str(self.home/"bin")+os.pathsep+os.environ["PATH"])
        return subprocess.run([str(self.base/'query'), *args], env=env,
                              capture_output=True, text=True, check=True, timeout=5).stdout

    def test_states_duplicates_bezel_and_free_games(self):
        output = self.run_query()
        self.assertIn('module:supported|Official supported|1|available', output)
        self.assertIn('module:blocked|Official blocked|0|available', output)
        self.assertIn('module:bezelproject|Bezel Project|0|available', output)
        self.assertIn('game:homebrew|Demo|-1|available', output)
        self.assertNotIn('Duplicate', output)

    def test_incomplete_query_leaves_unknown(self):
        (self.mods/'packages.sh').write_text('rp_registerAllModules() { exit 1; }')
        output = self.run_query()
        self.assertIn('module:blocked|Official blocked|-1|available', output)

    def test_backend_refuses_unavailable_install_before_sudo(self):
        self.assertIn('Unavailable for this system', self.run_query('install'))


if __name__ == '__main__':
    unittest.main()
