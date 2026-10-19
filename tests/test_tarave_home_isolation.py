#!/usr/bin/env python3
"""Source-level regression guard for Tarave's independent config home.

The full build CI separately compiles the frontend. This check ensures the
default is set before Paths/Settings instantiate and that the manual --home
argument is still evaluated after defaults, preserving explicit overrides.
"""
from pathlib import Path

code = (Path(__file__).resolve().parents[1] / "es-app/src/main.cpp").read_text()
start = code.index("bool parseArgs(int argc, char* argv[])")
end = code.index("\n\tfor(int i = 1; i < argc; i++)", start)
parse = code[start:end]

assert "#if !defined(WIN32) && !defined(BATOCERA) && !defined(RETROBAT)" in parse
assert "std::getenv(\"BATOCERA_ES_TEST_HOME\")" in parse
assert "std::getenv(\"HOME\")" in parse
assert '"/.local/share/batocera-es-test"' in parse
assert 'Paths::setHomePath(taraveHome)' in parse
assert 'Paths::setHomePath(argv[i + 1])' in parse
assert parse.index('Paths::setHomePath(taraveHome)') < parse.index('Paths::setHomePath(argv[i + 1])')
assert parse.index('"/.local/share/batocera-es-test"') < parse.index('Paths::setHomePath(argv[i + 1])')
assert "Settings::getInstance()" not in parse.split("// We need to process --home", 1)[0]
print("PASS: standalone direct binary defaults to Tarave's private home, --home still wins")
