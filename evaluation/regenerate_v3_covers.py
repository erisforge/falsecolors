#!/usr/bin/env python3
"""Regenerate a sample of v3 covers for LACH TPR estimation.

The v3 results-v3-twostep.json stores trial metadata but not the cover
text itself. To estimate TPR against frontier detectors we need the
actual covers. This script regenerates one cover per (model, doc) cell
using the v3 two-step prompt that's already the default in
falsecolors.py, and writes them to a JSON for downstream scoring.

Output: evaluation/results/v3_covers_for_lach.json
Cost: zero (local Ollama). Wall time: ~10 minutes for 18 cells.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from falsecolors import encode_document, EMBED_MARKER

MODELS = [
    "llama3.2:3b",
    "qwen3:1.7b",
    "phi3:mini",
    "gemma3:4b",
    "mistral:7b-instruct",
    "llama3.1:8b",
]
DOCS_DIR = Path(__file__).parent / "documents"
PROMPT_PREFIX = {
    "qwen3:1.7b": "/no_think\n",
    "qwen3:4b": "/no_think\n",
    "qwen3:8b": "/no_think\n",
}
TOPIC = "brewery"
PASSPHRASE = "lach-pilot-2026"
OUT = Path(__file__).parent / "results" / "v3_covers_for_lach.json"

doc_paths = sorted(DOCS_DIR.glob("*.txt"))
docs = [(p.name, p.read_text()) for p in doc_paths]

results = []
total = len(MODELS) * len(docs)
n = 0
started = time.time()

for model in MODELS:
    os.environ["OLLAMA_PROMPT_PREFIX"] = PROMPT_PREFIX.get(model, "")
    os.environ["OLLAMA_TIMEOUT"] = "600"
    for doc_name, doc_text in docs:
        n += 1
        tag = f"[{n}/{total}] {model} | {doc_name}"
        print(tag, "...", end=" ", flush=True)
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
            results.append({
                "model": model,
                "doc": doc_name,
                "error": f"{type(e).__name__}: {e}"[:200],
            })
        # Persist after each trial in case of interrupt
        OUT.write_text(json.dumps(results, indent=2))

elapsed = time.time() - started
print(f"\nDone. {len(results)} cells in {elapsed:.0f}s. Wrote {OUT}")
