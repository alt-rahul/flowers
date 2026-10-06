# Makefile: build instructions. Run `make` in this folder.
#
# HOW C++ IS BUILT
#   Each .cpp file is COMPILED into machine code, then the pieces are LINKED
#   together into one program. `make` reads this file, works out what needs
#   (re)building, and runs the compiler for you.
#
# HOW A MAKEFILE READS
#   target: things it depends on
#   <TAB>command that builds the target
#   `make` rebuilds a target whenever one of its dependencies is newer.
#
# THE PROGRAMS (put in bin/)
#   bin/experiments  runs the bots on many random trials, writes a CSV
#   bin/analyze      turns one or more of those CSVs into summary tables
#   bin/tests        checks that everything works

# The compiler and its options:
#   -std=c++17           use the 2017 C++ standard
#   -O2                  optimise (the program runs much faster)
#   -Wall -Wextra        turn on warnings about suspicious code
#   -pedantic            warn about non-standard code
#   -ffp-contract=off    do every floating-point step separately, exactly as
#                        written (no fused multiply-add), so the same input
#                        gives the same numbers on every compiler and machine
CXX = g++
CXXFLAGS = -std=c++17 -O2 -Wall -Wextra -pedantic -ffp-contract=off

# The shared code that the simulation programs use.
LIB = src/ship.cpp src/fire.cpp src/planning.cpp src/planners.cpp src/bots.cpp src/simulation.cpp
HEADERS = src/common.hpp src/ship.hpp src/fire.hpp src/planning.hpp src/planners.hpp \
          src/bots.hpp src/simulation.hpp

all: bin/experiments bin/tests bin/analyze

# $@ means "the target being built", $< means "the first dependency".
bin/experiments bin/tests: bin/%: src/%.cpp $(LIB) $(HEADERS)
	mkdir -p bin
	$(CXX) $(CXXFLAGS) -o $@ $< $(LIB)

# The analysis tool only reads CSV files, so it needs none of the shared code.
bin/analyze: src/analyze.cpp
	mkdir -p bin
	$(CXX) $(CXXFLAGS) -o $@ $<

test: bin/tests
	./bin/tests

clean:
	rm -rf bin

# These names are commands, not files.
.PHONY: all test clean
