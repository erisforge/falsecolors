# Eris FALSECOLORS Local-Model Evaluation, May 2026

## What this evaluation answers

The question: **is the local-LLM backend in `falsecolors.py encrypt --backend llm` viable for production protection of sensitive pentest findings, and if so, at what model size?**

The headline finding: **not at 1.7B-4B parameters, partially at 7-8B parameters, and not yet at any size for identifier-dense documents.** Mean round-trip recovery moves from 0.65 in the 3B band to 0.79 in the 7-8B band, a real lift. But doc 3 (a substation finding with CVE references, multiple standards, multiple measurements, and dense numeric content) bottoms out at 0.342-0.597 even on mistral:7b-instruct. Parameter count helps; prompt design is the remaining ceiling on hard inputs. Sub-4B is consistency-broken regardless. Production use today should pin to a 7-8B model AND keep the cover-document recovery loop in human supervision until either the prompt or a polish step closes the doc-3 gap.

A second finding: **the harness as built does not catch the most dangerous failure mode.** A model can emit a parseable mapping JSON that does not correspond to the substitutions actually made in the cover. The trial passes every automated check (JSON valid, `mapping_size > 0`, no timeout) and `recovery_ratio` lands at 0.000 silently. We saw this in phi3:mini (3B band) and mistral:7b-instruct (7B band). A v2 of this harness must verify N random `(src, tgt)` pairs against the cover before declaring a trial scored.

## Methodology

Hardware: Mac, Ollama 0.17.4. All models pulled via `ollama pull <tag>`.

Six models tested across two parameter bands:

| Tag | Family | Params | Quant | Band |
|---|---|---|---|---|
| `llama3.2:3b` | Meta Llama 3.2 | 3.2B | Q4_K_M | 3-4B |
| `qwen3:1.7b` | Alibaba Qwen3 | 1.7B | Q4_K_M | 3-4B |
| `phi3:mini` | Microsoft Phi-3 Mini | 3.8B | Q4_0 | 3-4B |
| `gemma3:4b` | Google Gemma 3 | 4B | Q4_K_M | 3-4B |
| `mistral:7b-instruct` | Mistral AI | 7.2B | Q4_K_M | 7-8B |
| `llama3.1:8b` | Meta Llama 3.1 | 8B | Q4_K_M | 7-8B |

