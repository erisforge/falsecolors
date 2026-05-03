# Eris FALSECOLORS Local-Model Evaluation, v2 (May 2026)

This is the second-pass evaluation. The first pass (v1, see commit history of `evaluation/results.json` and `evaluation/results-extended.json`) ran n=3 trials per (model, doc) and used a JSON-validity check as the only quality signal. v2 adds n=10 trials, a mapping-verification gate that detects the silent "hallucinated mapping" failure mode, a 5x corpus expansion, and a `/no_think` retry for qwen3.

## Headline

**No model in the cohort is production-grade for the public falsecolors prompt.** `P(recovery ≥ 0.95)` is at most 0.17 (mistral:7b-instruct), and every other model is 0.00. The local-LLM backend in `falsecolors.py encrypt --backend llm` is a research-grade tool today. Production use requires either (a) a polish step that runs after the LLM rewrite, (b) a much larger model than this cohort tests, or (c) a prompt redesign that the model can follow more reliably.

**For the most consistent local model, use `gemma3:4b`.** It produces the highest fraction of mapping-supported substitutions (95% of sampled `(src, tgt)` pairs are present in the cover), it never collapses below 0.30 recovery, and it has the tightest variance in the cohort (0.125). It is the only model in the cohort that is not bimodal.

**`mistral:7b-instruct` is the highest-mean model but is also the most dangerous.** It produces the highest peak recoveries (17% of trials at ≥0.95) but also has 13% of trials below 0.30 with parseable mapping JSONs. Its mapping-supported ratio is 0.69, the lowest of any non-broken model. The mean (0.703) hides a bimodal distribution: 17% near-perfect, 13% catastrophic, the middle bunched around 0.7-0.85.

**`qwen3:1.7b` is unusable on the public prompt.** /no_think eliminates the thinking-mode bleed but the model still emits mapping JSONs that match the cover in 1 of 81 sampled pairs (mapping support ratio: 0.01). Whatever qwen3 is doing on the rewrite, it is not what the prompt is asking for.

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

## Production-use guidance (revised from v1)

1. **No model in this cohort is production-grade for high-stakes use.** The local-LLM backend is research-grade today; treat outputs as drafts that require manual diff before transmission.
2. **For batch or unattended use, use `gemma3:4b`.** It is the only model with `P(recovery < 0.30) = 0.00` across n=30 trials, and 95% of its sampled mapping entries appear in the cover. It is also faster than the 7-8B models.
3. **For one-off interactive use where you can diff before sending, mistral:7b-instruct can produce stronger covers** — but verify every output. The 0.95+ trials are excellent; the 0.30- trials look superficially fine and are not.
4. **Avoid identifier-dense documents on any local model in this cohort.** Pre-process out CVEs, standards, measurements, and version numbers via the `IdentEncoder` placeholder system, and feed the LLM only the prose layer.
5. **Do not use qwen3:1.7b** with the public falsecolors prompt as shipped, even with `/no_think`. The mapping fidelity is 0.01.
6. **A polish step is the obvious next product investment.** Rerun the cover through a second LLM call ("rewrite this document to read more naturally as a brewery document, preserving every domain term") and re-verify. This was identified in the paper (Section 2.15.4) as the path from `Caudle Distance > 0.5` to `Caudle Distance ≈ 0` and is independent of the rewrite-quality issue.

## v3 future work

Open after v2:

- **Polish-step harness.** Add a second-pass LLM call that rewrites the cover for naturalness without modifying the mapping. Measure whether `recovery_ratio` and SCD both improve and whether mapping_supported holds.
- **Reference 13B+ model.** Tests this cohort doesn't span. Likely needs cloud or a beefier local box.
- **Alternative prompt structures.** Separate the rewrite step from the mapping-emission step (two LLM calls). Force the model to emit the mapping first, then write the cover, applying the mapping mechanically. This may resolve the mistral bimodality and the qwen3 prompt-following failure.
- **Identifier-dense document rewrite test.** Doc 3 is the failure case; a v3 should construct documents at varying identifier-density levels and characterize the recovery-vs-density curve.
- **Cross-document SCD.** Compute SCD against the corpus AND against other covers. Cross-cover similarity may be more discriminating than corpus similarity given the corpus-quality floor.

## Reproducing this evaluation

```bash
cd /path/to/falsecolors
ollama pull llama3.2:3b qwen3:1.7b phi3:mini gemma3:4b mistral:7b-instruct llama3.1:8b
OLLAMA_TIMEOUT=600 python3 evaluation/run.py --trials 10 --out evaluation/results-v2.json
```

The harness writes incrementally so partial progress survives interrupt. Override the model list with `--models llama3.2:3b gemma3:4b`. Per-model prompt prefixes are configured in the `PROMPT_PREFIX` dict in `run.py`.

## Data

- v2 raw: `evaluation/results-v2.json` (n=10 × 6 models × 3 docs = 180 trials)
- v1 raw: `evaluation/results.json` (3-4B band, n=3) and `evaluation/results-extended.json` (7-8B band, n=3) — preserved for v1 vs v2 comparison
- Test documents: `evaluation/documents/`
- Reference corpus: `evaluation/corpora/brewery.txt` (5x v1 size)
- Harness: `evaluation/run.py`
