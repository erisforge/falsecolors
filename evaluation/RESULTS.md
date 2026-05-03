# Eris FALSECOLORS Local-Model Evaluation, May 2026

## Summary

Four small local models (1.7B-4B parameters, Q4 quantization) were evaluated as the LLM backend for `falsecolors.py encrypt --backend llm`. The harness ran three sensitive OT/ICS pentest findings through each model three times and recorded round-trip recovery, mapping JSON validity, Caudle Distance against a native brewery corpus, and encode latency.

**Recommendation:**

| Use case | Model |
|---|---|
| Best overall (consistency-first) | **gemma3:4b** |
| Best speed (single-shot, accept variance) | **llama3.2:3b** |
| Avoid | qwen3 family (default thinking mode), phi3:mini for batch use |

`gemma3:4b` produced parseable mapping JSON on 9/9 trials, the largest mean mapping size (14.6 substitutions per document), and the tightest variance on round-trip recovery. `llama3.2:3b` produced the highest mean recovery (0.646) but with 1.6x the standard deviation; it is the recommended choice when speed matters and per-document variance is acceptable. `qwen3:4b` failed every trial at the default 120s timeout and again at 600s due to the model's default thinking mode generating multi-thousand-token internal monologue before emitting the response. `qwen3:1.7b` ran inside the timeout but the same thinking-mode bleed corrupted the cover document and the mapping JSON. `phi3:mini` worked on the medium-length document (3/3 with mean 0.62 recovery) but degraded on the longest and shortest documents to 1/3 valid mappings.

## Methodology

Hardware: Mac, Ollama 0.17.4. All models pulled via `ollama pull <tag>`.

Models tested:

| Tag | Family | Params | Quant |
|---|---|---|---|
| `llama3.2:3b` | Meta Llama 3.2 | 3.2B | Q4_K_M |
| `qwen3:1.7b` | Alibaba Qwen3 | 1.7B | Q4_K_M |
| `phi3:mini` | Microsoft Phi-3 Mini | 3.8B | Q4_0 |
| `gemma3:4b` | Google Gemma 3 | 4B | Q4_K_M |

