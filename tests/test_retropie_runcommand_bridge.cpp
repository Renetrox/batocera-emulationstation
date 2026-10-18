// Standalone Runcommand backend regression tests.
// Compile: g++ -std=c++11 -Wall -Wextra -pedantic tests/test_retropie_runcommand_bridge.cpp -o /tmp/tarave-runcommand-test
#include "../es-app/src/RetroPieRuncommand.h"
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <unistd.h>

int main()
{
    using namespace RetroPieRuncommand;
    assert(::setenv("TARAVE_USE_RETROPIE_RUNCOMMAND", "0", 1) == 0);
    assert(!enabled());
    assert(::setenv("TARAVE_USE_RETROPIE_RUNCOMMAND", "1", 1) == 0);
    assert(enabled());
    assert(::unsetenv("TARAVE_USE_RETROPIE_RUNCOMMAND") == 0);
    assert(!handlesSystem("retropie"));
    assert(!handlesSystem("ports"));
    assert(!handlesSystem("kodi"));
    assert(!handlesSystem("wine"));
    assert(safeId("lr-mupen64plus-next"));
    assert(!safeId("n64; rm -rf /"));
    assert(romKey("n64", "/home/pi/RetroPie/roms/n64/Super Mario 64 (USA).z64") == "n64_SuperMario64USA");
    assert(romKey("n64", "/roms/n64/Pokémon Stadium.n64") == "n64_PokmonStadium");
    assert(romKey("n64", "/roms/n64/Mario-Kart_64.n64") == "n64_Mario-Kart_64");

    char dir[] = "/tmp/tarave-runcommand-XXXXXX";
    assert(::mkdtemp(dir) != nullptr);
    const std::string path = std::string(dir) + "/emulators.cfg";
    {
        std::ofstream out(path.c_str());
        out << "# keep = this comment\n";
        out << "default = \"lr-mupen64plus\"\n";
        out << "lr-mupen64plus = \"/opt/retropie/supplementary/runcommand/runcommand.sh %ROM%\"\n";
        out << "lr-parallel-n64 = \"retroarch -L parallel_n64_libretro.so %ROM%\"\n";
    }
    assert(getValue(path, "default") == "lr-mupen64plus");
    assert(readEntries(path).size() == 3);
    assert(setValue(path, "default", "lr-parallel-n64"));
    assert(getValue(path, "default") == "lr-parallel-n64");
    assert(getValue(path, "lr-mupen64plus").find("runcommand.sh") != std::string::npos);

    const std::string key = romKey("n64", "/roms/n64/Super Mario 64 (USA).z64");
    assert(setValue(path, key, "lr-mupen64plus"));
    assert(getValue(path, key) == "lr-mupen64plus");
    assert(setValue(path, key, ""));
    assert(getValue(path, key).empty());

    assert(!setValue(path, "default; malicious", "lr-parallel-n64"));
    assert(!setValue(path, "default", "bad value"));
    {
        std::ifstream in(path.c_str());
        std::string first;
        std::getline(in, first);
        assert(first == "# keep = this comment");
    }
    assert(::unlink(path.c_str()) == 0);
    assert(::rmdir(dir) == 0);
    std::cout << "PASS: Runcommand config parser, overrides, atomic writes and ROM keys\n";
}
