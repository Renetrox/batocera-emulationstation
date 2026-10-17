from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

class DispatchTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('g++'),'g++ required')
    def test_actual_standalone_finish_dispatch(self):
        root=Path(__file__).parents[1]
        text=(root/'es-core/src/InputManager.cpp').read_text()
        method=text.split('void InputManager::doOnFinish(bool configureRetroPie)',1)[1].split('std::string InputManager::getConfigPath()',1)[0]
        source=r'''
#include <string>
#include <sstream>
#include <sys/wait.h>
#include <cerrno>
#include <cassert>
static int lookups=0, launches=0;
static bool available=false;
static std::ostringstream log;
#define LOG(x) log
char** environ=nullptr;
int posix_spawnp(pid_t*,const char*,void*,void*,char* const[],char* const[]) {++launches;return 2;}
struct ResourceManager {
 static ResourceManager* getInstance() {static ResourceManager r;return &r;}
 std::string getResourcePath(const std::string&) {++lookups;return "/test/helper";}
};
namespace Utils { namespace FileSystem {bool exists(const std::string&) {return available;}}}
struct InputManager {
 bool initialized() {return true;}
 std::string getTemporaryConfigPath() {return "/test/native/es_last_input.cfg";}
 void doOnFinish(bool configureRetroPie);
};
void InputManager::doOnFinish(bool configureRetroPie)
'''+method+r'''
int main() {
 InputManager input;
 input.doOnFinish(false);
 assert(lookups==0 && launches==0);
 input.doOnFinish(true);
 assert(lookups==1 && launches==0);
 available=true;
 input.doOnFinish(true);
 assert(lookups==2 && launches==1);
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            cpp=Path(tmp)/'test.cpp';binary=Path(tmp)/'test';cpp.write_text(source)
            subprocess.run(['g++','-std=c++11',str(cpp),'-o',str(binary)],check=True,capture_output=True)
            subprocess.run([str(binary)],check=True)

if __name__=='__main__': unittest.main()
