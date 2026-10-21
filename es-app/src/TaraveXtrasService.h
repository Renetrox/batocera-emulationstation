#pragma once
#include "ApiSystem.h"
#include <functional>
#include <string>
#include <utility>
#include <vector>

// RetroPie backend for Batocera-ES's native Content Downloader widget.
// Does not replace Batocera services on native Batocera builds.
namespace TaraveXtrasService {
    std::vector<PacmanPackage> list();
    std::pair<std::string, int> install(const std::string& id,
        const std::function<void(const std::string)>& notify = nullptr);
    std::pair<std::string, int> remove(const std::string& id,
        const std::function<void(const std::string)>& notify = nullptr);
}
