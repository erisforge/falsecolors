#!/usr/bin/env python3
"""Apocrypha v0.1 prototype: single-shot fictional-world cover.

Replaces the static cover-domain TOPIC with a generative directive
that asks the LLM to invent a self-consistent fictional world per
document. No code changes to falsecolors.py; just a different TOPIC
string. The LLM does the world-spec invention and the cover generation
in the same Method 4 two-step prompt flow.

This is the cheapest Apocrypha prototype. If the leak rate drops
materially vs brewery and RPG, the structural-isomorphism conjecture
(Observation 4.2.5 of LACH paper) is supported and a real
implementation with skeleton extraction + World Spec + key embedding
is justified.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from falsecolors import encode_document, EMBED_MARKER

MODEL = "gemma3:4b"
TOPIC = ("a self-consistent fictional setting of your invention with novel "
         "proper nouns, an invented governing body, a coined process taxonomy, "
         "and its own internal physics or rules. Pick something distinctive "
         "(magical academy, alien colony, dieselpunk research commune, ancient "
         "guild charter, parallel-dimension diplomatic corps). Use the same "
         "structural pattern as the source document but rewrite all "
         "domain-specific terms into the fictional vocabulary you create")
PASSPHRASE = "lach-apocrypha-2026"
OUT = Path(__file__).parent / "results" / "apocrypha_covers_for_lach.json"
DOCS_DIR = Path(__file__).parent / "documents"

doc_paths = sorted(DOCS_DIR.glob("*.txt"))
results = []
for p in doc_paths:
    src = p.read_text()
    print(f"  {MODEL} | {p.name} | apocrypha v0.1 ...", end=" ", flush=True)
    os.environ["OLLAMA_TIMEOUT"] = "300"
    t0 = time.time()
    try:
        cover_full = encode_document(src, PASSPHRASE, TOPIC, backend="llm",
                                      model=MODEL)
        cover = cover_full.split(EMBED_MARKER)[0].strip()
        elapsed = time.time() - t0
        results.append({"model": MODEL, "doc": p.name, "topic": TOPIC,
                        "encode_secs": round(elapsed, 1),
                        "cover_chars": len(cover),
                        "cover_text": cover, "source_text": src})
        print(f"OK {elapsed:.0f}s ({len(cover)} chars)")
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        results.append({"model": MODEL, "doc": p.name,
                        "error": f"{type(e).__name__}: {e}"})
    OUT.write_text(json.dumps(results, indent=2))

print(f"\nDone. Wrote {OUT}")
