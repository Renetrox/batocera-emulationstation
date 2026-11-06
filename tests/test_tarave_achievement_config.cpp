#include "../es-app/src/RetroPieAchievementConfig.h"
#include <cassert>
#include <fstream>
#include <sys/stat.h>
#include <unistd.h>
using namespace RetroPieAchievementConfig;

static void write(const std::string& path, const std::string& text) {
    std::ofstream out(path, std::ios::binary); out << text; out.close(); assert(out.good());
}
int main() {
    char folder[] = "/tmp/tarave-achievements-XXXXXX";
    assert(mkdtemp(folder));
    const std::string path = std::string(folder) + "/retroarch.cfg";
    const std::string backup = path + ".tarave-achievements.bak";
    const std::string original = "# Keep comments\r\nvideo_driver = \"gl\"\r\n"
        "cheevos_username = \"TestUser\"\r\ncheevos_password = \"TEST-SECRET\"\r\n"
        "cheevos_token = \"TEST-TOKEN\"\r\ncheevos_enable = \"false\"\r\n"
        "cheevos_enable = \"true\"\r\n#include \"other.cfg\"\r\n";
    write(path, original); assert(chmod(path.c_str(), 0640) == 0);
#ifdef __linux__
    const bool hasXattrs = ::setxattr(path.c_str(), "user.tarave-test", "keep", 4, 0) == 0;
#endif
#ifdef __linux__
    if (hasXattrs) {
        const std::string staging = path + ".attrs";
        const int fd = ::open(staging.c_str(), O_CREAT | O_RDWR | O_EXCL, 0600);
        assert(fd >= 0);
        assert(::fsetxattr(fd, "user.inherited", "remove", 6, 0) == 0);
        struct stat metadata;
        assert(::stat(path.c_str(), &metadata) == 0);
        assert(copyAttributes(path, fd, metadata));
        assert(::fgetxattr(fd, "user.inherited", nullptr, 0) < 0 && errno == ENODATA);
        char data[4];
        assert(::fgetxattr(fd, "user.tarave-test", data, sizeof(data)) == 4);
        ::close(fd); ::unlink(staging.c_str());
    }
#endif
    auto initial = read(path);
    assert(initial.valid && initial.username == "TestUser");
    assert(initial.option("cheevos_enable") == "true"); // Last key wins.
    assert(initial.options.count("cheevos_password") == 0);
    assert(initial.options.count("cheevos_token") == 0);
    assert(save(path, initial, {{"cheevos_enable", "true"}}).empty());
    assert(access(backup.c_str(), F_OK) != 0); // Unchanged save is byte-identical.
    assert(read(path).content == original);
    assert(!save(path, initial, {{"cheevos_password", "false"}}).empty());
    assert(read(path).content == original);
    assert(!save(path, initial, {{"cheevos_enable", "arbitrary"}}).empty());
    assert(save(path, initial, {{"cheevos_enable", "false"}, {"cheevos_verbose_enable", "true"}}).empty());
    auto changed = read(path);
    assert(changed.option("cheevos_enable") == "false");
    assert(changed.option("cheevos_verbose_enable") == "true");
    assert(changed.content.find("cheevos_password = \"TEST-SECRET\"\r\n") != std::string::npos);
    assert(changed.content.find("cheevos_token = \"TEST-TOKEN\"\r\n") != std::string::npos);
    assert(changed.content.find("#include \"other.cfg\"\r\n") != std::string::npos);
    assert(read(backup).content == original);
    struct stat st, bak;
    assert(stat(path.c_str(), &st) == 0 && (st.st_mode & 0777) == 0640);
    assert(stat(backup.c_str(), &bak) == 0 && (bak.st_mode & 0777) == 0600);
    assert(st.st_uid == getuid());
#ifdef __linux__
    if (hasXattrs) {
        char value[4];
        assert(::getxattr(path.c_str(), "user.tarave-test", value, sizeof(value)) == 4);
        assert(std::string(value, 4) == "keep");
    }
#endif
    assert(!save(path, initial, {{"cheevos_enable", "false"}}).empty()); // Stale editor.
    assert(save(path, changed, {{"cheevos_enable", ""}}).empty());
    assert(read(path).content.find("cheevos_enable =") == std::string::npos);
    const auto current = read(path);
    assert(symlink(path.c_str(), (path + ".link").c_str()) == 0);
    assert(!read(path + ".link").valid);
    assert(!save(path + ".link", current, {{"cheevos_enable", "true"}}).empty());
    assert(read(path).content == current.content);
    assert(link(path.c_str(), (path + ".hard").c_str()) == 0);
    assert(!save(path, current, {{"cheevos_enable", "true"}}).empty());
    unlink((path + ".hard").c_str());
    assert(chmod(path.c_str(), 0440) == 0);
    assert(!save(path, current, {{"cheevos_enable", "true"}}).empty());
    chmod(path.c_str(), 0640);
    assert(!read(path + ".missing").valid);
    // Never create a missing RetroArch config just by opening the menu.
    assert(!save(path + ".missing", Snapshot(), {{"cheevos_enable", "true"}}).empty());
    unlink((path + ".link").c_str()); unlink(backup.c_str()); unlink(path.c_str()); rmdir(folder);
}
