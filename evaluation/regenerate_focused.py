#!/usr/bin/env python3
"""Focused cover regeneration: appends to v3_covers_for_lach.json
without re-running models already covered.

Skips qwen3 thinking models (slow, two-step prompt unstable) and
phi3:mini (v3 showed it has compression bias and unsuitable recovery).
Adds covers from gemma3:4b and mistral:7b-instruct to whatever is
already in the JSON.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from falsecolors import encode_document, EMBED_MARKER

MODELS = ["gemma3:4b", "mistral:7b-instruct"]
DOCS_DIR = Path(__file__).parent / "documents"
TOPIC = "brewery"
PASSPHRASE = "lach-pilot-2026"
OUT = Path(__file__).parent / "results" / "v3_covers_for_lach.json"

doc_paths = sorted(DOCS_DIR.glob("*.txt"))
docs = [(p.name, p.read_text()) for p in doc_paths]

results = json.loads(OUT.read_text()) if OUT.exists() else []
done = {(r["model"], r["doc"]) for r in results if "cover_text" in r}
print(f"Already have {len(done)} covers; targeting {len(MODELS)*len(docs)} new")

started = time.time()
for model in MODELS:
    os.environ["OLLAMA_PROMPT_PREFIX"] = ""
    os.environ["OLLAMA_TIMEOUT"] = "300"
    for doc_name, doc_text in docs:
        if (model, doc_name) in done:
            continue
        print(f"  {model} | {doc_name} ...", end=" ", flush=True)
        t0 = time.time()
        try:
            cover_full = encode_document(doc_text, PASSPHRASE, TOPIC,
                                          backend="llm", model=model)
            cover_only = cover_full.split(EMBED_MARKER)[0].strip()
            elapsed = time.time() - t0
            results.append({
                "model": model,
                "doc": doc_name,
                "encode_secs": round(elapsed, 1),
                "cover_chars": len(cover_only),
                "cover_text": cover_only,
                "source_text": doc_text,
            })
            print(f"OK {elapsed:.0f}s ({len(cover_only)} chars)")
        except Exception as e:
            print(f"FAIL {type(e).__name__}: {str(e)[:80]}")
            results.append({"model": model, "doc": doc_name,
                            "error": f"{type(e).__name__}: {e}"[:200]})
        OUT.write_text(json.dumps(results, indent=2))

print(f"\nDone. {len(results)} total cells in {time.time()-started:.0f}s.")