`qwen3:4b` was attempted but exceeded the request timeout at both 120s and 600s on every trial; it is excluded from the comparison and discussed separately under [Excluded models](#excluded-models).

Test corpus: three pentest finding documents under `evaluation/documents/`:

- `01_reactor_sis_bypass.txt` (172 words, ethylene oxide reactor SIS bypass via Modbus TCP)
- `02_water_scada_creds.txt` (264 words, hardcoded SCADA credentials in pump station firmware)
- `03_substation_iec61850.txt` (242 words, GOOSE message spoofing on substation process bus)

Native brewery corpus: `evaluation/corpora/brewery.txt`, 12 paragraphs of plausible craft-brewery quality-audit prose used both as the SCD reference distribution and as the source for the PPMI embedding vectors.

Each model encoded each document three times via `falsecolors.encode_document(..., backend="llm")` with passphrase `"eval-2026"` and topic `"brewery"`. The harness records:

- **encode_secs** — wall time of `encode_document`.
- **mapping_size** — number of entries in the embedded `domain` map. A value of 0 means the model produced no parseable JSON tail; the cover may still have been rewritten but cannot be reversed.
- **recovery_ratio** — `difflib.SequenceMatcher(None, source, recovered).ratio()` after `decode_document`. 1.0 is a perfect round-trip; 0.0 means the recovered text shares no substring runs with the source.
- **scd** — Caudle Distance of the cover (with the embedded-key footer stripped) against the brewery corpus, in nats.
- **doc_pairs** — number of adjacent content-token pairs in the cover that have shared embedding-vocabulary entries with the corpus.

The harness, results, and corpora are all under `evaluation/`. Raw per-trial data is in `evaluation/results.json`.

`OLLAMA_TIMEOUT=600` was set for the run so that any slow model reached terminal failure rather than hanging the harness mid-trial.

## Results

### Per-model summary

Mean ± stdev across 9 trials (3 documents × 3 trials).

| Model | recovery | mapping_size | SCD (nats) | encode (s) | JSON ok | total fail |
|---|---|---|---|---|---|---|
| llama3.2:3b | 0.646 ± 0.220 | 8.2 ± 3.8 | 1.071 ± 0.139 | 42.8 ± 8.6 | 9/9 | 0/9 |
| gemma3:4b | 0.591 ± 0.138 | 14.6 ± 4.1 | 1.092 ± 0.123 | 62.7 ± 18.2 | 9/9 | 0/9 |
| phi3:mini | 0.460 ± 0.198 | 5.7 ± 5.8 | 1.062 ± 0.107 | 52.9 ± 23.2 | 5/9 | 0/9 |
| qwen3:1.7b | 0.127 ± 0.136 | 5.3 ± 5.7 | 0.980 ± 0.185 | 74.9 ± 31.5 | 9/9 | 0/9 |

"JSON ok" counts trials where `mapping_size > 0`. A nonzero mapping does not guarantee correctness; phi3:mini occasionally produced a mapping JSON that did not match the substitutions actually made in the cover, scoring `recovery=0.000` despite `mapping_size=10` (see [Failure modes](#failure-modes)).

### Per-document detail

```
gemma3:4b
  doc 01_reactor_sis_bypass:    recovery 0.482±0.134   map 11.3±1.2   scd 1.117±0.070   enc 44.0s
  doc 02_water_scada_creds:     recovery 0.744±0.027   map 13.0±0.0   scd 1.207±0.071   enc 65.5s
  doc 03_substation_iec61850:   recovery 0.546±0.034   map 19.3±3.5   scd 0.954±0.030   enc 78.6s

llama3.2:3b
  doc 01_reactor_sis_bypass:    recovery 0.693±0.060   map  9.7±2.5   scd 1.071±0.000   enc 37.0s
  doc 02_water_scada_creds:     recovery 0.442±0.289   map  5.3±5.8   scd 1.220±0.100   enc 38.8s
  doc 03_substation_iec61850:   recovery 0.804±0.056   map  9.7±0.6   scd 0.922±0.027   enc 52.7s

phi3:mini
  doc 01_reactor_sis_bypass:    recovery 0.315±0.274   map  3.3±5.8   scd 1.117±0.016   enc 29.7s
  doc 02_water_scada_creds:     recovery 0.620±0.096   map 11.3±3.5   scd 0.949±0.081   enc 56.2s
  doc 03_substation_iec61850:   recovery 0.444±0.040   map  2.3±4.0   scd 1.119±0.101   enc 72.8s

qwen3:1.7b
  doc 01_reactor_sis_bypass:    recovery 0.123±0.213   map  7.3±4.7   scd 1.274          enc 83.8s
  doc 02_water_scada_creds:     recovery 0.145±0.114   map  1.7±0.6   scd 0.942±0.177   enc 48.1s
  doc 03_substation_iec61850:   recovery 0.112±0.120   map  7.0±8.7   scd 0.891±0.044   enc 92.7s
```

### Findings

**1. gemma3:4b is the most consistent.** Across all nine trials it produced parseable mapping JSON, the largest mean mapping size (14.6 substitutions, vs 8.2 for llama3.2:3b), and the tightest standard deviation on recovery (0.138, vs 0.220 for llama). On the medium-length document it scored a near-deterministic 0.744 ± 0.027 recovery across three trials with identical mapping size of 13. This consistency matters more for FALSECOLORS than peak recovery: a tool that protects sensitive findings cannot have a 1-in-3 chance of producing an unrecoverable cover.

**2. llama3.2:3b has the highest peak recovery but high variance.** Its overall mean recovery of 0.646 is the highest in the cohort, driven by an excellent 0.804 ± 0.056 on document 3. But on document 2 it produced one trial with `mapping_size=2` and another with `mapping_size=11` and the recovery range was 0.114-0.663. For a single-shot interactive use ("encrypt this one finding") llama3.2:3b is the fastest and often the best. For batch use over many documents, the tail risk of a 0.114 trial argues against it.

**3. phi3:mini fails the JSON tail more than half the time on hard documents.** On documents 1 and 3 (shortest and longest), it produced empty mappings on 4 of 6 trials. The documents that triggered failures were the ones with the most numeric identifiers and standard references (Modbus, IEC, NERC CIP, CVE), which seems to crowd out the model's attention budget for the JSON tail. On the medium document with fewer technical density, all three trials succeeded with mean 0.62 recovery. phi3:mini also showed the most concerning failure mode: a trial with `mapping_size=10` and `recovery_ratio=0.000`, indicating the model emitted a mapping JSON that did not match the substitutions it had actually performed in the cover prose.

**4. qwen3 family is unsuitable in default settings.** Both qwen3:4b and qwen3:1.7b run with thinking mode enabled by default. The harness uses the public `falsecolors.py` prompt format with no model-specific overrides, so the model's `<think>` block runs to completion and frequently bleeds into the final output, corrupting both the cover prose and the JSON tail. Round-trip recovery for qwen3:1.7b averaged 0.127 across nine trials with two complete-zero recoveries despite `mapping_size > 0`. A future evaluation pass with a `/no_think` directive prepended to the prompt may produce different results, but in default ergonomic settings these models do not work for FALSECOLORS.

**5. Caudle Distance does not separate the models well.** All four models produced covers with SCD in the range 0.9-1.3 nats against the brewery corpus. The brewery corpus is small (~1700 tokens) and the documents are short (~250 words), so the histograms are sparse and the KL has high variance. SCD as a model-discriminating metric will require larger corpora and longer documents. SCD remains useful as an absolute-quality signal: a hypothetical "perfect" cover would score under 0.1 nats; all models in this evaluation are roughly an order of magnitude from that bar, indicating substantial room for cover-quality improvement (e.g., LLM polish step, larger native corpora, longer cover prose).

**6. Latency scales with thinking output, not parameter count.** gemma3:4b (4B params) ran 62.7s per encode; llama3.2:3b (3.2B params) ran 42.8s; qwen3:1.7b (1.7B params) ran 74.9s. The 1.7B qwen model was the slowest because its thinking mode produced the most tokens overall. For interactive use, the determining factor is whether the model is configured to emit a thinking trace.

## Failure modes

Three distinct failure modes appeared in the data:

**Empty mapping JSON.** The model wrote the cover prose but did not emit a parseable `{...}` tail at the end of its response. The harness records `mapping_size=0` and `decode_document` returns the cover unchanged (only identifier-encoder placeholders are reversed). Recovery ratios of 0.4-0.5 are typical when this happens because the IdentEncoder placeholders are still inverted by their separately-stored map. Affected: phi3:mini on documents 1 and 3.

**Hallucinated mapping JSON.** The model emitted a parseable mapping JSON, but the entries do not match the substitutions actually made in the cover. The inverse mapping then fails to reverse the cover text. Recovery ratio drops to 0.000 despite `mapping_size > 0`. Affected: phi3:mini at least once, qwen3:1.7b multiple times.

**Thinking-mode bleed.** The model's internal thinking trace ends up appended to the cover prose or interleaved with the JSON tail, corrupting both. The harness records a nonzero mapping size (whatever JSON the model finally emitted) and a recovery ratio that may be 0.000 if the cover is unrecognizable, or low-but-nonzero if the cover is partially recovered. Affected: qwen3:1.7b on every trial, qwen3:4b indirectly (it never finishes thinking inside the timeout).

## Excluded models

`qwen3:4b` was attempted at both 120s and 600s timeouts. Every trial ran the request to the timeout boundary without returning a response. Two of the three documents in the smoke run hit the 600s ceiling. The model is excluded from the headline comparison; users who want to use it should set a much higher `OLLAMA_TIMEOUT` and expect 5-10 minute encode latencies per document.

A future evaluation should test:

- `qwen3:4b` and `qwen3:1.7b` with `/no_think` injection at the start of the prompt.
- `gemma3:4b` and `llama3.2:3b` at higher quantization levels (Q5 or Q8) to measure quantization sensitivity.
- A 7-8B reference model (e.g., `mistral:7b-instruct`, `qwen3:8b`, `llama3.1:8b`) as an upper bound on local-model recovery.

## Reproducing this evaluation

```bash
cd /path/to/falsecolors
ollama pull llama3.2:3b qwen3:1.7b phi3:mini gemma3:4b
OLLAMA_TIMEOUT=600 python3 evaluation/run.py
```

The harness writes incrementally to `evaluation/results.json` so partial progress survives an interrupt. Override the model list with `--models llama3.2:3b gemma3:4b` and the trial count with `--trials N`.

## Data

Raw per-trial JSON is at `evaluation/results.json`. Test documents are under `evaluation/documents/`. Reference corpus is at `evaluation/corpora/brewery.txt`. The harness is `evaluation/run.py`. All inputs and outputs are committed to the repo for full reproducibility.
