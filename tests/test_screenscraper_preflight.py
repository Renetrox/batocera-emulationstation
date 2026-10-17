"""Compile the actual preflight method with a deterministic HTTP stand-in."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

class PreflightTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('g++'), 'g++ required')
    def test_account_branches(self):
        root=Path(__file__).parents[1]
        source=(root/'es-app/src/scrapers/ScreenScraper.cpp').read_text()
        self.assertIn('#include "LocaleES.h"', source)
        method=source.split('int ScreenScraperScraper::getThreadCount(std::string &result)',1)[1].rsplit('#endif',1)[0]
        harness=r'''
#include <string>
#include <cassert>
#include "LocaleES.h"
static int calls=0, status=0, maxthreads=3;
static bool validXML=true;
struct Settings {
 std::string user,pass;
 static Settings* getInstance() { static Settings s; return &s; }
 std::string getString(const std::string& key) { return key=="ScreenScraperUser"?user:pass; }
};
struct HttpReq {
 enum {REQ_SUCCESS=0};
 HttpReq(const std::string&) {++calls;}
 void wait() {}
 int status() {return ::status;}
 std::string getErrorMsg() {return "rejected";}
 std::string getContent() {return "<Data/>";}
};
namespace Utils { namespace String {
 std::string replace(std::string value,const std::string&,const std::string&) {return value;}
 std::string trim(std::string value) {return value;}
}}
namespace pugi {
 struct xml_parse_result {operator bool() const {return validXML;}};
 struct xml_document {xml_parse_result load_string(const char*) {return {};}};
}
struct ScreenScraperRequest {
 struct ScreenScraperConfig {std::string getUserInfoUrl() {return "test";}};
 struct User {int maxthreads;};
 static User processUserInfo(const pugi::xml_document&) {return {maxthreads};}
};
struct ScreenScraperScraper {int getThreadCount(std::string& result);};
int ScreenScraperScraper::getThreadCount(std::string &result)
'''+method+r'''
int main() {
 auto s=Settings::getInstance(); ScreenScraperScraper scraper; std::string error="stale";
 assert(scraper.getThreadCount(error)==1 && calls==0 && error.empty());
 s->user="user";
 assert(scraper.getThreadCount(error)==-1 && calls==0 && error.find("incomplete")!=std::string::npos);
 s->pass="pass";
 assert(scraper.getThreadCount(error)==3 && calls==1 && error.empty());
 status=1;
 assert(scraper.getThreadCount(error)==-1 && calls==2 && error.find("ssuserInfos")!=std::string::npos);
 status=0; validXML=false;
 assert(scraper.getThreadCount(error)==1 && calls==3);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            cpp=Path(directory)/'test.cpp'; binary=Path(directory)/'test'
            cpp.write_text(harness)
            subprocess.run(['g++','-std=c++11','-I'+str(root/'es-core/src'),str(cpp),'-o',str(binary)],check=True,capture_output=True)
            subprocess.run([str(binary)],check=True)

if __name__=='__main__': unittest.main()
