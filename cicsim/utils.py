#!/usr/bin/env python3

def parse_runfile(path):
    """Read a runfile and return a list of stripped, non-empty lines."""
    entries = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                entries.append(line)
    return entries
