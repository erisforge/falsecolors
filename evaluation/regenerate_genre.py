#!/usr/bin/env python3
"""Genre-transformation prototype: instruct the model to fully reframe
the document genre, not just substitute vocabulary.

The default Method 4 prompt asks for vocabulary substitution within
the source document's structure. The pilot found that the source's
rhetorical framing (CONFIDENTIAL ENGAGEMENT FINDINGS, vulnerability
narrative arc) survives vocabulary substitution and identifies the
source domain to frontier detectors.

This prototype changes the TOPIC string to push the model into a
different document genre entirely: the cover should open, structure,
and conclude as a native brewery audit document, not as a pentest
finding rewritten with brewery vocabulary.
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
TOPIC = (
    "a craft brewery quality control audit memo. The output MUST be "
    "structured as a real brewery audit document: opening with batch "
    "identification and audit scope, listing QC observations and "
    "deviations from spec, concluding with brewmaster recommendations "
    "and corrective actions. Do NOT preserve the source document's "
    "section headings, framing language, or rhetorical structure. "
    "Recast the entire content as if a brewery quality auditor wrote "
    "it from scratch about a real brewery operations issue. The "
    "underlying logical relationships (what causes what, what exceeds "
    "what threshold, what triggers what response) must be preserved, "
    "but the surface document type, opening, structure, voice, and "
    "closing must read as a native brewery audit, not as a transformed "
    "cybersecurity finding"
)
PASSPHRASE = "lach-genre-2026"
OUT = Path(__file__).parent / "results" / "genre_covers_for_lach.json"
DOCS_DIR = Path(__file__).parent / "documents"

doc_paths = sorted(DOCS_DIR.glob("*.txt"))
results = []
for p in doc_paths:
    src = p.read_text()
    print(f"  {MODEL} | {p.name} | genre transformation ...", end=" ", flush=True)
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
