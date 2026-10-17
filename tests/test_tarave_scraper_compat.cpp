// Standalone compile check for native provider macros and override precedence.
#include <cassert>
#include <string>
class HttpReq {
public:
    static std::string urlEncode(const std::string& value) {
        const char* digits = "0123456789ABCDEF";
        std::string out;
        for (unsigned char ch : value) {
            if ((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') ||
                (ch >= '0' && ch <= '9') || ch == '-' || ch == '_' || ch == '.') out += ch;
            else { out += '%'; out += digits[ch >> 4]; out += digits[ch & 15]; }
        }
        return out;
    }
};
#include "../es-app/src/scrapers/TaraveScraperCompat.h"
#ifndef SCREENSCRAPER_DEV_LOGIN
#error Native ScreenScraper must be available in compatibility builds
#endif
#ifndef GAMESDB_APIKEY
#error Native TheGamesDB must be available in compatibility builds
#endif
int main() {
#ifdef TEST_OVERRIDES
    assert(std::string(SCREENSCRAPER_DEV_LOGIN) == "custom-login");
    assert(std::string(GAMESDB_APIKEY) == "custom-key");
    assert(std::string(SCREENSCRAPER_SOFTNAME) == "custom-name");
#else
    auto login = std::string(SCREENSCRAPER_DEV_LOGIN);
    assert(login.find("devid=") == 0);
    auto separator = login.find("&devpassword=");
    assert(separator != std::string::npos && separator > 6);
    assert(login.size() > separator + 13);
    assert(login.find(' ') == std::string::npos);
    assert(!std::string(GAMESDB_APIKEY).empty());
    assert(!std::string(SCREENSCRAPER_SOFTNAME).empty());
    const auto& value = TaraveScraperCompat::API_DEV_U;
    auto decoded = TaraveScraperCompat::decode(value);
    for (size_t i=0; i<value.size(); ++i)
        assert((decoded[i] ^ TaraveScraperCompat::API_DEV_KEY[i]) == value[i]);
#endif
}
