// Read-only RetroArch achievements status parser used by Tarave theme bindings.
#include "../es-app/src/RetroPieAchievements.h"
#include <cassert>
#include <cstdio>
#include <fstream>
#include <string>
#include <unistd.h>

int main()
{
    char path[] = "/tmp/tarave-retroarch-cheevos-XXXXXX";
    const int fd = mkstemp(path);
    assert(fd >= 0);
    close(fd);

    {
        std::ofstream file(path);
        file << "# cheevos_enable = false\n"
             << "cheevos_enable = \"true\"  # enabled\n"
             << "cheevos_username = \"Renetrox#test\"\n"
             << "cheevos_password = \"THIS_SECRET_MUST_NOT_LEAK\"\n"
             << "cheevos_token = \"PRIVATE_TOKEN\"\n";
    }
    auto result = RetroPieAchievements::read(path);
    assert(result.enabled);
    assert(result.username == "Renetrox#test");
    assert(result.username.find("SECRET") == std::string::npos);
    {
        std::ofstream file(path);
        file << "cheevos_enable = 0\n"
             << "cheevos_username = Renetrox ; note\n";
    }
    result = RetroPieAchievements::read(path);
    assert(!result.enabled);
    assert(result.username == "Renetrox");
    {
        std::ofstream file(path);
        file << "cheevos_enable = \"FALSE\"\n"
             << "cheevos_username = \"\"\n";
    }
    result = RetroPieAchievements::read(path);
    assert(!result.enabled && result.username.empty());
    std::remove(path);
    result = RetroPieAchievements::read(path);
    assert(!result.enabled && result.username.empty()); // Missing config.
    return 0;
}
