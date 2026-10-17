#include "scrapers/Skyscraper.h"
#ifndef WIN32
#include "SystemData.h"
#include "Settings.h"
#include "resources/ResourceManager.h"
#include <pugixml/src/pugixml.hpp>
#include <spawn.h>
#include <sys/wait.h>
#include <signal.h>
#include <unistd.h>
#include <cerrno>
#include <cstdlib>
extern char** environ;

namespace {
class SkyscraperRequest : public ScraperRequest
{
    ScraperSearchParams mParams;
    pid_t mPid = -1;
    std::string mOutput;
public:
    SkyscraperRequest(const ScraperSearchParams& params, std::vector<ScraperSearchResult>& results)
        : ScraperRequest(results), mParams(params) {}
    ~SkyscraperRequest() override
    {
        if (mPid > 0) {
            kill(-mPid, SIGKILL);
            while (waitpid(mPid, nullptr, 0) < 0 && errno == EINTR) {}
        }
        if (!mOutput.empty()) unlink(mOutput.c_str());
    }
    void update() override
    {
        if (mStatus != ASYNC_IN_PROGRESS) return;
        if (mPid < 0) {
            char name[] = "/tmp/batocera-skyscraper-XXXXXX";
            int fd = mkstemp(name);
            if (fd < 0) { setError("Cannot create Skyscraper result file"); return; }
            close(fd);
            mOutput = name;
            std::vector<std::string> args = {"python3",
                ResourceManager::getInstance()->getResourcePath(":/skyscraper-batocera.py"),
                mParams.system->getName(), mParams.system->getStartPath(),
                mParams.game->getPath(), mOutput};
            if (Settings::getInstance()->getBool("ScrapeVideos")) args.push_back("--videos");
            std::vector<char*> argv;
            for (auto& arg : args) argv.push_back(const_cast<char*>(arg.c_str()));
            argv.push_back(nullptr);
            posix_spawnattr_t attr;
            posix_spawnattr_init(&attr);
            posix_spawnattr_setflags(&attr, POSIX_SPAWN_SETPGROUP);
            posix_spawnattr_setpgroup(&attr, 0);
            int error = posix_spawnp(&mPid, "python3", nullptr, &attr, argv.data(), environ);
            posix_spawnattr_destroy(&attr);
            if (error) { mPid = -1; setError("Cannot launch Skyscraper bridge"); }
            return;
        }
        int status = 0;
        auto result = waitpid(mPid, &status, WNOHANG);
        if (result == 0 || (result < 0 && errno == EINTR)) return;
        mPid = -1;
        if (result < 0 || !WIFEXITED(status) || WEXITSTATUS(status) != 0) {
            setError("Skyscraper failed. Check the terminal log and Skyscraper configuration.");
            return;
        }
        pugi::xml_document doc;
        if (!doc.load_file(mOutput.c_str()) || !doc.child("gameList")) {
            setError("Invalid Skyscraper result XML"); return;
        }
        auto game = doc.child("gameList").child("game");
        if (game) {
            ScraperSearchResult found("Skyscraper");
            found.mdl.loadFromXML(GAME_METADATA, game, mParams.system);
            mResults.push_back(found);
        }
        setStatus(ASYNC_DONE);
    }
};
}

bool SkyscraperScraper::isSupportedPlatform(SystemData* system)
{
    return system && system->isGameSystem() && !system->isCollection();
}
const std::set<Scraper::ScraperMediaSource>& SkyscraperScraper::getSupportedMedias()
{
    // Prototype exposes only the option actually forwarded to the bridge.
    static const std::set<ScraperMediaSource> supported = {Video};
    return supported;
}
void SkyscraperScraper::generateRequests(const ScraperSearchParams& params,
    std::queue<std::unique_ptr<ScraperRequest>>& requests,
    std::vector<ScraperSearchResult>& results)
{
    requests.push(std::unique_ptr<ScraperRequest>(new SkyscraperRequest(params, results)));
}
#endif
