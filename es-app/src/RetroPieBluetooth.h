#pragma once
// Scoped BlueZ bridge for standalone Tarave. No system-wide daemon or sudo.
#include "resources/ResourceManager.h"
#include "utils/FileSystemUtil.h"
#include <atomic>
#include <chrono>
#include <functional>
#include <string>
#include <vector>
#if !defined(WIN32)
#include <unistd.h>
#include <signal.h>
#include <poll.h>
#include <sys/wait.h>
#include <cerrno>
#endif

namespace RetroPieBluetooth {
inline std::atomic<bool>& cancelled() { static std::atomic<bool> value{false}; return value; }
inline void prepareScan() { cancelled() = false; }
inline void stopScan() { cancelled() = true; }
inline std::string helper() {
    return ResourceManager::getInstance()->getResourcePath(":/retropie-bluetooth.py");
}
inline bool available() {
#if !defined(WIN32)
    return Utils::FileSystem::isRegularFile(helper()) &&
        (Utils::FileSystem::isRegularFile("/usr/bin/bluetoothctl") ||
         Utils::FileSystem::isRegularFile("/bin/bluetoothctl"));
#else
    return false;
#endif
}
inline bool run(const std::string& action, const std::string& mac = "",
                const std::function<void(const std::string)>& notify = nullptr) {
#if !defined(WIN32)
    const std::string path = helper();
    if (!Utils::FileSystem::isRegularFile(path)) return false;
    int output[2];
    if (::pipe(output) != 0) return false;
    const pid_t child = ::fork();
    if (child == 0) {
        ::setpgid(0, 0);
        ::close(output[0]);
        ::dup2(output[1], STDOUT_FILENO);
        ::dup2(output[1], STDERR_FILENO);
        ::close(output[1]);
        if (mac.empty())
            ::execlp("python3", "python3", path.c_str(), action.c_str(), (char*)nullptr);
        else
            ::execlp("python3", "python3", path.c_str(), action.c_str(), mac.c_str(), (char*)nullptr);
        _exit(127);
    }
    ::close(output[1]);
    if (child < 0) { ::close(output[0]); return false; }
    ::setpgid(child, child);
    pollfd fd = {output[0], POLLIN, 0};
    std::string pending;
    bool stopped = false;
    bool reportedError = false;
    const auto started = std::chrono::steady_clock::now();
    for (;;) {
        if ((action == "scan" && cancelled()) ||
            (action != "scan" && std::chrono::steady_clock::now() - started > std::chrono::seconds(65)))
            { stopped = true; break; }
        const int ready = ::poll(&fd, 1, 100);
        if (ready < 0) { if (errno == EINTR) continue; stopped = true; break; }
        if (!(fd.revents & (POLLIN | POLLHUP))) continue;
        char buffer[4096];
        const ssize_t count = ::read(output[0], buffer, sizeof(buffer));
        if (count <= 0) break;
        pending.append(buffer, static_cast<size_t>(count));
        size_t end;
        while ((end = pending.find('\n')) != std::string::npos) {
            const auto line = pending.substr(0, end);
            if (line.compare(0, 7, "<error ") == 0) reportedError = true;
            if (notify) notify(line);
            pending.erase(0, end + 1);
        }
        if (pending.size() > 16384) pending.clear();
    }
    // Cancellation kills only this helper's group, never another BT frontend.
    if (stopped) ::kill(-child, SIGKILL);
    ::close(output[0]);
    int status = -1;
    while (::waitpid(child, &status, 0) < 0 && errno == EINTR) {}
    const bool ok = !stopped && status != -1 && WIFEXITED(status) && WEXITSTATUS(status) == 0;
    if (!ok && !(action == "scan" && cancelled()) && notify && !reportedError)
        notify("<error key=\"BLUETOOTH OPERATION FAILED\" />");
    return ok;
#else
    return false;
#endif
}
inline std::vector<std::string> paired() {
    std::vector<std::string> lines;
    run("list", "", [&lines](const std::string& line) { lines.push_back(line); });
    return lines;
}
} // namespace RetroPieBluetooth
