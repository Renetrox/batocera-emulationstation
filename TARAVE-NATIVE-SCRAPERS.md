# Native scrapers in standalone Tarave-ES

Standalone builds now default to the same application identity already present
in ES-X/RetroPie for ScreenScraper and TheGamesDB. This enables the existing
native C++ implementations and preserves Tarave's current scraping UI, media
options, batch processing, and manual search. No Skyscraper process or Python
helper is used by these native providers.

The inherited constants remain in their upstream encoded representation where
applicable; this is not secret storage. Attribution and source blob revisions
are recorded in TaraveScraperCompat.h. The ScreenScraper software base name is
kept as Emulationstation and the native code adds the current version.
Application identity is separate from a personal account. Personal ScreenScraper
credentials are read from the existing ACCOUNTS tab. TheGamesDB does not use
those ScreenScraper account fields.

Build switches:
- TARAVE_ESX_SCRAPER_COMPAT=ON (default for non-Batocera/non-Retrobat builds).
- TARAVE_ENABLE_SKYSCRAPER=OFF (default; hides the external prototype).
- Explicit SCREENSCRAPER_DEV_LOGIN, SCREENSCRAPER_SOFTNAME, and GAMESDB_APIKEY
  build settings override the compatibility defaults.

Changing provider now rebuilds the filters and compatible system list. Existing
settings pointing to the hidden Skyscraper provider fall back to an available
native provider when opening the scraping screen. Choose ScreenScraper or
TheGamesDB explicitly and start with one game.

## Validation

Two standalone C++11 harness builds passed: inherited provider macro wiring,
encoded identity decoding/URL formatting, and explicit override precedence.
These harnesses use a minimal HttpReq URL-encoding stand-in, not the live API.
The existing 11 Python bridge tests also pass; git diff --check passes.
Full frontend compilation and live provider responses have not been verified
in this runtime. CMake and the GUI development dependencies are unavailable.
Inherited API identities may be revoked or subject to provider quotas; a live
request on the target machine is still required. Personal credentials cannot
repair a rejected application identity.

The ES-X J2ME/MIDlet search improvements are NOT ported by this change. Tarave's
platform enumeration differs; that is separate work. ScreenScraper's existing
quota/account preflight and native media implementation remain in use.
