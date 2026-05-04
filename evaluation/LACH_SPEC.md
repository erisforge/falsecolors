# LACH: LLM-Adversarial Cover Hardening

**Status:** Draft 0.1. Specification for the v4 evaluation harness extension.
**Owner:** River Caudle.
**Depends on:** existing v3 evaluation infrastructure (`evaluation/run.py`, `evaluation/results-v3-twostep.json`, `falsecolors.py` Method 4 backend).
**Companion roadmap:** `ROADMAP.md` Section "Step 1: LACH".

---

## 1. Goal

Replace the v3 evaluation's reliance on Caudle Distance against a fixed reference corpus with an empirical, frontier-LLM-bounded measurement of cover-document distinguishability. Produce a new metric `Adv_D` (detector-bounded adversary advantage) reportable per (model, document, trial) alongside `recovery_ratio`, `scd`, and `mapping_supported_ratio`. Optionally close the loop with an encode-time rewrite layer that uses the detector's reasoning as a constraint signal.

The first-class deliverable is the measurement instrument. The defense layer is secondary and only built if measurement reveals a gap worth closing.

## 2. Theoretical framing

### 2.1 The Detector-Bounded Distinguishing Game

Section 2.17 of `Eris_FALSECOLORS_v3.md` defines the Semantic Distinguishing Game with adversary advantage bounded by the total variation distance between cover and native distributions. That bound is information-theoretic and not directly measurable. LACH introduces a measurable variant.

**Game 2.17b.X (Detector-Bounded Distinguishing Game).** Challenger C and detector adversary D play:

1. **Setup.** C selects a domain pair (T_a, T_b), a relational graph G, and an isomorphism M from S(G, T_a, T_b). C prepares source D = (G, L_a) and cover C_doc = (G, M ∘ L_a). C also samples native document N from the natural cover-domain distribution.
2. **Challenge.** C flips a fair coin b. If b = 0, C sends N to D. If b = 1, C sends C_doc to D.
3. **Detection.** D outputs a binary guess b' and a confidence score p ∈ [0, 1] for "this is a cover."
4. **Advantage.** `Adv_D = | P(b' = 1 | b = 1) - P(b' = 1 | b = 0) |` measured over many independent trials.

Adv_D is the operational adversary advantage against the named detector D. Theorem 2.17.3 still bounds the information-theoretic advantage; Adv_D measures the realized advantage of a specific detector. The two are linked by `Adv_D <= Adv_information-theoretic` for any computable D, but Adv_D is what the user actually faces.

### 2.2 Three sub-tasks

The detector D performs three tasks, each scored independently:

1. **Detection.** Binary cover-or-native classification, with confidence score. Yields `Adv_D` per the game above.
2. **Classification.** If D guesses "cover," guess the source domain from a closed candidate set (e.g., {OT/ICS, political SITREP, legal contract, medical, financial, none-of-above}). Yields `cls_acc_D` accuracy.
3. **Inversion.** Propose a partial inverse mapping: for k randomly chosen cover-domain content tokens, propose the most likely source-domain term. Yields `inv_acc_D` (fraction of proposals matching the true mapping).

Detection is the headline metric. Classification and inversion characterize how much an adversary who has decided "this is a cover" can recover beyond the binary fact.

## 3. Threat model

**LACH defends against:**
- A passive observer who runs a frontier LLM as a triage filter over collected documents.
- An active investigator who suspects a specific user is using FALSECOLORS and queries an LLM to evaluate documents found in their possession.
- A cloud LLM provider running automated content-classification on inputs, with frontier-LLM detectors in the loop.

**LACH does NOT defend against:**
- An adversary with the passphrase or with access to the embedded key.
- Side-channel attacks (timing, length, file metadata).
- Detectors strictly stronger than the one in the LACH loop. Robustness is detector-relative by construction.
- Statistical attacks that do not rely on LLM-mediated reasoning (Caudle Distance still measures these).
- Adversaries who already know the source domain and are doing targeted search (the Distinguishing Game assumes the adversary does not already know the answer).

## 4. Architecture

### 4.1 Phase 1: Measurement (no defense)

