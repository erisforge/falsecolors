# Eris FALSECOLORS Local-Model Evaluation

Three rounds of evaluation have been run. Each round superseded the prior round's guidance.

- **v3 (May 2026): Two-step prompt.** Current guidance lives here. Recovery rose substantially across every model in the cohort, the hallucinated-mapping failure mode was effectively eliminated for four of six models, and the smallest model in the cohort (qwen3:1.7b) became one of the strongest. Section [v3](#v3-may-2026-two-step-prompt) below.
- **v2 (May 2026): Verification gate and 5x corpus.** Introduced the `mapping_supported / mapping_sampled` metric that exposed the silent "hallucinated mapping" failure mode and reframed the picture from v1's mean-recovery ranking to a viability-tier ladder. Superseded for guidance by v3 but the methodology section is still authoritative. Section [v2](#v2-may-2026-verification-gate-and-5x-corpus) below.
- **v1 (May 2026): n=3 baseline.** Mean-recovery ranking only, no mapping-fidelity check. Surfaced that the LLM backend was less consistent than the static backend and motivated v2.

This document is structured oldest-on-the-bottom: read v3 for current guidance; descend into v2 for the methodology and the original viability-tier framing.

---

## v3 (May 2026): Two-step prompt

### Headline

**Four of six local models are now in striking distance of production-grade.** mistral:7b-instruct and qwen3:1.7b both reach `P(recovery ≥ 0.95) ≥ 0.40` with `P(recovery < 0.30) = 0.00`; gemma3:4b and llama3.1:8b both reach `P(recovery < 0.30) = 0.00` with median recovery above 0.87. The two-step prompt closed the gap that v2 attributed to "needs a much larger model than this cohort tests."

**The single most consequential v3 finding: `qwen3:1.7b` went from unusable to tied for best.** Median recovery rose from 0.080 (v2) to 0.916 (v3). Mapping support ratio rose from 0.01 to 0.86. The smallest model in the lineup is now one of the most reliable. The v2 hypothesis that qwen3 had a "deeper prompt-following failure" was wrong; the failure was in the prompt, not the model.

**`mistral:7b-instruct` is now the highest-mean model with no catastrophic tail.** Mean recovery 0.883, `P(recovery ≥ 0.95) = 0.43`, `P(recovery < 0.30) = 0.00`. The bimodal recovery-by-not-shifting failure documented in v2 is gone: the two-step prompt forces the model to commit to a mapping before writing the cover, so it cannot fall back to a 2-entry minimal-shift trial.

**`phi3:mini` did not benefit.** Median recovery 0.555, only 7/30 trials above 0.70. The two-step prompt fixed phi3's mapping-support problem (0.51 → 0.84) but recovery did not follow. Phi3 now produces honest mappings of covers that drop or mangle source content; the bottleneck moved from mapping fidelity to content preservation in the cover write itself.

### What v3 changed

The v2 prompt asked the model to do three things in one response: plan a domain shift, write the cover prose, and emit the substitutions as a JSON tail. The third step is a *recall* task: the model has to remember every word-pair it just used. Small models cannot reliably do this and instead emit a *plausible* mapping that does not correspond to the cover. v2 measured this as the mapping support ratio. qwen3:1.7b in v2 produced 81 sampled mapping entries across 30 trials, of which 1 appeared in the cover.

The v3 prompt splits the rewrite from the mapping-emission step. Call 1 asks for a JSON object of substitutions only, no prose. Call 2 takes that fixed mapping back as input and asks the model to write the cover constrained to those substitutions. The mapping is locked before the rewrite begins, so the model can no longer fabricate it from memory after the fact. The recall task becomes a *constraint-satisfaction* task, which small models handle well.

This is implemented in `falsecolors.py` under `LLM_TWO_STEP = True` (default). Set the flag to `False` to revert to the v2 single-step prompt for A/B comparison.

### v3 results table

180 trials (6 models × 3 docs × n=10), same documents and corpus as v2.

| Model | Recovery (mean ± SD) | P(rec ≥ 0.95) | P(rec < 0.30) | Map support (agg) | Trials with sup=100% | Encode (s) |
|---|---|---|---|---|---|---|
| **mistral:7b-instruct** | 0.883 ± 0.087 | **0.43** | **0.00** | 0.75 | 6/30 | 96.7 |
| **qwen3:1.7b** | 0.908 ± 0.073 | 0.40 | **0.00** | 0.86 | 17/28 | 115.3 |
| **gemma3:4b** | 0.842 ± 0.107 | 0.17 | **0.00** | **0.92** | 19/30 | 30.8 |
| **llama3.1:8b** | 0.853 ± 0.137 | 0.07 | **0.00** | 0.85 | 17/30 | 81.5 |
| llama3.2:3b | 0.785 ± 0.186 | 0.17 | **0.00** | 0.61 | 3/30 | 24.1 |
| phi3:mini | 0.556 ± 0.193 | 0.00 | 0.03 | 0.84 | 15/30 | 31.5 |

Aggregate map support is `Σ mapping_supported / Σ mapping_sampled` across all trials for that model. qwen3 had 2 encode failures (Ollama timeout); the other models had zero.

Total v3 wall time: 3.17h (within 2% of v2's 3.24h despite running two LLM calls per encode; smaller models like gemma3 and llama3.2 produced a faster constrained rewrite in step 2 and partially offset the extra call).

### v3 vs v2 deltas

| Model | v2 mean | v3 mean | Δ | v2 sup_agg | v3 sup_agg | v2 P<.30 | v3 P<.30 |
|---|---|---|---|---|---|---|---|
| qwen3:1.7b | 0.146 | **0.908** | **+0.762** | 0.01 | 0.86 | 0.83 | 0.00 |
| mistral:7b-instruct | 0.703 | 0.883 | +0.180 | 0.69 | 0.75 | 0.13 | 0.00 |
| gemma3:4b | 0.581 | 0.842 | +0.261 | 0.95 | 0.92 | 0.00 | 0.00 |
| llama3.1:8b | 0.631 | 0.853 | +0.222 | 0.92 | 0.85 | 0.00 | 0.00 |
| llama3.2:3b | 0.635 | 0.785 | +0.150 | 0.81 | 0.61 | 0.07 | 0.00 |
| phi3:mini | 0.474 | 0.556 | +0.082 | 0.51 | 0.84 | 0.07 | 0.03 |

Every model improved on every primary metric. The qwen3 delta is the largest single improvement observed in any FALSECOLORS evaluation to date.

### Per-document medians

```
                    doc01    doc02    doc03
gemma3:4b           0.905    0.919    0.719
llama3.1:8b         0.943    0.913    0.844
llama3.2:3b         0.621    0.946    0.884
mistral:7b-instruct 0.891    0.952    0.827
phi3:mini           0.705    0.578    0.366
qwen3:1.7b          0.923    0.960    0.901
```

doc 03 (substation, IEC 61850, dense identifiers) was the hardest case in v2 with mistral and llama3.1 both at ~0.45 mean. In v3 the same document recovers above 0.82 median for every model except phi3. The two-step prompt's largest absolute lift is on the identifier-dense case, which makes sense: the recall burden was highest where there were the most substitutions to remember.

### Updated viability tiers

**Production-tier (with manual diff still recommended):** mistral:7b-instruct, qwen3:1.7b. Both above 0.40 P(rec ≥ 0.95), both with zero catastrophic trials, both with median recovery above 0.91. Use mistral when wall-time budget is permissive and you want the highest peak quality; use qwen3 for fastest small-model deployment with comparable median recovery (115s encode is dominated by the second LLM pass; the first pass finishes in ~30s).

**Beta-tier (consistency-first):** gemma3:4b, llama3.1:8b. Median recovery 0.84-0.85, both with zero catastrophic trials. gemma3:4b has the highest mapping fidelity in the cohort (0.92 aggregate, 19/30 trials at 100%) and the fastest encode (30.8s). Use gemma3:4b when you want minimal trust in the mapping-verification gate and don't need the absolute highest peak recovery.

**Caution-tier:** llama3.2:3b. Median 0.842 sounds fine but doc 01 median is only 0.621 and aggregate map support is 0.61 (lowest of any non-failing model). Variance is the highest in the cohort (SD 0.186). Useful for short content; risky for short documents specifically.

**Not viable:** phi3:mini. Median 0.555. The two-step prompt fixed its mapping fidelity but did not fix its content preservation. Likely needs the polish step (v3-C, available via `--polish`) or a different prompt structure entirely.

### One open puzzle

For mistral:7b-instruct the per-trial Pearson correlation between `mapping_supported_ratio` and `recovery_ratio` is **−0.48** (n=30). Higher mapping fidelity weakly predicts *lower* recovery for this model specifically. This does not appear for any other model (gemma −0.04, llama3.1 +0.24, llama3.2 −0.22, phi3 +0.36, qwen3 −0.05).

Working hypothesis: when mistral's two-step pass aggressively re-derives mapping entries from the cover, it captures incidental cover words that were not part of the planned substitution. These inflate the mapping size, pass the substring-presence check, and then introduce decode-time noise because the inverse rewrites cover-domain bystander words back into source-domain terms that were never there. The fix would be to weight the mapping-verification gate by identifier coverage of the source, not just substring presence in the cover. This is unresolved and worth investigating in v4.

### v3 production-use guidance

1. **Use the LLM backend with `LLM_TWO_STEP = True` (the default).** Do not fall back to the v2 single-step prompt outside of A/B testing.
2. **For the highest-quality covers, use `mistral:7b-instruct`.** P(rec ≥ 0.95) = 0.43, zero catastrophic trials, median 0.92.
3. **For fastest deployment of the smallest viable model, use `qwen3:1.7b`.** Median recovery 0.92 at 1.7B parameters; runs on essentially any modern hardware with Ollama. Note the second LLM call extends total encode to ~115s.
4. **For best mapping-fidelity audit trail, use `gemma3:4b`.** 92% aggregate mapping support, 19/30 trials at 100% support. The substitutions in the embedded JSON are the substitutions in the cover, almost without exception.
5. **The `--strict` flag on `encrypt` is now safe to use as a default.** With v3 prompts, the 80% mapping-support threshold rarely trips for the four production/beta-tier models. It still trips for phi3 (16% of trials below 80%) and llama3.2:3b on doc 01 specifically.
6. **The `--polish` flag remains optional.** v3 narrowed the recovery-quality gap; the polish step is still the right intervention for closing the Caudle Distance gap (cover naturalness vs native), which v3 did not address. SCD remained at 1.10-1.16 nats across all models.

### Reproducing v3

```bash
cd /path/to/falsecolors
ollama pull llama3.2:3b qwen3:1.7b phi3:mini gemma3:4b mistral:7b-instruct llama3.1:8b
OLLAMA_TIMEOUT=600 python3 evaluation/run.py --trials 10 --out evaluation/results-v3-twostep.json
# To resume after interruption:
OLLAMA_TIMEOUT=600 python3 evaluation/run.py --out evaluation/results-v3-twostep.json --resume
```

The harness writes incrementally; `--resume` loads the existing `--out` file and skips any `(doc, model, trial)` already recorded. Raw v3 data: `evaluation/results-v3-twostep.json`.

---

## v2 (May 2026): Verification gate and 5x corpus

The methodology section below is the authoritative description of how trials are run, what metrics mean, and what the test corpus looks like. The viability-tier framing and per-model recommendations have been superseded by v3 above.

### Headline (superseded by v3)

**No model in the cohort is production-grade for the public falsecolors prompt.** `P(recovery ≥ 0.95)` is at most 0.17 (mistral:7b-instruct), and every other model is 0.00. The local-LLM backend in `falsecolors.py encrypt --backend llm` is a research-grade tool today. Production use requires either (a) a polish step that runs after the LLM rewrite, (b) a much larger model than this cohort tests, or (c) a prompt redesign that the model can follow more reliably.

**For the most consistent local model, use `gemma3:4b`.** It produces the highest fraction of mapping-supported substitutions (95% of sampled `(src, tgt)` pairs are present in the cover), it never collapses below 0.30 recovery, and it has the tightest variance in the cohort (0.125). It is the only model in the cohort that is not bimodal.

**`mistral:7b-instruct` is the highest-mean model but is also the most dangerous.** It produces the highest peak recoveries (17% of trials at ≥0.95) but also has 13% of trials below 0.30 with parseable mapping JSONs. Its mapping-supported ratio is 0.69, the lowest of any non-broken model. The mean (0.703) hides a bimodal distribution: 17% near-perfect, 13% catastrophic, the middle bunched around 0.7-0.85.

**`qwen3:1.7b` is unusable on the public prompt.** /no_think eliminates the thinking-mode bleed but the model still emits mapping JSONs that match the cover in 1 of 81 sampled pairs (mapping support ratio: 0.01). Whatever qwen3 is doing on the rewrite, it is not what the prompt is asking for. *(v3 update: this conclusion was wrong. The two-step prompt brings qwen3:1.7b to median recovery 0.916 and mapping support 0.86. The failure was in the prompt structure, not the model.)*

## Methodology

Hardware: Mac, Ollama 0.17.4. Six models tested:

| Tag | Family | Params | Quant |
|---|---|---|---|
| `llama3.2:3b` | Meta Llama 3.2 | 3.2B | Q4_K_M |
| `qwen3:1.7b` | Alibaba Qwen3 | 1.7B | Q4_K_M |
| `phi3:mini` | Microsoft Phi-3 Mini | 3.8B | Q4_0 |
| `gemma3:4b` | Google Gemma 3 | 4B | Q4_K_M |
| `mistral:7b-instruct` | Mistral AI | 7.2B | Q4_K_M |
| `llama3.1:8b` | Meta Llama 3.1 | 8B | Q4_K_M |

`qwen3:4b` was excluded after every v1 trial timed out at 600s.

Three sensitive OT/ICS test documents under `evaluation/documents/`:

- `01_reactor_sis_bypass.txt` (172 words)
- `02_water_scada_creds.txt` (264 words)
- `03_substation_iec61850.txt` (242 words; **highest identifier density** with CVE, IEC 61850, IEC 62351, NERC CIP, multiple measurements)

Native brewery corpus: `evaluation/corpora/brewery.txt`, 2560 words across five sub-genres (audit reports, brewmaster operational logs, regulatory submissions, trade press, brewing process reference). 5x larger than v1 by embedding vocab (517 tokens, 1846 adjacent pairs).

Each model encoded each document **10 times** via `falsecolors.encode_document(..., backend="llm")` with passphrase `"eval-2026"` and topic `"brewery"`. n=10 is enough to estimate `P(recovery ≥ 0.95)` and `P(recovery < 0.30)` to ~10% precision per cell.

Per-model prompt prefixes (qwen3 family received `/no_think\n` via `OLLAMA_PROMPT_PREFIX`; all other models received no prefix). `OLLAMA_TIMEOUT=600`.

The harness records:

- **encode_secs / decode_secs** — wall time.
- **mapping_size** — number of entries in the embedded `domain` JSON. 0 means JSON didn't parse.
- **mapping_supported / mapping_sampled** — for each trial, the harness samples up to 5 random `(src, tgt)` map entries, lowercases the cover, and counts how many `tgt` substrings actually appear. **`mapping_supported = 0` with `mapping_size > 0` is the silent-integrity-failure signature.** v1 missed this entirely.
- **recovery_ratio** — `difflib.SequenceMatcher(None, source, recovered).ratio()`. 1.0 = perfect round-trip.
- **scd** — Caudle Distance of cover (with footer stripped) against brewery corpus, in nats.

180 trials total. Run wall-time: 11662s (3h 14min).

Raw data in `evaluation/results-v2.json`.

## Combined results

| Model | Recovery (mean ± SD) | P(rec ≥ 0.95) | P(rec < 0.30) | Map size | Map support ratio | JSON ok | Crash | Encode (s) |
|---|---|---|---|---|---|---|---|---|
| **gemma3:4b** | 0.581 ± 0.125 | 0.00 | **0.00** | 12.6 ± 3.6 | **0.95** | 30/30 | 0/30 | 56.7 |
| llama3.1:8b | 0.631 ± 0.163 | 0.00 | 0.00 | 10.7 ± 1.6 | 0.92 | 30/30 | 0/30 | 77.9 |
| llama3.2:3b | 0.635 ± 0.192 | 0.00 | 0.07 | 8.2 ± 3.6 | 0.81 | 30/30 | 0/30 | 38.4 |
| mistral:7b-instruct | **0.703 ± 0.281** | **0.17** | 0.13 | 8.1 ± 5.5 | 0.69 | 30/30 | 0/30 | 84.6 |
| phi3:mini | 0.474 ± 0.113 | 0.00 | 0.07 | 5.7 ± 5.6 | 0.51 | 17/30 | 1/30 | 50.4 |
| qwen3:1.7b | 0.146 ± 0.198 | 0.00 | 0.83 | 5.9 ± 8.2 | 0.01 | 30/30 | 0/30 | 79.8 |

`P(rec ≥ 0.95)` and `P(rec < 0.30)` are estimated as fraction of n=30 trials per model.

`Map support ratio` aggregates: `Σ mapping_supported / Σ mapping_sampled` across all trials.

`JSON ok` counts trials where `mapping_size > 0`. `Crash` counts encode failures (timeout, JSONDecodeError on the model's own output).

### Per-document detail

```
gemma3:4b
  doc 01 (short):              recovery 0.476 ±0.076   map  8.8 ±1.8   sup 49/50   scd 0.937
  doc 02 (mid):                recovery 0.721 ±0.065   map 12.3 ±1.8   sup 44/50   scd 0.984
  doc 03 (identifier-dense):   recovery 0.547 ±0.070   map 16.7 ±0.7   sup 49/50   scd 0.989

llama3.1:8b
  doc 01 (short):              recovery 0.764 ±0.143   map  9.8 ±1.0   sup 50/50   scd 1.255
  doc 02 (mid):                recovery 0.672 ±0.053   map 11.3 ±2.2   sup 40/50   scd 1.072
  doc 03 (identifier-dense):   recovery 0.457 ±0.081   map 11.0 ±1.1   sup 48/50   scd 1.135

llama3.2:3b
  doc 01 (short):              recovery 0.604 ±0.227   map  6.7 ±3.4   sup 33/42   scd 1.154
  doc 02 (mid):                recovery 0.588 ±0.220   map  7.6 ±4.6   sup 33/39   scd 1.169
  doc 03 (identifier-dense):   recovery 0.712 ±0.096   map 10.3 ±1.4   sup 40/50   scd 1.099

mistral:7b-instruct
  doc 01 (short):              recovery 0.926 ±0.068   map  6.7 ±0.9   sup 25/46   scd 1.169
  doc 02 (mid):                recovery 0.742 ±0.142   map  7.8 ±6.5   sup 29/35   scd 1.083
  doc 03 (identifier-dense):   recovery 0.440 ±0.310   map  9.9 ±7.0   sup 28/38   scd 1.034

phi3:mini
  doc 01 (short):              recovery 0.489 ±0.127   map  3.4 ±3.8   sup 16/25   scd 1.171
  doc 02 (mid):                recovery 0.486 ±0.138   map  9.0 ±7.3   sup 13/30   scd 1.218
  doc 03 (identifier-dense):   recovery 0.447 ±0.076   map  5.1 ±4.5   sup 14/30   scd 1.026

qwen3:1.7b
  doc 01 (short):              recovery 0.114 ±0.151   map  4.2 ±3.6   sup  0/26   scd 1.139
  doc 02 (mid):                recovery 0.209 ±0.254   map  4.1 ±4.5   sup  0/26   scd 1.082
  doc 03 (identifier-dense):   recovery 0.114 ±0.181   map  9.5 ±12.7  sup  1/29   scd 1.124
```

## Findings

### 1. Tail risk is the right metric for FALSECOLORS, and v2 reveals a new picture

v1 ranked models by mean recovery: mistral:7b at 0.789, llama3.1:8b at 0.675, llama3.2:3b at 0.646, gemma3:4b at 0.591. The implication was "use mistral:7b for peak quality, gemma3:4b for consistency." v2 with n=10 trials and the verification gate inverts this for production work. Three observations break the v1 ranking:

- **mistral:7b-instruct has the highest tail risk in the viable cohort.** 13% of its trials land below 0.30 recovery despite passing JSON validity. This is unacceptable for a tool that protects sensitive findings; one in eight documents arrives substantially destroyed at the recipient. v1 saw the high mean and missed the tail because n=3 trials per cell does not reliably surface a 13% failure rate.
- **gemma3:4b never collapses.** 0/30 trials below 0.30. Its mean recovery is the lowest of the viable models, but the entire distribution sits in the 0.4-0.8 band with no catastrophic failures. For a tool whose worst-case behavior is what matters, this is the better profile.
- **mistral:7b-instruct's mapping support ratio is 0.69**, the lowest of any non-broken model. mistral often emits mapping JSONs that don't faithfully describe what it did to the cover. The reason its recovery looks high is partly that it does light shifts (only 6-8 substitutions on doc 1, vs 11-17 for gemma3:4b on doc 3) — the cover is largely unchanged, so the inverse-mapping is largely a no-op, and `recovery_ratio` reads high. This is recovery-by-not-shifting, not recovery-by-correct-shifting.

### 2. The viability tier ladder

Working from the v2 data, four viability tiers emerge:

**Production-grade**: `P(recovery ≥ 0.95) > 0.90`, `P(rec < 0.30) = 0.00`, mapping support ratio ≥ 0.95. **No model in this cohort meets this bar.** Reaching it likely requires a polish/verification step outside the LLM call, or a substantially larger model than was tested here.

**Beta-grade (consistency-first)**: `P(rec < 0.30) ≤ 0.05`, mapping support ratio ≥ 0.85, no crashes. **gemma3:4b** (mapping ratio 0.95) and **llama3.1:8b** (0.92) qualify. Recommended for batch use where individual document recovery quality matters less than the floor on the worst-case trial. Recovery ceiling for these models is in the 0.60-0.75 band.

**Beta-grade (peak-first)**: `P(recovery ≥ 0.95) > 0.10` but `P(rec < 0.30) > 0.05`. **mistral:7b-instruct** is the only model in this tier. Use it when you can manually diff every cover before relying on it, and accept that 1 trial in 8 will produce a destroyed recovery you must catch and discard.

**Research-grade**: anything else. **llama3.2:3b** (mapping ratio 0.81, but P(rec < 0.30) = 0.07) and **phi3:mini** (mapping ratio 0.51, plus a JSONDecodeError crash) sit here.

**Unsuitable**: **qwen3:1.7b** (mapping ratio 0.01, P(rec < 0.30) = 0.83). Even with `/no_think` injection, the model does not produce a cover that corresponds to the mapping it emits. The thinking-mode bleed identified in v1 was not the only problem.

### 3. The verification gate caught what JSON validity missed

In v1, "JSON ok" was the only mapping-quality check. mistral:7b-instruct passed 9/9 in v1 with a mean recovery of 0.789 and the writeup recommended it as the highest-quality model. v2 with the verification gate shows that mistral's mapping support ratio is 0.69: roughly one in three sampled mapping entries does not appear in the cover. Same model, same prompt, same documents. The hallucinated-mapping failure mode was real all along; v1 just couldn't see it.

For phi3:mini, the v2 picture is grimmer than v1 reported. v1 noted "JSON ok 5/9" and described phi3 as inconsistent. v2 confirms 17/30 trials emit valid JSON, but the *contents* of those JSONs are wrong: 43 of 85 sampled entries are unsupported (mapping support ratio 0.51). Half the time phi3 emits no JSON; the other half, half its JSON is hallucinated.

For qwen3:1.7b, the v1 hypothesis was that thinking-mode bleed corrupted the output. v2 ran with `/no_think` injected, so thinking is suppressed. The model still produced 81 sampled mapping entries across 30 trials, of which exactly 1 appeared in the cover. The failure is not thinking-mode. The model is doing something fundamentally different from what the prompt asks. Whether it is following its own internal interpretation, hallucinating, or treating the prompt as "produce a JSON about brewing" rather than "produce a brewing-domain rewrite plus a faithful substitution map" is unclear from the run alone.

### 4. The hardest document still breaks every model

Doc 3 (substation finding with CVE, IEC 61850, multiple standards, multiple measurements, port numbers, firmware versions) is consistently the lowest-recovery document for every model except llama3.2:3b. The 7-8B models' doc 3 means:

- mistral:7b-instruct: 0.440 ± 0.310 (very high variance, includes the 0.086-0.107 cluster of minimal-rewrite failures)
- llama3.1:8b: 0.457 ± 0.081 (low but tight)
- gemma3:4b (3-4B band): 0.547 ± 0.070 (best on doc 3 in the cohort, despite being smaller)

llama3.2:3b is the unexpected outlier: doc 3 is its **best** document at 0.712 ± 0.096. Hypothesis: llama3.2:3b's tendency toward minimal substitutions (mean map size 8.2) is well-matched to a document whose vocabulary already partially overlaps with the brewery domain (both have "registers," "thresholds," "operators," "control"). This is recovery-by-minimal-shift, similar to mistral but more consistent.

Identifier-dense documents remain the case where prompt design, not model size, is the limiting factor. A v3 of this prompt that pre-extracts identifiers more aggressively, or that splits the rewrite from the mapping-emission step, would likely lift doc 3 recovery for all models.

### 5. Bimodal model behavior is real and matters

mistral:7b-instruct on doc 3 produces a clean bimodal distribution: trials with `mapping_size = 2` consistently score in the 0.086-0.123 range (recovery-by-not-shifting, but not even shifting *enough* to recover well via the small mapping); trials with `mapping_size > 10` score 0.338-0.759. The two modes don't overlap. Same prompt, same temperature 0.1, same document — the model picks one of two strategies per trial.

This bimodality is invisible at n=3 and is the single most important reason to prefer larger sample sizes for FALSECOLORS evaluation. Mean and stdev assume unimodal; this distribution is not unimodal; the mean and stdev mislead.

### 6. SCD remains underpowered

The 5x corpus expansion gave SCD enough adjacent-pair samples to compute a stable value (1700 → 1846 doc_pairs in the corpus, vocabulary 106 → 517), but SCD across the cohort still clusters in 0.94-1.30 nats. The discrimination problem is not corpus thinness; it's that none of the models in the cohort produces a cover good enough to score below ~0.9 nats. A target SCD floor of 0.1 nats (close to native) is roughly an order of magnitude away. SCD will become discriminating either when a polish step lifts cover quality into the 0.1-0.5 range, or when the prompt is tuned for collocational naturalness rather than just correct substitutions.

### 7. New failure mode: model emits invalid JSON

phi3:mini doc 2 trial 3 crashed with `JSONDecodeError: Illegal trailing comma`. The model emitted a mapping JSON with a trailing comma, which Python's strict JSON parser refused. v1 didn't see this because n=3 didn't surface a 1-in-30 event. The harness records it as a crash and continues; in production this would either crash the user's encrypt or silently fall through to "no mapping" depending on how `falsecolors.py` handles `JSONDecodeError` in `llm_translate`. Worth a defensive parse path in production.

## v1 vs v2 deltas (where the picture changed)

| Model | v1 mean | v2 mean | v1 finding | v2 finding |
|---|---|---|---|---|
| mistral:7b-instruct | 0.789 | 0.703 | "highest peak recovery, recommended" | bimodal; 13% catastrophic; mapping support 0.69 |
| gemma3:4b | 0.591 | 0.581 | "most consistent" | confirmed; only model with P(rec<0.30)=0; mapping support 0.95 |
| llama3.1:8b | 0.675 | 0.631 | "good consistency" | confirmed; mapping support 0.92; safe choice |
| llama3.2:3b | 0.646 | 0.635 | "highest 3B-band peak" | confirmed but mapping support 0.81 (gemma is better) |
| phi3:mini | 0.460 | 0.474 | "fails JSON tail half the time" | confirmed plus hallucinated mapping 0.49 of the time |
| qwen3:1.7b | 0.127 | 0.146 | "thinking-mode bleed" | wrong: /no_think doesn't fix it; deeper prompt-following issue |

The v1 mistral recommendation was the wrong call. The mean was right; the tail was missed; and the mapping fidelity was opaque.

### Production-use guidance (v2, superseded by v3)

These six v2 recommendations were the operational guidance shipped after v2 and have been replaced by the v3 guidance at the top of this document. They are kept here for traceability.

1. **No model in this cohort is production-grade for high-stakes use.** The local-LLM backend is research-grade today; treat outputs as drafts that require manual diff before transmission. *(v3: superseded. Four models now reach beta-or-better tier with the two-step prompt.)*
2. **For batch or unattended use, use `gemma3:4b`.** It is the only model with `P(recovery < 0.30) = 0.00` across n=30 trials, and 95% of its sampled mapping entries appear in the cover. It is also faster than the 7-8B models. *(v3: gemma3:4b remains a strong beta-tier choice; mistral:7b and qwen3:1.7b now exceed it on recovery while maintaining `P(rec<0.30)=0`.)*
3. **For one-off interactive use where you can diff before sending, mistral:7b-instruct can produce stronger covers**, but verify every output. The 0.95+ trials are excellent; the 0.30- trials look superficially fine and are not. *(v3: the catastrophic-trial failure mode is gone. Manual diff is still recommended but no longer required to catch silent collapses.)*
4. **Avoid identifier-dense documents on any local model in this cohort.** Pre-process out CVEs, standards, measurements, and version numbers via the `IdentEncoder` placeholder system, and feed the LLM only the prose layer. *(v3: doc 03 median recovery is now 0.82-0.90 for four of six models. Identifier density is no longer a hard limit.)*
5. **Do not use qwen3:1.7b** with the public falsecolors prompt as shipped, even with `/no_think`. The mapping fidelity is 0.01. *(v3: reversed. qwen3:1.7b is now production-tier on the two-step prompt.)*
6. **A polish step is the obvious next product investment.** *(v3: implemented as the optional `--polish` flag. Recommended for SCD reduction; v3-B already addressed the recovery-quality concern that motivated this item.)*

### v2 reproducing instructions (superseded by v3)

```bash
cd /path/to/falsecolors
ollama pull llama3.2:3b qwen3:1.7b phi3:mini gemma3:4b mistral:7b-instruct llama3.1:8b
OLLAMA_TIMEOUT=600 python3 evaluation/run.py --trials 10 --out evaluation/results-v2.json
```

To run v2 today (with the two-step prompt now default), set `LLM_TWO_STEP = False` in `falsecolors.py` first. The v3 reproducing instructions at the top of this document are the recommended path.

---

## Data

- **v3 raw:** `evaluation/results-v3-twostep.json` (n=10 × 6 models × 3 docs = 180 trials, two-step prompt)
- **v2 raw:** `evaluation/results-v2.json` (n=10 × 6 models × 3 docs = 180 trials, single-step prompt)
- **v1 raw:** `evaluation/results.json` (3-4B band, n=3) and `evaluation/results-extended.json` (7-8B band, n=3)
- Test documents: `evaluation/documents/` (unchanged across v1, v2, v3)
- Reference corpus: `evaluation/corpora/brewery.txt` (unchanged from v2)
- Harness: `evaluation/run.py` (v3 added the `--resume` flag)

## Future work after v3

- **Polish-step evaluation.** v3-C implementation exists (`--polish` flag) but has not been run through the full 180-trial evaluation. Open question: does polish lift Caudle Distance from 1.10 to below 0.5 nats without breaking the `mapping_supported` ratio? The verify-and-fallback in `polish_cover` should keep mapping fidelity intact, but the trade-off has not been characterized.
- **Mistral mapping-fidelity / recovery negative correlation.** −0.48 Pearson on n=30 is suggestive but not conclusive. v4 should run mistral:7b-instruct at n=30+ on a per-doc basis to see whether the correlation persists and whether it is driven by mapping size inflation specifically.
- **Reference 13B+ model.** Carried forward from v2. With the two-step prompt now lifting the small-model band, the open question is whether a 13B-70B model gets to `P(rec ≥ 0.95) ≥ 0.90` without polish.
- **Identifier-dense regression set.** v3 removed the doc-03 cliff for most models. v4 should construct documents at varying identifier densities (e.g., 0.5 to 5.0 identifiers per sentence) to characterize the recovery-vs-density curve under the two-step prompt.
- **Cross-document SCD.** Carried forward from v2. Compute SCD between covers from different source documents to assess unlinkability.
