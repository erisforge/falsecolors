#!/usr/bin/env python3
"""Score regenerated v3 covers via the LACH detector.

Reads results/v3_covers_for_lach.json, scores each cover through the
named detector, and writes per-trial detection results to
results/lach_tpr_<api>_<model>.json. Uses concurrent.futures for
parallel API calls.

Usage:
  python3 score_covers.py <api> <model> [<concurrency>]
"""
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, "/Users/butterbones/falsecolors/evaluation")
from detector import score_cover

API = sys.argv[1]
MODEL = sys.argv[2]
CONC = int(sys.argv[3]) if len(sys.argv) > 3 else 3

IN = os.environ.get("LACH_COVERS_IN", "/Users/butterbones/falsecolors/evaluation/results/v3_covers_for_lach.json")
data = json.load(open(IN))
trials = [t for t in data if "cover_text" in t and not t.get("error")]
print(f"Scoring {len(trials)} covers via {API}/{MODEL} with concurrency={CONC}")

def one(trial):
    r = score_cover(trial["cover_text"], model=MODEL, api=API)
    return {
        "model": trial["model"],
        "doc": trial["doc"],
        "p_cover": r["p_cover"],
        "is_cover": r["is_cover"],
        "guess": r["source_domain_guess"],
        "parse_ok": r["parse_ok"],
        "reasoning": r["reasoning"][:400],
        "inversion_proposals": list(r.get("inversion_proposals", {}).keys())[:5],
    }

results = []
t0 = time.time()
with ThreadPoolExecutor(max_workers=CONC) as ex:
    futures = {ex.submit(one, t): t for t in trials}
    for fut in as_completed(futures):
        try:
            r = fut.result()
        except Exception as e:
            t = futures[fut]
            r = {
                "model": t["model"], "doc": t["doc"], "error": f"{type(e).__name__}: {e}"[:200],
                "p_cover": 0.5, "is_cover": False, "guess": "unsure", "parse_ok": False,
            }
        flag = "TP" if r.get("is_cover") else "FN"
        if not r.get("parse_ok"):
            flag = "PARSE_FAIL"
        print(f"  [{len(results)+1:02d}/{len(trials)}] {flag:10s} p={r.get('p_cover',0):.2f} guess={r.get('guess','?'):14s} {r['model']} | {r['doc']}")
        results.append(r)

elapsed = time.time() - t0
ok = [r for r in results if r.get("parse_ok")]
n = len(ok)
tp = sum(1 for r in ok if r["is_cover"])
mean_p = sum(r["p_cover"] for r in ok) / n if n else 0
correct_cls = sum(1 for r in ok if r["is_cover"] and r["guess"] == "ot_ics") / max(tp, 1)

def wilson(k, n, z=1.96):
    if n == 0:
        return 0, 0
    p = k / n
    d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return max(0, c-h), min(1, c+h)
lo, hi = wilson(tp, n)

print()
print(f"==== TPR SUMMARY ({elapsed:.1f}s) ====")
print(f"  parsed: {n}/{len(results)}")
print(f"  TPR: {tp}/{n} = {tp/n if n else 0:.3f}  Wilson 95% CI: [{lo:.3f}, {hi:.3f}]")
print(f"  classification accuracy on flagged covers: {correct_cls:.3f}")
print(f"  mean p_cover on covers: {mean_p:.3f}")

# Per-model breakdown
by_model = {}
for r in ok:
    by_model.setdefault(r["model"], []).append(r["p_cover"])
print("\n  per-model mean p_cover:")
for m, ps in sorted(by_model.items()):
    fp_rate = sum(1 for p in ps if p > 0.5) / len(ps)
    print(f"    {m:30s} mean_p={sum(ps)/len(ps):.3f} flagged={fp_rate:.0%} n={len(ps)}")

tag = os.environ.get("LACH_TAG", "v3")
out_name = f"lach_tpr_{tag}_{API}_{MODEL.replace('/','_')}.json"
out_path = f"/Users/butterbones/falsecolors/evaluation/results/{out_name}"
out = {
    "detector": {"api": API, "model": MODEL},
    "n_scored": len(results),
    "n_parsed": n,
    "tp_count": tp,
    "tpr": tp/n if n else 0,
    "wilson_95_ci": [lo, hi],
    "mean_p_cover": mean_p,
    "elapsed_secs": elapsed,
    "trials": results,
}
with open(out_path, "w") as f:
    json.dump(out, f, indent=2)
print(f"\n  wrote {out_path}")