```
v3 eval harness                            LACH addition
+-----------------+                       +-------------------+
| run.py          |                       |  detector.py      |
| produces        | ---- cover_only ----> |  prompts adversary|
| (cover, key,    |                       |  LLM 3 ways       |
| recovery, scd)  |                       |  returns scores   |
+-----------------+                       +---------+---------+
                                                    |
                                                    v
                                          +-------------------+
                                          |  results.json     |
                                          |  + adv_d, cls_acc,|
                                          |    inv_acc fields |
                                          +-------------------+
```

The existing `run_one(model, doc_text, corpus_text)` signature stays the same. After computing `recovery_ratio` and `scd`, call `evaluate_against_detector(cover_only, doc_text, domain_map)` and merge its output dict into the trial result.

For the negative set (b = 0 case in the game), sample paragraphs from the brewery corpus matched in length to the cover. Run those through the same detector with the same prompt. Adv_D is computed across all trials, not per-trial.

### 4.2 Phase 2: Defense (encode-time rewrite loop)

Built only if Phase 1 shows Adv_D significantly > 0 for any (model, document) cell.

```
encode_document(...)
    |
    v
llm_translate(...)   -> cover_v0, mapping
    |
    v
detector.score(cover_v0)
    |
    v
if score > threshold:
    rewrite_prompt = build_constraint(detector_reasoning, mapping)
    cover_v1 = llm_rewrite(cover_v0, rewrite_prompt)
    verify_mapping_support(cover_v1, mapping)  # must still hold
    iterate up to N times or until score <= threshold
return cover_final, mapping
```

The rewrite loop is opt-in via `--harden` flag on `encrypt`, similar to the existing `--polish` flag. Default off to preserve v3 behavior and avoid the latency hit.

## 5. Components

### 5.1 `evaluation/detector.py`

Single new file. Responsibilities:

- `score_cover(text, model, api) -> dict` runs the three-task prompt against the named adversary model and returns `{"is_cover": bool, "p_cover": float, "domain_guess": str, "inv_proposals": dict[str, str], "raw": str}`.
- `evaluate_against_detector(cover_only, source, domain_map) -> dict` orchestrates one detection trial and one matched native-paragraph trial, returns merged metrics.
- Adapter pattern for the API: start with Anthropic Messages API (Claude Opus 4.7 as the adversary), add OpenAI and Gemini adapters as second pass.

