#!/usr/bin/env python3
"""Generate gemma3:4b covers using tabletop RPG rulebook as the cover
domain to test whether a structurally-rich-but-different-vocabulary
domain reduces vocabulary leak vs brewery."""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from falsecolors import encode_document, EMBED_MARKER

MODEL = "gemma3:4b"
TOPIC = "tabletop role playing game rulebook covering combat actions, ability checks, and edge case rulings"
PASSPHRASE = "lach-rpg-2026"
OUT = Path(__file__).parent / "results" / "rpg_covers_for_lach.json"
DOCS_DIR = Path(__file__).parent / "documents"

doc_paths = sorted(DOCS_DIR.glob("*.txt"))
results = []
for p in doc_paths:
    src = p.read_text()
    print(f"  {MODEL} | {p.name} | topic=RPG rulebook ...", end=" ", flush=True)
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