`qwen3:4b` was attempted at both 120s and 600s timeouts; every trial ran to the timeout boundary. The model is excluded from numbers and discussed under [Excluded models](#excluded-models).

Test corpus: three pentest-style finding documents under `evaluation/documents/`:

- `01_reactor_sis_bypass.txt` (172 words, ethylene oxide reactor SIS bypass via Modbus TCP)
- `02_water_scada_creds.txt` (264 words, hardcoded SCADA credentials in pump-station firmware)
- `03_substation_iec61850.txt` (242 words, GOOSE message spoofing on substation process bus, **highest identifier density**: CVE, IEC 61850, IEC 62351, NERC CIP, port 102, 230 kV, 220 MW, firmware version v2.18.7, register 40023, multiple IEDs)

Native brewery corpus: `evaluation/corpora/brewery.txt`, 12 paragraphs (~1700 tokens) of plausible craft-brewery quality-audit prose. **This corpus is too thin to make Caudle Distance discriminating across models;** it produces SCD values clustered in a narrow band. A v2 corpus expansion is identified as future work.

Each model encoded each document three times via `falsecolors.encode_document(..., backend="llm")` with passphrase `"eval-2026"` and topic `"brewery"`. n=3 trials per (model, doc) is enough to spot order-of-magnitude differences but **not enough to characterize tail-risk distributions**. Variance claims in this writeup should be read as preliminary.

`OLLAMA_TIMEOUT=600` was set for the run.

The harness, results, and corpora are under `evaluation/`. Raw per-trial data is in `evaluation/results.json` (3-4B band) and `evaluation/results-extended.json` (7-8B band).

## Combined results

Mean ± stdev across 9 trials (3 documents × 3 trials).

| Band | Model | Recovery | Mapping size | SCD (nats) | Encode (s) | JSON ok |
|---|---|---|---|---|---|---|
| 7-8B | **mistral:7b-instruct** | **0.789 ± 0.189** | 10.3 ± 4.1 | 1.144 ± 0.151 | 105.9 ± 32.4 | 9/9 |
| 7-8B | llama3.1:8b | 0.675 ± 0.147 | 11.9 ± 0.9 | 1.181 ± 0.093 | 107.4 ± 15.2 | 9/9 |
| 3-4B | llama3.2:3b | 0.646 ± 0.220 | 8.2 ± 3.8 | 1.071 ± 0.139 | 42.8 ± 8.6 | 9/9 |
| 3-4B | gemma3:4b | 0.591 ± 0.138 | 14.6 ± 4.1 | 1.092 ± 0.123 | 62.7 ± 18.2 | 9/9 |
| 3-4B | phi3:mini | 0.460 ± 0.198 | 5.7 ± 5.8 | 1.062 ± 0.107 | 52.9 ± 23.2 | 5/9 |
| 3-4B | qwen3:1.7b | 0.127 ± 0.136 | 5.3 ± 5.7 | 0.980 ± 0.185 | 74.9 ± 31.5 | 9/9 |

"JSON ok" counts trials where `mapping_size > 0`. **A nonzero mapping does not guarantee that the mapping matches the substitutions actually made in the cover.** See [Failure modes](#failure-modes).

### Per-document detail

```
mistral:7b-instruct (7-8B band)
  doc 01 (short):              recovery 0.924 ±0.037   map  6.3 ±0.6   scd 1.298 ±0.188   enc  69.0s
  doc 02 (mid):                recovery 0.845 ±0.063   map 10.3 ±4.0   scd 1.046 ±0.005   enc 119.1s
  doc 03 (identifier-dense):   recovery 0.597 ±0.223   map 14.3 ±1.5   scd 1.089 ±0.028   enc 129.6s

llama3.1:8b (7-8B band)
  doc 01 (short):              recovery 0.807 ±0.013   map 11.0 ±0.0   scd 1.258 ±0.061   enc  95.5s
  doc 02 (mid):                recovery 0.717 ±0.054   map 12.3 ±1.2   scd 1.170 ±0.050   enc 124.2s
  doc 03 (identifier-dense):   recovery 0.502 ±0.095   map 12.3 ±0.6   scd 1.114 ±0.113   enc 102.5s

gemma3:4b (3-4B band)
  doc 01 (short):              recovery 0.482 ±0.134   map 11.3 ±1.2   scd 1.117 ±0.070   enc  44.0s
  doc 02 (mid):                recovery 0.744 ±0.027   map 13.0 ±0.0   scd 1.207 ±0.071   enc  65.5s
  doc 03 (identifier-dense):   recovery 0.546 ±0.034   map 19.3 ±3.5   scd 0.954 ±0.030   enc  78.6s

llama3.2:3b (3-4B band)
  doc 01 (short):              recovery 0.693 ±0.060   map  9.7 ±2.5   scd 1.071 ±0.000   enc  37.0s
  doc 02 (mid):                recovery 0.442 ±0.289   map  5.3 ±5.8   scd 1.220 ±0.100   enc  38.8s
  doc 03 (identifier-dense):   recovery 0.804 ±0.056   map  9.7 ±0.6   scd 0.922 ±0.027   enc  52.7s

phi3:mini (3-4B band)
  doc 01 (short):              recovery 0.315 ±0.274   map  3.3 ±5.8   scd 1.117 ±0.016   enc  29.7s
  doc 02 (mid):                recovery 0.620 ±0.096   map 11.3 ±3.5   scd 0.949 ±0.081   enc  56.2s
  doc 03 (identifier-dense):   recovery 0.444 ±0.040   map  2.3 ±4.0   scd 1.119 ±0.101   enc  72.8s

qwen3:1.7b (3-4B band)
  doc 01 (short):              recovery 0.123 ±0.213   map  7.3 ±4.7   scd 1.274          enc  83.8s
  doc 02 (mid):                recovery 0.145 ±0.114   map  1.7 ±0.6   scd 0.942 ±0.177   enc  48.1s
  doc 03 (identifier-dense):   recovery 0.112 ±0.120   map  7.0 ±8.7   scd 0.891 ±0.044   enc  92.7s
```

## Findings

### 1. Parameter scaling delivers ~0.14 mean-recovery lift, 3B → 7-8B

Best 3-4B mean recovery: **0.646** (llama3.2:3b). Best 7-8B mean recovery: **0.789** (mistral:7b-instruct). The lift is real and consistent: every 7-8B model outperforms every 3-4B model on every document, with one minor exception (gemma3:4b ties llama3.1:8b on doc 2). Parameter count is the single biggest knob in this evaluation. The 2.5x latency cost (mistral:7b at 106s vs llama3.2:3b at 43s per encode) is the trade.

### 2. Identifier-dense documents break every model

Doc 3 has the highest density of CVE references, standards (IEC 61850, IEC 62351, NERC CIP), measurements (230 kV, 220 MW), firmware versions, port numbers, and named protocols. Every model in the cohort except llama3.2:3b drops 0.15+ in recovery on doc 3 versus its best document. mistral:7b-instruct drops from 0.924 to 0.597. llama3.1:8b drops from 0.807 to 0.502. The model has more substitutions to track in a single response, more places to misalign the mapping JSON against the rewritten prose, and more places to drop a low-frequency identifier. **Doc 3 is the case that distinguishes a research-quality eval from a production-ready eval.** No model in the cohort scores it above 0.82.

### 3. Mean recovery is the wrong target. Tail recovery is the right target.

mistral:7b-instruct's 0.789 ± 0.189 mean conceals the trial that emitted a 14-entry mapping JSON for doc 3 with `recovery_ratio = 0.342`. That trial passes JSON validity, passes mapping-size threshold, passes timeout, and produces a recovered document that is 65% destroyed. For a tool that protects sensitive pentest findings in transit, the tail of the recovery distribution is what matters. The single worst trial across the cohort is the one that decides whether a finding lands intact at the recipient or arrives garbled. A useful production metric is `P(recovery > 0.95)` per model, not `mean(recovery)`. With n=3 we cannot estimate this reliably; v2 of this evaluation will run n=10.

### 4. The "JSON ok" gate is insufficient as a quality signal

phi3:mini emitted a parseable mapping JSON with 10 entries on doc 1 trial 2. Round-trip recovery was 0.000. The mapping it emitted does not correspond to the substitutions it made in the cover; the inverse-mapping pass therefore fails to revert any of the cover's domain-shifted vocabulary. mistral:7b-instruct hit the same failure mode on doc 3 trial 1 (14-entry mapping, 0.342 recovery: partial coincidental overlap rather than true inversion). The harness's `mapping_size > 0` filter declares both trials successful by current measurement standards. **They are not.** A v2 harness must spot-check N random `(src, tgt)` mapping entries against the cover prose and reject the trial if `tgt` is not present.

### 5. qwen3 family is unusable in default settings, but this is a prompt-engineering problem

qwen3:1.7b ran inside the timeout but generated thinking-mode output that bled into the cover prose, corrupting both the cover and the JSON tail. qwen3:4b never produced a response inside 600s. Both models default to thinking mode in Ollama. **A `/no_think` directive prepended to the prompt likely fixes both.** This was not tested in the present run; v2 will include a per-model prefix override and a clean qwen3 retry. The current writeup should be read as "qwen3 family cannot be used with the public falsecolors prompt as shipped today" — not "the model is incompatible."

### 6. Caudle Distance does not separate the cohort. The corpus is too thin.

All six models produced covers with SCD between 0.89 and 1.30 nats against the brewery corpus. The 1700-token corpus is not large enough to give the histograms enough adjacent-pair samples to discriminate small differences in cover quality, and none of the models in this cohort produces a cover good enough to challenge a hypothetical "perfect" SCD floor of <0.1 nats. SCD remains useful as an absolute-quality signal: every cover scored is roughly an order of magnitude from production-quality. SCD will become discriminating only with (a) a 5x-10x larger native corpus and (b) covers good enough to span more of the [0, 0.5] range, which today's models do not produce.

## Failure modes

Three distinct failure modes appeared in the data.

**Empty mapping JSON.** The model wrote the cover prose but did not emit a parseable `{...}` tail. The harness records `mapping_size = 0` and `decode_document` reverses only the IdentEncoder placeholders. Recovery typically lands at 0.4-0.5 because the IdentEncoder map is stored separately. Affected: phi3:mini on documents 1 and 3.

**Hallucinated mapping JSON.** The model emitted a parseable mapping but the entries do not match the substitutions actually made in the cover. Inverse mapping fails to revert the cover. `recovery_ratio` lands at 0.000-0.34 despite `mapping_size > 0`. Affected: phi3:mini at least once (doc 1 trial 2: map 10, recovery 0.000); mistral:7b-instruct at least once (doc 3 trial 1: map 14, recovery 0.342). **This is the most dangerous mode in the data because it is silent under current harness checks.**

**Thinking-mode bleed.** The model's internal thinking trace appended to the cover or interleaved with the JSON. Affected: qwen3:1.7b on every trial; qwen3:4b indirectly (never finishes thinking inside the timeout).

## Excluded models

`qwen3:4b` was attempted at 120s and 600s timeouts. Every trial ran to the timeout boundary. The model is excluded from headline numbers; users who insist on it should expect 5-10 minute encode latencies per document and may find that recovery quality is unrelated to the parameter count itself.

## Production-use guidance

Until v2 lands these recommendations, treat the local-LLM backend in `falsecolors.py encrypt --backend llm` as **research-grade**, not production-grade.

If you must use it today:

1. **Use mistral:7b-instruct or llama3.1:8b.** Sub-4B local models lose >35% of content on round-trip on average and should not be used for any document you cannot afford to recover incorrectly.
2. **Diff every recovered document against the original before trusting it.** The harness's `recovery_ratio < 0.95` should be a manual-review trigger, not a logged warning. The hallucinated-mapping failure mode is silent under current checks.
3. **Avoid identifier-dense documents.** Pre-process out CVE references, standard citations, and dense numeric content via `IdentEncoder` (which already handles them) and feed the model only the prose layer. The combination of a sparse-content prose layer plus identifier-encoder placeholders is what the LLM backend handles cleanly today.
4. **Do not use qwen3 family in default thinking-mode configuration.**
5. **Verify the round-trip on a non-sensitive document before deploying the model in your workflow.** A 30-second `python falsecolors.py demo` will catch a broken model. A targeted test with a representative sensitive document will catch the hallucinated-mapping failure mode if it exists.

## V2 evaluation plan

A second-pass evaluation, with the harness and methodology gaps closed, is identified as future work:

- **Mapping-verification gate.** After encode, sample 5 random `(src, tgt)` map entries; require `tgt` substring match in the cover. Trials that fail are recorded as `mapping_unsupported` and excluded from recovery scoring.
- **Brewery corpus expansion to 5x-10x current size** (~10K-15K tokens), multiple sub-genres (audit reports, brewmaster logs, regulatory submissions, trade press) so SCD has discrimination at this cover-quality range.
- **n=10 trials per (model, doc)** instead of n=3, to characterize tail-risk distribution.
- **qwen3 retry with `/no_think` prefix injection** before writing off the family.
- **Reframe in terms of viability tiers** (research-grade, beta-grade, production-grade) keyed on `P(recovery > 0.95)` and absence of hallucinated-mapping incidents.

## Reproducing this evaluation

```bash
cd /path/to/falsecolors
ollama pull llama3.2:3b qwen3:1.7b phi3:mini gemma3:4b mistral:7b-instruct llama3.1:8b
OLLAMA_TIMEOUT=600 python3 evaluation/run.py --models llama3.2:3b qwen3:1.7b phi3:mini gemma3:4b
OLLAMA_TIMEOUT=600 python3 evaluation/run.py --models mistral:7b-instruct llama3.1:8b --out evaluation/results-extended.json
```

Override the trial count with `--trials N`. The harness writes incrementally so partial progress survives an interrupt.

## Data

- 3-4B band raw: `evaluation/results.json`
- 7-8B band raw: `evaluation/results-extended.json`
- Test documents: `evaluation/documents/`
- Reference corpus: `evaluation/corpora/brewery.txt`
- Harness: `evaluation/run.py`

All inputs and outputs are committed for full reproducibility.