Pure stdlib for the orchestration, `urllib` for the API call (consistent with `falsecolors.py`'s zero-deps style).

### 5.2 `evaluation/score.py`

Aggregation script. Takes the trial-level `results.json` (now including detector fields) and produces:

- Per-(model, document) Adv_D with confidence intervals.
- Pooled Adv_D across all trials (the headline number).
- Confusion matrix for cover vs native classification.
- Per-(model, document) classification accuracy on the source-domain task.
- Inversion accuracy distribution.

### 5.3 `falsecolors.py` additions (Phase 2 only)

- `harden_cover(cover, mapping, source, topic, detector_model, max_iters=3)` is the rewrite loop.
- `--harden` flag on `encrypt` subcommand.
- New `_build_rewrite_prompt(cover, mapping, detector_reasoning)` helper.

No changes to the encode/decode contract: `decode_document` does not need to know whether `--harden` was used.

## 6. Detector prompt design

The detector prompt is the most consequential single design choice. It controls the adversary's strength and therefore the meaningful range of `Adv_D`.

### 6.1 Baseline (zero-shot) prompt

```
You are reviewing a document to determine if it is genuine native-domain
content or a covertly transformed version of a sensitive source document
that was rewritten to appear as innocuous content in an unrelated domain.

A "covertly transformed document" is one where:
- The vocabulary belongs to one domain (e.g. brewing, gardening) but the
  underlying logical structure was originally about a different domain
  (e.g. industrial control systems, political analysis, legal contracts).
- The relational structure (causation, measurement, conditionals,
  enumeration) is preserved but the surface vocabulary is substituted.

Document to evaluate:
---
{cover_or_native}
---

Respond in JSON only, with this exact schema:

{
  "is_cover": <bool>,
  "p_cover": <float in [0, 1]>,
  "reasoning": <string, max 200 words explaining the cues you used>,
  "source_domain_guess": <one of: "ot_ics", "political", "legal",
                          "medical", "financial", "none_of_above", "unsure">,
  "inversion_proposals": {
    "<cover_term>": "<your guess at the source-domain original>",
    ...
  }
}

For inversion_proposals, list 3 to 8 cover-domain content terms that
look most likely to be substitutions, and your best guess at what they
were originally. If you believe this is genuine native content, return
an empty object.
```

### 6.2 Few-shot strengthened prompt

A second variant that includes 2-3 demonstration pairs of (native, cover) with the cover labeled. Used to characterize how much detection improves with examples. Reported as `Adv_D_fewshot` alongside `Adv_D_zeroshot`.

### 6.3 Adversary model selection

Default: `claude-opus-4-7`. Reasoning: contemporary frontier model, accessible via Anthropic API, instruction-following strong enough for structured JSON output.

Cross-checks (Phase 1 stretch goal): GPT-5 or whatever is current, Gemini 2.5+ Pro, Llama 3.3 405B via a hosted endpoint. Cross-checking guards against detector-overfit: if Adv_D varies wildly across detectors, the metric is detector-specific in a way the user must account for.

## 7. Negative set construction

Adv_D requires both b=1 (cover) and b=0 (native) trials. The b=0 set construction matters as much as the cover set.

**Construction rule:** for each (model, document) cell that produces N cover trials, sample N matched native paragraphs from `evaluation/corpora/brewery.txt` such that each native paragraph has token count within +/- 20% of its paired cover. Run the detector on each native paragraph with the same prompt as the cover. Pool b=0 outputs across the (model, document) cell.

**Why matched length:** length is a trivial detection feature. If covers are systematically longer than the native corpus, the detector will exploit length and Adv_D will be inflated by a non-semantic signal. Matched-length sampling controls for this.

**Stretch goal:** expand the brewery corpus to 5000+ words across more sub-genres (audit reports, brewmaster logs, regulatory submissions, trade press) to give the negative-paragraph sampling room. This is partially done in v2 expansion already.

## 8. Reporting format

The headline table for the v4 RESULTS.md:

| Model | Doc | Recovery | SCD | Adv_D (zero) | Adv_D (few) | Cls Acc | Inv Acc |
|---|---|---|---|---|---|---|---|
| mistral:7b | 01_reactor | 0.94 | 1.21 | 0.62 | 0.81 | 0.70 | 0.45 |
| mistral:7b | 02_water | 0.91 | 1.18 | 0.55 | 0.76 | 0.65 | 0.38 |
| ... | ... | ... | ... | ... | ... | ... | ... |

Plus rolled-up "model-level" rows averaging across documents.

A pooled-across-everything single number: **Adv_D = X (95% CI [Y, Z])** is the v4 headline.

## 9. Implementation plan

### Week 1: Detector module skeleton
- `detector.py` with Anthropic adapter
- Zero-shot prompt drafted, tested on 5 hand-picked covers and 5 native paragraphs
- Output JSON validated, fallback path for malformed responses
- No integration with `run.py` yet

### Week 2: Negative-set construction
- Paragraph extractor over `brewery.txt` with length-matching logic
- Test that paired (cover, native) pairs are length-balanced within 20%
- Verify the detector's responses on natives look reasonable (low p_cover)

### Week 3: Integration with run.py
- Add `evaluate_against_detector` call in `run_one`
- Update `results.json` schema with new fields
- Run a small pilot: 1 model, 1 document, 5 trials, end-to-end
- Validate: all fields populate, no crashes, latency acceptable

### Week 4: Full evaluation pass
- Run the full LACH-extended eval: 6 models x 3 docs x 10 trials = 180 cover trials, plus 180 matched native trials. Total adversary calls: 360.
- Estimated cost at Claude Opus 4.7 pricing: roughly $15-30 depending on token counts.
- Generate `results-v4-lach.json`

### Week 5: Aggregation and reporting
- `score.py` produces the pooled Adv_D and per-cell tables
- Draft the RESULTS.md v4 section
- Cross-check with at least one second adversary model (GPT or Gemini) on a 30-trial subset

### Week 6: Detector-Bounded Distinguishing Game in the paper
- Add Section 2.17b (or revise 2.17) with the new game
- Update Section 7.9 to reference Adv_D
- Decide whether Phase 2 (rewrite loop) is worth building based on Phase 1 results

## 10. Open questions

1. **Adversary model pinning.** Adv_D is detector-relative. Should the v4 paper pin a specific model+version (e.g. `claude-opus-4-7-20260301`) as the canonical D, or report against multiple detectors? Pinning is reproducible but ages quickly; multi-detector is robust but expensive.

2. **What confidence score to use.** Anthropic API does not return token logprobs. Using the model's self-reported `p_cover` is convenient but possibly unreliable (LLMs are notoriously miscalibrated on confidence). Alternative: ask the model 5 times with temperature > 0 and use the fraction of "is_cover": true responses as the score. More expensive but more reliable.

3. **Inversion grading.** The inversion task asks the detector to guess source-domain originals for selected cover terms. Grading "correct" requires comparing against the true mapping. Exact-match is harsh (model says "valve" instead of "actuator"). Need a synonym-tolerant grading function. Probably: a small per-domain synonym dictionary plus exact-match fallback.

4. **Negative-set domain match.** Brewery natives are the obvious negative set when topic="brewery". What if v4 evaluations expand to other cover topics (garden, novel)? Each topic needs its own native corpus. Scope creep risk.

5. **Cost ceiling.** Each LACH trial adds 1 to 3 frontier-LLM calls (zero-shot, few-shot, possibly 5x for self-consistency). At 360 base trials and average 2 calls each, that's 720 frontier calls per evaluation pass. Cost is manageable for one eval but limits how many sweeps are feasible during development.

6. **Defense-evaluation contamination.** If Phase 2 (rewrite loop) is built, the rewrite uses the detector. Then evaluating the hardened cover against the same detector is in-distribution and will overstate effectiveness. Need a separate held-out detector for evaluation. This doubles the API cost during Phase 2 evaluation.

## 11. What success looks like

**Minimum viable success (Phase 1 only):**
- `Adv_D` is computed and reported for all v3 cohort cells.
- The number is honest (matched negatives, no length-cheating, validated detector behavior).
- A new section in the v4 RESULTS.md reframes the Caudle Distance commentary in light of measured Adv_D.
- A new game in the paper formalizes what was measured.

This alone is publishable as "we measured what FALSECOLORS actually defends against modern adversaries, and here is the gap."

**Full success (Phase 1 + Phase 2):**
- The rewrite loop reduces Adv_D by a measurable amount on at least one (model, document) cell without dropping `recovery_ratio` below the v3 0.92 floor.
- Cost-benefit data lets the user choose: "is the latency hit worth the Adv_D reduction?"

**Failure modes that are still publishable:**
- Adv_D is high across all cells and the rewrite loop cannot reduce it without breaking recovery. This is the negative result: current FALSECOLORS Method 4 is not robust against frontier-LLM adversaries; v4 must commit to Apocrypha or another structural change.
- Adv_D is low across all cells. This is the positive surprise: frontier LLMs are bad at detecting semantic domain shift, and FALSECOLORS' v3 recovery numbers are operationally sufficient.
- Adv_D varies wildly across detectors. The metric is detector-specific in a way that requires the v4 paper to recommend an adversary tier rather than a single number.

All four outcomes (success, partial success, full failure, surprise) yield reportable findings. The investment is justified regardless of which way the empirical chips fall.

## 12. Out of scope for this spec

- The Apocrypha implementation. LACH is the measurement instrument; Apocrypha is one of the things to measure with it. Separate spec when Phase 1 is in.
- The Caudle Accountant. Depends on multi-query empirical data that LACH does not produce in a single pass.
- Multi-detector ensemble methods (e.g., majority vote across 3 detectors). Possible Phase 1.5 if cross-checking shows high inter-detector variance.
- Adversary models other than instruction-tuned chat LLMs (e.g., embedding-based detectors trained specifically on FALSECOLORS covers). Different threat model, different paper.
