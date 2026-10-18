#include "../es-app/src/RetroPieGamelist.h"
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <string>
#include <sys/stat.h>
#include <unistd.h>

static void directory(const std::string& path)
{
    assert(mkdir(path.c_str(), 0700) == 0);
}
static void create(const std::string& path, const std::string& value)
{
    std::ofstream out(path.c_str());
    assert(out.good());
    out << value;
    out.close();
}
int main()
{
    char name[] = "/tmp/tarave-retropie-metadata-XXXXXX";
    char* temp = mkdtemp(name);
    assert(temp);
    const std::string base(temp);
    const std::string privatePath = base + "/private";
    const std::string roms = base + "/retropiemenu";
    const std::string home = base + "/home";
    const std::string global = base + "/configs";
    const std::string etc = base + "/etc";
    directory(privatePath);
    directory(privatePath + "/gamelists");
    directory(privatePath + "/gamelists/retropie");
    directory(roms);
    directory(home);
    directory(home + "/.emulationstation");
    directory(home + "/.emulationstation/gamelists");
    directory(home + "/.emulationstation/gamelists/retropie");
    directory(global);
    directory(global + "/gamelists");
    directory(global + "/gamelists/retropie");
    directory(etc);
    directory(etc + "/gamelists");
    directory(etc + "/gamelists/retropie");

    using RetroPieGamelist::path;
    const std::string own = privatePath + "/gamelists/retropie/gamelist.xml";
    const std::string original = home + "/.emulationstation/gamelists/retropie/gamelist.xml";
    const std::string globalList = global + "/gamelists/retropie/gamelist.xml";
    const std::string etcList = etc + "/gamelists/retropie/gamelist.xml";
    const std::string romList = roms + "/gamelist.xml";

    // Without metadata, do not create anything under RetroPie or ES-X.
    assert(path(false, privatePath, roms, home, global, etc) == own);
    assert(!RetroPieGamelist::readable(own));

    create(etcList, "etc");
    assert(path(false, privatePath, roms, home, global, etc) == etcList);
    create(globalList, "global");
    assert(path(false, privatePath, roms, home, global, etc) == globalList);

    create(original, "<gameList><game><image>/home/pi/RetroPie/retropiemenu/icons/rpsetup.png</image></game></gameList>");
    assert(path(false, privatePath, roms, home, global, etc) == original);

    create(romList, "rom folder");
    assert(path(false, privatePath, roms, home, global, etc) == romList);

    // Reading is allowed from the original gamelist, but writing NEVER is.
    assert(path(true, privatePath, roms, home, global, etc) == own);
    assert(!RetroPieGamelist::readable(own));
    create(own, "private override");
    assert(path(false, privatePath, roms, home, global, etc) == own);

    std::ifstream previous(original.c_str());
    std::string contents;
    std::getline(previous, contents);
    assert(contents.find("icons/rpsetup.png") != std::string::npos);
    return 0;
}
