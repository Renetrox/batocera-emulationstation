#pragma once
// Read-only RetroAchievements status for Tarave themes on RetroPie.
//
// RetroPie configures RetroArch itself; Tarave should not infer achievements
// from a private Batocera setting or copy passwords/tokens into ES settings.
// This adapter reads ONLY the global enabled flag and public username.
// Per-core or per-game RetroArch overrides remain the emulator's authority.
#include <algorithm>
#include <cctype>
#include <fstream>
#include <string>

namespace RetroPieAchievements
{
struct Status
{
    bool enabled = false;
    std::string username;
};

inline std::string trim(const std::string& raw)
{
    const auto start = raw.find_first_not_of(" \t\r\n");
    if (start == std::string::npos)
        return "";
    const auto end = raw.find_last_not_of(" \t\r\n");
    return raw.substr(start, end - start + 1);
}

inline std::string lower(std::string value)
{
    std::transform(value.begin(), value.end(), value.begin(),
        [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    return value;
}

inline std::string value(const std::string& raw)
{
    const std::string v = trim(raw);
    if (v.empty())
        return "";
    if (v.front() == '"')
    {
        // RetroArch normally writes quoted values. Do not treat a # or ;
        // inside a quoted username as a comment delimiter.
        const auto end = v.find('"', 1);
        return end != std::string::npos ? v.substr(1, end - 1) : "";
    }
    // Support unquoted values and trailing config comments as well.
    return trim(v.substr(0, v.find_first_of("#;")));
}

inline Status read(const std::string& path)
{
    Status status;
    std::ifstream input(path.c_str());
    std::string line;
    while (std::getline(input, line))
    {
        line = trim(line);
        if (line.empty() || line[0] == '#' || line[0] == ';')
            continue;
        const auto equals = line.find('=');
        if (equals == std::string::npos)
            continue;
        const std::string key = trim(line.substr(0, equals));
        // Avoid parsing or copying RetroArch's secret credential/token values.
        if (key != "cheevos_enable" && key != "cheevos_username")
            continue;
        const std::string val = value(line.substr(equals + 1));
        if (key == "cheevos_enable")
            status.enabled = lower(val) == "true" || val == "1";
        else
            status.username = val;
    }
    return status;
}

inline Status read()
{
    return read("/opt/retropie/configs/all/retroarch.cfg");
}
} // namespace RetroPieAchievements
