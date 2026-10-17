// Compatibility application identity inherited from ES-X / RetroPie.
// Sources: Renetrox/EmulationStation-X ScreenScraper.h (2999a464)
// and GamesDBJSONScraperResources.cpp (517fd336). Retain upstream attribution.
#pragma once
#include <string>
namespace TaraveScraperCompat {
const std::string API_DEV_U = { 91, 32, 7, 17 };
const std::string API_DEV_P = { 108, 28, 54, 55, 83, 43, 91, 44, 30, 22, 41, 12, 0, 108, 38, 29 };
const std::string API_DEV_KEY = { 54, 73, 115, 100, 101, 67, 111, 107, 79, 66, 68, 66, 67, 56, 118, 77, 54, 88, 101, 54 };
const std::string API_SOFT_NAME = "Emulationstation";
constexpr char GamesDBAPIKey[] = "445fcbc3f32bb2474bc27016b99eb963d318ee3a608212c543b9a79de1041600";
inline std::string decode(const std::string& value) {
    std::string result = value;
    for (size_t i = 0; i < result.size() && i < API_DEV_KEY.size(); ++i)
        result[i] ^= API_DEV_KEY[i];
    return result;
}
inline std::string screenScraperLogin() {
    // URL encoding is done by the native HttpReq implementation.
    return "devid=" + HttpReq::urlEncode(decode(API_DEV_U)) +
        "&devpassword=" + HttpReq::urlEncode(decode(API_DEV_P));
}
}
#if defined(TARAVE_ESX_SCRAPER_COMPAT)
#ifndef SCREENSCRAPER_DEV_LOGIN
#define SCREENSCRAPER_DEV_LOGIN TaraveScraperCompat::screenScraperLogin()
#endif
#ifndef SCREENSCRAPER_SOFTNAME
#define SCREENSCRAPER_SOFTNAME TaraveScraperCompat::API_SOFT_NAME
#endif
#ifndef GAMESDB_APIKEY
#define GAMESDB_APIKEY TaraveScraperCompat::GamesDBAPIKey
#endif
#endif
