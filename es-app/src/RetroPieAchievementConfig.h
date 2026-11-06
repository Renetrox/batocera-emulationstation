#pragma once
// Only public option keys are editable. Credential/token lines remain opaque.
#include "RetroPieAchievements.h"
#include <map>
#include <sstream>
#include <cstdlib>
#include <set>
#include <string>
#include <vector>
#ifndef WIN32
#include <fcntl.h>
#include <sys/stat.h>
#ifdef __linux__
#include <sys/xattr.h>
#endif
#include <unistd.h>
#include <cerrno>
#include <cstdio>
#endif

namespace RetroPieAchievementConfig {
inline const std::vector<std::string>& keys() {
    static const std::vector<std::string> list = {
        "cheevos_enable", "cheevos_hardcore_mode_enable", "cheevos_leaderboards_enable",
        "cheevos_verbose_enable", "cheevos_richpresence_enable", "cheevos_start_active",
        "cheevos_auto_screenshot", "cheevos_challenge_indicators", "cheevos_test_unofficial",
        "cheevos_unlock_sound_enable"};
    return list;
}
inline bool allowed(const std::string& key) {
    for (const auto& item : keys()) if (item == key) return true;
    return false;
}
inline std::string keyOf(const std::string& line) {
    const auto text = RetroPieAchievements::trim(line);
    if (text.empty() || text[0] == '#' || text[0] == ';') return "";
    const auto eq = text.find('=');
    return eq == std::string::npos ? "" : RetroPieAchievements::trim(text.substr(0, eq));
}
struct Snapshot {
    bool valid = false;
    std::string content;
    std::map<std::string, std::string> options;
    std::string username;
    std::string option(const std::string& key) const {
        const auto found = options.find(key);
        return found == options.end() ? "" : found->second;
    }
};
inline Snapshot read(const std::string& path) {
    Snapshot snapshot;
#ifndef WIN32
    const int fd = ::open(path.c_str(), O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return snapshot;
    struct stat st;
    if (::fstat(fd, &st) != 0 || !S_ISREG(st.st_mode) || st.st_size > 4 * 1024 * 1024) {
        ::close(fd); return snapshot;
    }
    char buffer[4096];
    ssize_t count;
    while ((count = ::read(fd, buffer, sizeof(buffer))) != 0) {
        if (count < 0) { if (errno == EINTR) continue; ::close(fd); return Snapshot(); }
        snapshot.content.append(buffer, static_cast<size_t>(count));
        if (snapshot.content.size() > 4 * 1024 * 1024) { ::close(fd); return Snapshot(); }
    }
    ::close(fd);
    std::istringstream lines(snapshot.content);
    std::string line;
    while (std::getline(lines, line)) {
        const auto key = keyOf(line);
        // Never parse password/token values or expose them to the UI.
        if (!allowed(key) && key != "cheevos_username") continue;
        const auto value = RetroPieAchievements::value(line.substr(line.find('=') + 1));
        if (key == "cheevos_username") snapshot.username = value;
        else {
            const auto lower = RetroPieAchievements::lower(value);
            snapshot.options[key] = lower == "true" || lower == "1" ? "true" :
                                    lower == "false" || lower == "0" ? "false" : "";
        }
    }
    snapshot.valid = true;
#endif
    return snapshot;
}

#ifndef WIN32
inline bool writeAll(int fd, const std::string& data) {
    size_t offset = 0;
    while (offset < data.size()) {
        const auto count = ::write(fd, data.data() + offset, data.size() - offset);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) return false;
        offset += static_cast<size_t>(count);
    }
    return ::fsync(fd) == 0;
}
inline bool copyAttributes(const std::string& path, int destination, const struct stat& expected) {
#ifdef __linux__
    const int source = ::open(path.c_str(), O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (source < 0) return false;
    struct stat st;
    if (::fstat(source, &st) != 0 || st.st_dev != expected.st_dev || st.st_ino != expected.st_ino) {
        ::close(source); return false;
    }
    const auto count = ::flistxattr(source, nullptr, 0);
    if (count < 0) { const bool unsupported = errno == ENOTSUP; ::close(source); return unsupported; }
    std::vector<char> names(static_cast<size_t>(count));
    bool ok = count == 0 || ::flistxattr(source, names.data(), names.size()) == count;
    size_t offset = 0;
    while (ok && offset < names.size()) {
        const std::string name(names.data() + offset);
        const auto length = ::fgetxattr(source, name.c_str(), nullptr, 0);
        if (length < 0) { ok = false; break; }
        std::vector<char> value(static_cast<size_t>(length));
        ok = ::fgetxattr(source, name.c_str(), value.data(), value.size()) == length &&
             ::fsetxattr(destination, name.c_str(), value.data(), value.size(), 0) == 0;
        offset += name.size() + 1;
    }
    ::close(source);
    return ok;
#else
    return true;
#endif
}
inline bool stagedFile(const std::string& path, const std::string& data,
                       const struct stat& st, bool backup, std::string& temporary) {
    std::vector<char> name(path.begin(), path.end());
    const std::string suffix = ".tarave-XXXXXX";
    name.insert(name.end(), suffix.begin(), suffix.end()); name.push_back('\0');
    const int fd = ::mkstemp(name.data());
    if (fd < 0) return false;
    temporary = name.data();
    struct stat created;
    bool ok = ::fstat(fd, &created) == 0;
    if (ok && !backup && (created.st_uid != st.st_uid || created.st_gid != st.st_gid))
        ok = ::fchown(fd, st.st_uid, st.st_gid) == 0;
    if (ok) ok = ::fchmod(fd, backup ? 0600 : st.st_mode & 0777) == 0;
    if (ok && !backup) ok = copyAttributes(path, fd, st);
    if (ok) ok = writeAll(fd, data);
    if (::close(fd) != 0) ok = false;
    if (!ok) { ::unlink(temporary.c_str()); temporary.clear(); }
    return ok;
}
#endif

// An empty value removes the explicit key, restoring RetroArch's default.
// Returns translation keys, never config contents or credential values.
inline std::string save(const std::string& path, const Snapshot& original,
                        const std::map<std::string, std::string>& requested) {
    std::map<std::string, std::string> changes;
    if (!original.valid) return "RETROARCH CONFIGURATION COULD NOT BE READ";
    for (const auto& item : requested) {
        if (!allowed(item.first) || (item.second != "" && item.second != "true" && item.second != "false"))
            return "RETROARCH SETTINGS COULD NOT BE SAVED";
        if (item.second != original.option(item.first)) changes.insert(item);
    }
    if (changes.empty()) return ""; // No write, backup or permission changes.
#ifndef WIN32
    const auto current = read(path);
    if (!current.valid) return "RETROARCH CONFIGURATION COULD NOT BE READ";
    if (current.content != original.content) return "RETROARCH CONFIGURATION CHANGED. REOPEN THIS MENU.";
    struct stat st;
    if (::lstat(path.c_str(), &st) != 0 || !S_ISREG(st.st_mode) || st.st_nlink != 1 || (st.st_mode & 0222) == 0 || ::access(path.c_str(), W_OK) != 0)
        return "RETROARCH SETTINGS COULD NOT BE SAVED";
    std::string output;
    size_t start = 0;
    const std::string newline = original.content.find("\r\n") != std::string::npos ? "\r\n" : "\n";
    while (start < original.content.size()) {
        const auto end = original.content.find('\n', start);
        const auto size = end == std::string::npos ? original.content.size() - start : end - start + 1;
        const auto line = original.content.substr(start, size);
        if (changes.find(keyOf(line)) == changes.end()) output += line;
        start += size;
    }
    for (const auto& item : changes) {
        if (item.second.empty()) continue;
        if (!output.empty() && output.back() != '\n') output += newline;
        output += item.first + " = \"" + item.second + "\"" + newline;
    }
    std::string staged, backup;
    if (!stagedFile(path, output, st, false, staged)) return "RETROARCH SETTINGS COULD NOT BE SAVED";
    if (!stagedFile(path, original.content, st, true, backup)) {
        ::unlink(staged.c_str()); return "RETROARCH SETTINGS COULD NOT BE SAVED";
    }
    // Reject edits made while staging, rather than overwrite a newer config.
    const auto finalCheck = read(path);
    if (!finalCheck.valid || finalCheck.content != original.content) {
        ::unlink(staged.c_str()); ::unlink(backup.c_str());
        return "RETROARCH CONFIGURATION CHANGED. REOPEN THIS MENU.";
    }
    if (::rename(backup.c_str(), (path + ".tarave-achievements.bak").c_str()) != 0) {
        ::unlink(staged.c_str()); ::unlink(backup.c_str());
        return "RETROARCH SETTINGS COULD NOT BE SAVED";
    }
    if (::rename(staged.c_str(), path.c_str()) != 0) {
        ::unlink(staged.c_str()); return "RETROARCH SETTINGS COULD NOT BE SAVED";
    }
    return "";
#else
    return "RETROARCH SETTINGS COULD NOT BE SAVED";
#endif
}
} // namespace RetroPieAchievementConfig
