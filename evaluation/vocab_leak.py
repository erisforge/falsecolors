#!/usr/bin/env python3
"""Measure source-domain vocabulary leak in Method 4 covers.

A "vocab leak" is a source-domain content token that survived
transformation and appears verbatim in the cover. High leak rate
indicates a partial cover whose dominant signal is source content
with surface anomalies, not a transformed cover.

This script computes per-cover leak count and rate, given:
  - the cover text
  - a list of source-domain content tokens to look for

For the v3 source documents (OT/ICS pentest findings) we use a
hand-curated list of high-signal OT terms that should never appear
in a clean brewery cover.

Output is appended to each trial in v3_covers_for_lach.json under
keys leak_terms and leak_count.
"""
import json
import re
import sys
from pathlib import Path

# Hand-curated OT/ICS vocabulary that is operationally significant
# in the source docs and should be substituted by Method 4. Lower-cased
# matching, word-boundary aware. NOT exhaustive; expanded as needed.
OT_TERMS = [
    # Protocols / standards
    "modbus", "modbus tcp", "modbus rtu", "ethernet/ip", "ethernet ip",
    "opc ua", "opc-ua", "dnp3", "profinet", "profibus", "bacnet",
    "hart", "wirelesshart", "s7comm", "goose", "mms", "iec 61850",
    "iec 61511", "iec 62443", "nerc cip", "nist 800-82", "isa 99",
    "isa 84", "iso 27001",
    # Roles / actors
    "scada", "dcs", "plc", "rtu", "ied",
    # Systems / assets
    "safety instrumented system", "sis", "control system",
    "process safety", "interlock", "interlocks", "emergency shutdown",
    "shutdown valve", "engineering workstation", "jump host",
    "data diode",
    # Parameters / addresses
    "holding register", "holding registers", "coil", "coils",
    "register address", "setpoint", "setpoints", "threshold",
    "thresholds", "alarm threshold",
    # Network / zones
    "level 0", "level 1", "level 2", "level 3", "dmz", "perimeter",
    "conduit", "process bus", "bay protection", "merging unit",
    "merging units",
    # CVE / vuln vocab specific to v3 docs
    "cve-", "firmware version", "patch level",
]


def measure_leak(cover_text, terms=OT_TERMS):
    """Return (leak_count, leaked_terms_unique) for a cover."""
    text = cover_text.lower()
    found = []
    for term in terms:
        # Word-boundary match for multi-word terms is tricky with regex
        # so use a simple substring + boundary check
        if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text):
            found.append(term)
    return len(found), found


def annotate_covers_file(path):
    data = json.loads(Path(path).read_text())
    for trial in data:
        if "cover_text" not in trial:
            continue
        n, found = measure_leak(trial["cover_text"])
        trial["leak_count"] = n
        trial["leak_terms"] = found
    Path(path).write_text(json.dumps(data, indent=2))
    return data


if __name__ == "__main__":
    target = (sys.argv[1] if len(sys.argv) > 1
              else "/Users/butterbones/falsecolors/evaluation/results/v3_covers_for_lach.json")
    data = annotate_covers_file(target)
    print(f"Annotated {sum(1 for t in data if 'leak_count' in t)} covers in {target}\n")
    print(f"{'model':30s} {'doc':35s} {'chars':>6s} {'leak':>5s} {'rate':>6s}  {'top leaked terms':40s}")
    for t in data:
        if "cover_text" not in t:
            continue
        rate = t["leak_count"] / max(len(t["cover_text"].split()), 1)
        top = ", ".join(t["leak_terms"][:6])
        print(f"{t['model']:30s} {t['doc']:35s} {t['cover_chars']:6d} {t['leak_count']:5d} {rate*100:5.1f}%  {top}")
