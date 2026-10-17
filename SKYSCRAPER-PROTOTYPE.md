# Skyscraper GUI prototype

Base: experiment/retropie-standalone-20261013 (9fee99e).

Experimental POSIX provider registered as `Skyscraper` in the existing scraping
screen. Existing providers are retained for comparison. It uses the native
per-game queue, native progress, and native metadata import/recovery path.
Skyscraper performs gather then generation per selected ROM. The generated XML
is temporary and never replaces the live gamelist; generated media is written
to the real system's media directory. Cache, account, and artwork configuration
come from the user's Skyscraper configuration, as with ES-X.

Requirements: python3 and Skyscraper in PATH, configured for ScreenScraper.
The helper is installed with the resources directory. No shell interpolation is
used for ROM paths. Each helper has its own process group for cancellation.

## Validation performed

`python3 -m unittest discover -s tests -v`: four tests passed using a mocked
Skyscraper process: exact selected-game import, absolute path conversion and
live gamelist preservation (including shell-special filenames), gather error
propagation, outside-root rejection, and missing binary handling.
`git diff --check`: passed.

Full C++ build and live GUI/network scraping have NOT been tested. This runtime
has no cmake, pkg-config, SDL development dependencies, or Skyscraper binary.
Do not treat this branch as ready to replace the working frontend.

## Remaining work

- Validate compilation and GUI behavior on Linux/Orange Pi.
- Refresh filter/system controls when the native provider selector changes.
- Map Batocera platform aliases to Skyscraper platform IDs; the prototype passes
  the system name directly and lets Skyscraper reject unknown IDs.
- Map language, artwork, region, accounts, and media overwrite policy explicitly.
  Currently the bridge defaults to English, forwards the video toggle, and uses
  the existing Skyscraper artwork/configuration. Other native options must not
  be assumed to control Skyscraper yet.
- Implement missing-media predicates independently of provider capabilities.
  The prototype only advertises video, so use the ALL filter for initial tests.
- Name override and interactive candidate selection are not implemented.
- Improve structured errors, cross-process cache locking, graceful cancellation,
  timeouts, and batching for large collections. Current process cancellation is
  forceful; failed/cancelled runs may leave temporary directories or media.
- Test favorites, statistics, collections, and recovery behavior end-to-end.

For an initial on-device test, compile with the same standalone settings used
for the working branch, choose Skyscraper, set GAMES TO SCRAPE FOR to ALL and
select a small system. Start from a backed-up test collection. Existing native
account fields do not configure Skyscraper in this prototype.
