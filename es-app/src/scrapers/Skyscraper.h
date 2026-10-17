#pragma once
#include "scrapers/Scraper.h"

// Experimental POSIX bridge: native GUI, external Skyscraper engine.
class SkyscraperScraper : public Scraper
{
public:
    bool isSupportedPlatform(SystemData* system) override;
    const std::set<ScraperMediaSource>& getSupportedMedias() override;
protected:
    void generateRequests(const ScraperSearchParams& params,
        std::queue<std::unique_ptr<ScraperRequest>>& requests,
        std::vector<ScraperSearchResult>& results) override;
};
