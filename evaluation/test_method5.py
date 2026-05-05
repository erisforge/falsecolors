#!/usr/bin/env python3
"""End-to-end test of Method 5 (Graph Shift) on 4 source documents:
3 OT/ICS pentest findings (existing v3 cohort) + 1 fresh geopolitical
intelligence assessment.

For each document:
  1. Encode via Method 5 with topic 'craft brewery quality control audit'
  2. Score the cover via Sonnet 4.6 + Opus 4.7 (source-identification rule)
  3. Decode and compare to source (recovery ratio via difflib)
  4. Annotate vocab leak

Outputs: evaluation/results/method5_test.json
"""
import difflib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation"))

from falsecolors import encode_document, decode_document, EMBED_MARKER
from detector import score_cover

MODEL = "gemma3:4b"
TOPIC = "craft brewery quality control audit"
PASSPHRASE = "method5-test-2026"
DOCS = [
    "01_reactor_sis_bypass.txt",
    "02_water_scada_creds.txt",
    "03_substation_iec61850.txt",
    "04_geopolitical_intel.txt",
]
DOCS_DIR = ROOT / "evaluation" / "documents"
OUT = ROOT / "evaluation" / "results" / "method5_test.json"

results = []
for doc_name in DOCS:
    src = (DOCS_DIR / doc_name).read_text()
    print(f"\n=== {doc_name} ===")
    t0 = time.time()
    try:
        encoded = encode_document(src, PASSPHRASE, TOPIC, backend="llm",
                                   model=MODEL, method="graph")
    except Exception as e:
        print(f"  encode FAIL: {type(e).__name__}: {e}")
        results.append({"doc": doc_name, "error": str(e)[:200]})
        continue
    encode_secs = time.time() - t0
    cover_only = encoded.split(EMBED_MARKER)[0].strip()
    print(f"  encoded in {encode_secs:.0f}s ({len(cover_only)} chars)")

    # Score covers
    is_geopolitical = "geopolitical" in doc_name
    expected_source = "political" if is_geopolitical else "ot_ics"

    sonnet = score_cover(cover_only, model="claude-sonnet-4-6", api="anthropic")
    opus = score_cover(cover_only, model="claude-opus-4-7", api="anthropic")
    sonnet_detected = sonnet["source_domain_guess"] == expected_source
    opus_detected = opus["source_domain_guess"] == expected_source
    print(f"  sonnet: p={sonnet['p_cover']:.2f} guess={sonnet['source_domain_guess']} -> {'DETECTED' if sonnet_detected else 'EVADED'}")
    print(f"  opus:   p={opus['p_cover']:.2f} guess={opus['source_domain_guess']} -> {'DETECTED' if opus_detected else 'EVADED'}")

    # Decode and measure recovery
    try:
        recovered = decode_document(encoded, PASSPHRASE)
        recovery = difflib.SequenceMatcher(None, src, recovered).ratio()
    except Exception as e:
        recovered = ""
        recovery = 0.0
        print(f"  decode FAIL: {type(e).__name__}: {e}")
    print(f"  round-trip recovery (difflib ratio): {recovery:.3f}")

    results.append({
        "doc": doc_name,
        "expected_source_domain": expected_source,
        "encode_secs": round(encode_secs, 1),
        "cover_chars": len(cover_only),
        "cover_text": cover_only,
        "recovered": recovered[:5000],
        "recovery_ratio": round(recovery, 4),
        "sonnet": {
            "p_cover": sonnet["p_cover"],
            "is_cover": sonnet["is_cover"],
            "guess": sonnet["source_domain_guess"],
            "detected": sonnet_detected,
            "reasoning": sonnet["reasoning"][:500],
        },
        "opus": {
            "p_cover": opus["p_cover"],
            "is_cover": opus["is_cover"],
            "guess": opus["source_domain_guess"],
            "detected": opus_detected,
            "reasoning": opus["reasoning"][:500],
        },
    })
    OUT.write_text(json.dumps(results, indent=2))

print()
print("==== METHOD 5 SUMMARY ====")
sonnet_evasions = sum(1 for r in results if not r.get("sonnet", {}).get("detected", True))
opus_evasions = sum(1 for r in results if not r.get("opus", {}).get("detected", True))
mean_recovery = (sum(r.get("recovery_ratio", 0) for r in results)
                  / max(len(results), 1))
print(f"  documents: {len(results)}")
print(f"  Sonnet evasions: {sonnet_evasions}/{len(results)}")
print(f"  Opus evasions:   {opus_evasions}/{len(results)}")
print(f"  mean recovery (difflib): {mean_recovery:.3f}")
print(f"  full results: {OUT}")
