#pragma once

// ES-X Next keeps a private --home, but RetroPie provides the descriptions
// and icon paths for its official configuration menu in the *original*
// EmulationStation gamelist. Borrow that XML for reading only: never write to
// the RetroPie or ES-X gamelist and never copy/symlink the user's settings.
#include <fstream>
#include <string>
#include <vector>

namespace RetroPieGamelist
{
inline bool readable(const std::string& path)
{
    return std::ifstream(path.c_str()).good();
}

inline std::string path(bool forWrite,
                        const std::string& privateConfig,
                        const std::string& retropieMenu,
                        const std::string& loginHome,
                        const std::string& globalConfig = "/opt/retropie/configs/all/emulationstation",
                        const std::string& systemConfig = "/etc/emulationstation")
{
    const std::string privateList = privateConfig + "/gamelists/retropie/gamelist.xml";

    // Even if the XML was loaded from ES-X, edits made in Tarave must stay
    // inside Tarave's private .emulationstation/gamelists/retropie.
    if (forWrite)
        return privateList;

    // Private user edits take precedence; everything else is only a fallback.
    std::vector<std::string> candidates;
    candidates.push_back(privateList);
    candidates.push_back(retropieMenu + "/gamelist.xml");

    if (!loginHome.empty())
        candidates.push_back(loginHome + "/.emulationstation/gamelists/retropie/gamelist.xml");

    candidates.push_back(globalConfig + "/gamelists/retropie/gamelist.xml");
    candidates.push_back(systemConfig + "/gamelists/retropie/gamelist.xml");

    for (const auto& candidate : candidates)
        if (readable(candidate))
            return candidate;

    return privateList; // no metadata available; no files created
}
}
