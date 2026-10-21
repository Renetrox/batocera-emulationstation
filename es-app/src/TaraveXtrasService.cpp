#include "TaraveXtrasService.h"
#include "Paths.h"
#include "Log.h"
#include "resources/ResourceManager.h"
#include "utils/FileSystemUtil.h"
#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <map>
#include <set>
#include <sstream>
#if !defined(WIN32)
#include <pwd.h>
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace {
std::string trim(const std::string& s) {
    const auto a = s.find_first_not_of(" \t\r\n");
    if (a == std::string::npos) return "";
    const auto b = s.find_last_not_of(" \t\r\n");
    return s.substr(a, b - a + 1);
}

std::string loginHome() {
#if !defined(WIN32)
    // The --home argument used by Tarave can point inside its private XDG tree.
    // The real login home is the root of RetroPie-Setup and user ROMs.
    if (const auto* p = getpwuid(getuid()))
        if (p->pw_dir && *p->pw_dir) return p->pw_dir;
#endif
    if (const char* h = std::getenv("HOME"))
        if (*h) return h;
    return Paths::getHomePath();
}

std::string quote(const std::string& str) {
    std::string result = "'";
    for (char c : str)
        if (c == '\'') result += "'\\''";
        else result += c;
    return result + "'";
}

bool token(const std::string& s) {
    if (s.empty() || s == "." || s == ".." || s.find("..") != std::string::npos)
        return false;
    for (unsigned char c : s)
        if (!std::isalnum(c) && c != '-' && c != '_' && c != '.') return false;
    return true;
}

bool filename(const std::string& s) {
    return !s.empty() && s != "." && s != ".." && s.find("..") == std::string::npos &&
           s.find('/') == std::string::npos && s.find('\\') == std::string::npos;
}

std::string value(const std::string& text, const std::string& key) {
    const auto line = trim(text);
    if (line.compare(0, key.size() + 1, key + "=") != 0) return "";
    auto v = trim(line.substr(key.size() + 1));
    if (v.size() > 1 && ((v.front() == '"' && v.back() == '"') ||
                         (v.front() == '\'' && v.back() == '\'')))
        v = v.substr(1, v.size() - 2);
    return v;
}

std::string setupRoot() {
    std::vector<std::string> paths;
    for (const char* var : {"TARAVE_RETROPIE_SETUP", "RETROPIE_SETUP_DIR"}) {
        if (const auto* p = std::getenv(var))
            if (*p) paths.emplace_back(p);
    }
    paths.push_back(loginHome() + "/RetroPie-Setup");
    paths.push_back(loginHome() + "/retropie-setup");
    paths.push_back("/opt/retropie-setup");
    for (const auto& root : paths) {
        if (Utils::FileSystem::isRegularFile(root + "/retropie_packages.sh") &&
            Utils::FileSystem::isDirectory(root + "/scriptmodules"))
            return root;
    }
    LOG(LogWarning) << "X-TRAS: RetroPie-Setup was not found in login HOME or configured paths.";
    return "";
}

std::string gamePath(const std::string& system, const std::string& name) {
    if (!token(system) || !filename(name)) return "";
    return loginHome() + "/RetroPie/roms/" + system + "/" + name;
}

std::string manifestPath() {
    auto p = Paths::getUserEmulationStationPath() + "/xtras/xtras-free-games.ini";
    if (Utils::FileSystem::isRegularFile(p)) return p;
    return ResourceManager::getInstance()->getResourcePath(":/xtras-free-games.ini");
}

struct Game {
    std::string id, system, filename, title, author, license, url;
    bool installed = false;
};

std::vector<Game> games() {
    std::vector<Game> result;
    std::ifstream input(manifestPath());
    std::string id, line;
    std::map<std::string, std::string> props;
    auto flush = [&] {
        if (id.empty()) return;
        auto get = [&](const char* k) {
            const auto it = props.find(k);
            return it != props.end() ? it->second : std::string();
        };
        if (get("ready") != "yes" && get("ready") != "true" && get("ready") != "1") return;
        const auto system = get("system"), file = get("filename"), url = get("download");
        if (!token(id) || !token(system) || !filename(file) ||
            url.compare(0, 8, "https://") != 0) return;
        Game g;
        g.id = id; g.system = system; g.filename = file; g.url = url;
        g.title = get("title"); g.author = get("author"); g.license = get("license");
        g.installed = Utils::FileSystem::isRegularFile(gamePath(system, file));
        result.push_back(g);
    };
    while (std::getline(input, line)) {
        line = trim(line);
        if (line.empty() || line.front() == ';' || line.front() == '#') continue;
        if (line.front() == '[' && line.back() == ']') {
            flush();
            props.clear();
            id = trim(line.substr(1, line.size() - 2));
        } else if (!id.empty()) {
            const auto pos = line.find('=');
            if (pos != std::string::npos)
                props[trim(line.substr(0, pos))] = trim(line.substr(pos + 1));
        }
    }
    flush();
    return result;
}

bool installedModule(const std::string& id) {
    if (id == "bezelproject" && Utils::FileSystem::isRegularFile(
            loginHome() + "/RetroPie/retropiemenu/bezelproject.sh")) return true;
    for (const char* dir : {"/opt/retropie/ports/", "/opt/retropie/emulators/",
                            "/opt/retropie/supplementary/"})
        if (Utils::FileSystem::isRegularFile(std::string(dir) + id + "/retropie.pkg"))
            return true;
    return false;
}

std::vector<PacmanPackage> modules() {
    std::vector<PacmanPackage> result;
    const auto root = setupRoot();
    if (root.empty()) return result;
    const auto ext = root + "/ext";
    std::vector<std::pair<std::string, std::string>> sources;
    sources.emplace_back(root + "/scriptmodules/ports", "RetroPie");
    if (Utils::FileSystem::isDirectory(ext))
        for (const auto& vendor : Utils::FileSystem::getDirContent(ext))
            if (Utils::FileSystem::isDirectory(vendor))
                sources.emplace_back(vendor + "/scriptmodules/ports",
                                     Utils::FileSystem::getFileName(vendor));

    std::set<std::string> known;
    for (const auto& source : sources) {
        if (!Utils::FileSystem::isDirectory(source.first)) continue;
        for (const auto& path : Utils::FileSystem::getDirContent(source.first)) {
            if (Utils::FileSystem::getExtension(path) != ".sh" ||
                !Utils::FileSystem::isRegularFile(path)) continue;
            std::ifstream input(path);
            std::string id, description, section, line;
            while (std::getline(input, line)) {
                auto v = value(line, "rp_module_id");
                if (!v.empty()) id = v;
                v = value(line, "rp_module_desc");
                if (!v.empty()) description = v;
                v = value(line, "rp_module_section");
                if (!v.empty()) section = v;
            }
            if (!token(id) || !known.insert(id).second) continue;
            PacmanPackage p;
            p.name = "module:" + id;
            p.description = description.empty() ? id : description;
            p.repository = "PORTS";
            p.group = source.second == "RetroPie" ? "RetroPie " + section : source.second;
            p.packager = source.second;
            p.available_version = id;
            p.arch = "any";
            p.status = installedModule(id) ? "installed" : "available";
            result.push_back(p);
        }
    }

    // The Bezel Project belongs to RetroPie-Extra's supplementary modules.
    // It must not be hidden merely because it is not a ports/ module.
    const auto addBezel = [&](const std::string& path) {
        if (!Utils::FileSystem::isRegularFile(path)) return;
        std::ifstream input(path);
        std::string line, id, description;
        while (std::getline(input, line)) {
            auto v = value(line, "rp_module_id");
            if (!v.empty()) id = v;
            v = value(line, "rp_module_desc");
            if (!v.empty()) description = v;
        }
        if (id != "bezelproject" || !known.insert(id).second) return;
        PacmanPackage p;
        p.name = "module:bezelproject";
        p.description = description.empty() ? "The Bezel Project" : description;
        p.repository = "HERRAMIENTAS";
        p.group = "RetroPie-Extra";
        p.packager = "RetroPie-Extra";
        p.available_version = "bezelproject";
        p.arch = "any";
        p.status = installedModule("bezelproject") ? "installed" : "available";
        result.push_back(p);
    };
    addBezel(root + "/scriptmodules/supplementary/bezelproject.sh");
    if (Utils::FileSystem::isDirectory(ext))
        for (const auto& vendor : Utils::FileSystem::getDirContent(ext))
            if (Utils::FileSystem::isDirectory(vendor))
                addBezel(vendor + "/scriptmodules/supplementary/bezelproject.sh");
    LOG(LogInfo) << "X-TRAS: found " << result.size() << " RetroPie modules under " << root;
    return result;
}

std::pair<std::string, int> command(const std::string& cmd) {
#if defined(WIN32)
    (void)cmd;
    return {"RetroPie commands are unavailable on this platform.", 1};
#else
    const auto code = std::system(cmd.c_str());
    if (code != -1 && WIFEXITED(code) && WEXITSTATUS(code) == 0) return {"", 0};
    return {"Command failed; check Tarave X-TRAS log and sudo -n permissions.", 1};
#endif
}

std::pair<std::string, int> execute(const std::string& id, bool uninstall,
                                    const std::function<void(const std::string)>& notify) {
    const auto root = setupRoot();
    if (id.compare(0, 5, "game:") == 0) {
        const auto gameId = id.substr(5);
        for (const auto& g : games()) if (g.id == gameId) {
            const auto dst = gamePath(g.system, g.filename);
            if (dst.empty()) break;
            if (uninstall) {
                if (!Utils::FileSystem::isRegularFile(dst)) return {"", 0};
                return std::remove(dst.c_str()) == 0 ?
                    std::make_pair(std::string(), 0) : std::make_pair(std::string("Could not remove ROM."), 1);
            }
            Utils::FileSystem::createDirectory(Utils::FileSystem::getParent(dst));
            const auto tmp = dst + ".tarave-part";
            if (notify) notify("Downloading " + g.title);
            const auto url = quote(g.url), output = quote(tmp);
            const auto log = Paths::getUserEmulationStationPath() + "/xtras/xtras.log";
            Utils::FileSystem::createDirectory(Utils::FileSystem::getParent(log));
            std::remove(tmp.c_str());
            const std::string cmd = "curl --fail --location --proto '=https' --max-time 180 "
                "--silent --show-error -o " + output + " " + url + " >> " + quote(log) + " 2>&1";
            const auto res = command(cmd);
            if (res.second != 0 || !Utils::FileSystem::isRegularFile(tmp)) {
                std::remove(tmp.c_str()); return {"Download failed; see X-TRAS log.", 1};
            }
            std::ifstream check(tmp, std::ios::binary | std::ios::ate);
            if (!check || check.tellg() <= 0) {
                check.close(); std::remove(tmp.c_str());
                return {"Downloaded ROM was empty.", 1};
            }
            check.close();
            if (std::rename(tmp.c_str(), dst.c_str()) != 0) {
                std::remove(tmp.c_str()); return {"Failed to save ROM.", 1};
            }
            return {"", 0};
        }
        return {"Unknown game in X-TRAS catalog.", 1};
    }

    if (id.compare(0, 7, "module:") != 0 || root.empty())
        return {"RetroPie module or RetroPie-Setup unavailable.", 1};
    const auto moduleId = id.substr(7);
    if (!token(moduleId)) return {"Invalid module ID.", 1};

    bool found = false;
    for (const auto& p : modules())
        if (p.name == id) { found = true; break; }
    if (!found) return {"Module not registered in RetroPie-Setup.", 1};

    const auto log = Paths::getUserEmulationStationPath() + "/xtras/xtras.log";
    Utils::FileSystem::createDirectory(Utils::FileSystem::getParent(log));
    if (notify) notify((uninstall ? "Removing " : "Installing ") + moduleId);
    return command("sudo -n " + quote(root + "/retropie_packages.sh") + " " +
        quote(moduleId) + (uninstall ? " remove" : " _autoupdate_") +
        " >> " + quote(log) + " 2>&1");
}
}

namespace TaraveXtrasService {
std::vector<PacmanPackage> list() {
    std::vector<PacmanPackage> out;
    for (const auto& g : games()) {
        PacmanPackage p;
        p.name = "game:" + g.id;
        p.description = g.title.empty() ? g.id : g.title;
        p.repository = "JUEGOS LIBRES";
        p.group = g.system;
        p.packager = g.author;
        p.available_version = g.license;
        p.arch = "any";
        p.status = g.installed ? "installed" : "available";
        out.push_back(p);
    }
    const auto ports = modules();
    out.insert(out.end(), ports.begin(), ports.end());
    return out;
}
std::pair<std::string, int> install(const std::string& id,
   const std::function<void(const std::string)>& notify) {
    return execute(id, false, notify);
}
std::pair<std::string, int> remove(const std::string& id,
   const std::function<void(const std::string)>& notify) {
    return execute(id, true, notify);
}
}
