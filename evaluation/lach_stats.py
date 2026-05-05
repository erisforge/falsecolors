#!/usr/bin/env python3
"""LACH cross-detector statistics utilities.

Loads per-trial JSON outputs from evaluation/results/, aligns trials
across detectors by (corpus or cover, paragraph_idx or model+doc),
computes pairwise Cohen's kappa on binary is_cover classifications,
and summarizes Adv_D when both TPR (covers) and FPR (natives) are
available.

Requires the evaluation venv: numpy + scipy.
"""
import json
import os
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np
from scipy import stats

RESULTS = Path("/Users/butterbones/falsecolors/evaluation/results")


def cohens_kappa(rater_a, rater_b):
    """Compute Cohen's kappa between two binary raters on the same items.
    Each rater is a list of bools (or 0/1)."""
    assert len(rater_a) == len(rater_b)
    a = np.array(rater_a, dtype=int)
    b = np.array(rater_b, dtype=int)
    n = len(a)
    if n == 0:
        return float("nan")
    po = np.mean(a == b)
    pa = np.sum(a == 1) / n
    pb = np.sum(b == 1) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    if abs(1 - pe) < 1e-9:
        # Both raters give the same constant; kappa undefined
        return float("nan") if po < 1 else 1.0
    return (po - pe) / (1 - pe)


def wilson_95(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def load_fpr_results():
    """Load all lach_fpr_*.json files, keyed by (corpus, detector)."""
    out = {}
    for f in RESULTS.glob("lach_fpr_*.json"):
        d = json.loads(f.read_text())
        corpus = os.path.basename(d["corpus"]).replace(".txt", "")
        det = f"{d['detector']['api']}/{d['detector']['model']}"
        out[(corpus, det)] = d
    return out


def load_tpr_results():
    """Load all lach_tpr_*.json files, keyed by detector."""
    out = {}
    for f in RESULTS.glob("lach_tpr_*.json"):
        d = json.loads(f.read_text())
        det = f"{d['detector']['api']}/{d['detector']['model']}"
        out[det] = d
    return out


def report_fpr_table():
    print("==== FPR baselines per (corpus, detector) ====\n")
    rows = []
    for (corpus, det), d in sorted(load_fpr_results().items()):
        n = d["n_parsed"]
        fp = d["fp_count"]
        lo, hi = d["wilson_95_ci"]
        rows.append((corpus, det, n, fp, d["fpr"], d["mean_p_cover"], lo, hi))
    print(f"{'corpus':22s} {'detector':45s} {'n':>4s} {'fp':>4s} {'fpr':>6s} {'mean_p':>7s} {'95% CI':>16s}")
    for r in rows:
        c, d, n, fp, fpr, mp, lo, hi = r
        print(f"{c:22s} {d:45s} {n:4d} {fp:4d} {fpr:6.3f} {mp:7.3f} [{lo:.3f}, {hi:.3f}]")


def report_tpr_table():
    tprs = load_tpr_results()
    if not tprs:
        print("\n[no TPR results yet; run score_covers.py first]\n")
        return
    print("\n==== TPR per detector (covers from results-v3-twostep cohort) ====\n")
    print(f"{'detector':45s} {'n':>4s} {'tp':>4s} {'tpr':>6s} {'mean_p':>7s} {'95% CI':>16s}")
    for det, d in sorted(tprs.items()):
        n = d["n_parsed"]
        tp = d["tp_count"]
        lo, hi = d["wilson_95_ci"]
        print(f"{det:45s} {n:4d} {tp:4d} {d['tpr']:6.3f} {d['mean_p_cover']:7.3f} [{lo:.3f}, {hi:.3f}]")


def report_adv_d():
    """Compute Adv_D = TPR - FPR per detector, pooling across cover domains."""
    fprs = load_fpr_results()
    tprs = load_tpr_results()
    if not tprs:
        return
    # For Adv_D we need the FPR on the same cover domain as the covers
    # (brewery for now) at the same detector.
    print("\n==== Adv_D = TPR - FPR (paired by detector and brewery cover domain) ====\n")
    print(f"{'detector':45s} {'TPR':>6s} {'FPR':>6s} {'Adv_D':>7s}")
    for det, t in sorted(tprs.items()):
        # find brewery_v4 fpr for the same detector
        f = fprs.get(("brewery_v4", det))
        if f is None:
            continue
        tpr, fpr = t["tpr"], f["fpr"]
        adv = abs(tpr - fpr)
        print(f"{det:45s} {tpr:6.3f} {fpr:6.3f} {adv:7.3f}")


def report_cross_detector_kappa():
    """Compute pairwise Cohen's kappa on the binary is_cover labels for
    detectors that scored the same paragraphs. Aligns by paragraph
    preview text (short prefix used as the key in our pilot files)."""
    fprs = load_fpr_results()
    # Group detectors by corpus
    by_corpus = defaultdict(dict)
    for (corpus, det), d in fprs.items():
        by_corpus[corpus][det] = d

    print("\n==== Pairwise Cohen's kappa on FPR sets (binary is_cover labels) ====\n")
    for corpus, dets in sorted(by_corpus.items()):
        print(f"  corpus={corpus}")
        det_names = sorted(dets.keys())
        # Build per-detector dict: paragraph_preview -> is_cover
        det_labels = {}
        for d in det_names:
            trials = dets[d]["trials"]
            det_labels[d] = {t["preview"]: bool(t["is_cover"])
                             for t in trials if t.get("parse_ok")}
        # Pairwise
        for i, a in enumerate(det_names):
            for b in det_names[i+1:]:
                shared = set(det_labels[a]) & set(det_labels[b])
                if not shared:
                    continue
                ra = [det_labels[a][p] for p in shared]
                rb = [det_labels[b][p] for p in shared]
                k = cohens_kappa(ra, rb)
                # Both detectors fully agree on all-native -> kappa is
                # undefined (1.0 perfect agreement; report as such)
                agree = sum(1 for x, y in zip(ra, rb) if x == y) / len(ra)
                print(f"    {a:45s} vs {b:45s} n={len(shared):3d} agree={agree:.2%} kappa={k:.3f}")
        print()


if __name__ == "__main__":
    report_fpr_table()
    report_tpr_table()
    report_adv_d()
    report_cross_detector_kappa()
