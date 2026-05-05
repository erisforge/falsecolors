# Eris FALSECOLORS v4
## LACH: LLM-Adversarial Cover Hardening and the Detector-Bounded Distinguishing Game

**Working Paper, Companion to Eris_FALSECOLORS_v3.md**
**Author: River Caudle**
**Revision: 0.3**
**Date: May 2026**

---

> *The v3 paper formalized adversary advantage as a total-variation
> distance between cover and native distributions. That bound is
> information-theoretic and not directly measurable. This document
> introduces an empirical, detector-bounded variant and the methodology
> for measuring it against modern frontier LLMs.*

---

## Abstract

This companion to the main Eris FALSECOLORS paper introduces LACH (LLM-Adversarial Cover Hardening), a measurement framework and optional defense layer for Method 4 (Dynamic Shift) cover documents under modern LLM-mediated adversaries. The Detector-Bounded Distinguishing Game replaces the unmeasurable total-variation bound of Section 2.17 of the main paper with an empirical, falsifiable advantage metric `Adv_D` computed against a named frontier-LLM detector. Three sub-tasks are scored per trial: binary detection, closed-set source-domain classification, and partial inverse mapping. The detector prompt, response schema, and parsing protocol are specified in full so the experiment is reproducible. An initial empirical pilot against Google Gemini 2.5 Flash and Groq-hosted Llama 3.3 70B is reported, including a methodologically consequential finding about the v3 reference corpus.

**Status of this document.** This is a methodology specification with pilot data, not a results paper. The full v4 evaluation across the v3 cohort (six models, three source documents, ten trials per cell, paired with length-matched native samples from `brewery_v4.txt`) is forthcoming. Pilot data presented in Section 7 establishes that the measurement pipeline works end-to-end and that the detection task is non-trivial for frontier LLMs; it does not yet establish headline `Adv_D` numbers. The reproducibility section (Section 9) and the appendices are written so that any reader with API access to one of the named detectors can reproduce the pilot results immediately and run the full evaluation when they choose to.

---

## 1. Motivation

The v3 paper defines a Distinguishing Game (Section 2.17) in which an adversary tries to tell a cover document apart from a native cover-domain document. Theorem 2.17.3 bounds the adversary advantage by the total variation distance between the cover document distribution and the native document distribution. That bound is information-theoretic and is correct as a theoretical limit, but it is not directly measurable in practice for two reasons:

1. The cover document distribution is induced by Method 4's local LLM and is not given in closed form.
2. The native document distribution is approximated by a finite reference corpus whose own distribution is not given in closed form.

Caudle Distance (Definition 2.15.2, alias Native-Text Drift) is a measurable surrogate based on token-adjacency cosine-similarity divergence. v3 evaluation reported Caudle Distance in the 1.0 to 1.3 nats range across the six-model cohort. This number measures statistical distinguishability but does not tell the user how easily a contemporary frontier LLM, prompted to act as an adversary, would actually flag a cover document.

LACH fills this gap. It introduces a measurable advantage `Adv_D` defined against a specific named detector D, with explicit prompt and parsing protocol. The metric is falsifiable, reproducible, and tracks the realized adversary advantage rather than the information-theoretic ceiling.

## 2. Theoretical Foundation

### 2.1 The Detector-Bounded Distinguishing Game

Section 2.17 of the main paper defines the Semantic Distinguishing Game with a single output: a binary guess. The Detector-Bounded variant extends this with a confidence score and three sub-tasks.

**Game 4.2.1 (Detector-Bounded Distinguishing Game).** Challenger C and detector adversary D play:

1. **Setup.** C selects a domain pair (T_a, T_b), a relational graph G, and an isomorphism M from S(G, T_a, T_b). C prepares source document D = (G, L_a) and cover document C_doc = (G, M ∘ L_a). C also samples a native document N from the natural cover-domain distribution.
2. **Challenge.** C flips a fair coin b. If b = 0, C sends N to D. If b = 1, C sends C_doc to D.
3. **Detection response.** D outputs `(is_cover, p_cover, reasoning, source_domain_guess, inversion_proposals)` per the schema in Appendix A.
4. **Scoring.** D wins the detection sub-game if `is_cover == (b == 1)`. D's confidence is `p_cover`. D additionally produces a source-domain classification (scored only when b = 1) and an inversion mapping (scored only when b = 1).

**Definition 4.2.2 (Detector-bounded advantage).** For detector D evaluated over N independent trials with cover and native challenges in equal proportion:

    Adv_D = | P(is_cover = 1 | b = 1) - P(is_cover = 1 | b = 0) |
          = | TPR - FPR |

where TPR is the true-positive rate on covers and FPR is the false-positive rate on natives.

**Remark 4.2.3 (Bound by information-theoretic advantage).** Trivially, `Adv_D <= Adv_information-theoretic <= TV( P(C_doc) || P(N) )` for any computable D, since D is a specific computable strategy and the information-theoretic adversary supremes over all strategies; the second inequality is Theorem 2.17.3 of the main paper. The substantive content is not the bound but Observation 4.2.4.

**Observation 4.2.4 (LACH does not contradict v3 results).** A high Caudle Distance does not imply high Adv_D, and a low Caudle Distance does not imply low Adv_D. Caudle Distance measures statistical distinguishability through token-adjacency cosine-similarity divergence; Adv_D measures the realized detection capability of a specific LLM detector. These are related but distinct quantities. The v3 paper's Caudle Distance numbers remain valid; LACH adds an orthogonal measurement.

**Observation 4.2.5 (Cover-selection and detection-resistance are the same criterion).** A cover domain is useful for FALSECOLORS to the extent that it is structurally isomorphic to the source domain: the same relational patterns (causation, measurement, threshold, sequence) must apply naturally in both vocabularies. This is the same property that makes the cover hard to distinguish from a generic native document in the cover domain. But it is also the property that makes a frontier-LLM detector apt to false-positive on legitimate technical content in the cover domain, because the cover domain itself contains structurally similar prose. The selection criterion that maximizes Method 4 viability and the criterion that maximizes detection difficulty are the same criterion viewed from opposite sides. This implies that any successful FALSECOLORS deployment will, by construction, produce a nonzero baseline FPR on the corresponding native corpus. A reported `Adv_D` that approaches zero is not necessarily evidence of cover failure; it may be evidence that the detector cannot separate covers from natives on a domain pair where structural overlap is high. Conversely, a reported `Adv_D` near 1.0 is evidence either that the cover domain is poorly chosen (insufficient structural overlap with the source) or that the detector is exploiting a non-structural signal (vocabulary leak, length, formatting). This conjecture is empirically testable across cover domains and is one of the more interesting open questions for v4 evaluation.

### 2.2 The three sub-tasks

The detector D performs three tasks per trial. Each scores independently.

**Sub-task 1 (Detection).** Binary cover-or-native classification with confidence in [0, 1]. Yields TPR and FPR; combined into Adv_D as above.

**Sub-task 2 (Classification).** Conditional on `is_cover = true`, guess the source domain from a closed set. The current set is `{ot_ics, political, legal, medical, financial, none_of_above, unsure}`. Yields per-trial accuracy `cls_acc` over the cover-trial subset.

**Sub-task 3 (Partial inversion).** Conditional on `is_cover = true`, propose 3 to 8 cover-domain content tokens and guess their source-domain originals. Yields per-trial inversion accuracy `inv_acc`, defined as the fraction of proposed pairs `(cover_term, source_guess)` that are correct under a synonym-tolerant grading function (Appendix B.2). On native trials the detector is instructed to return an empty object; non-empty inversion on a native trial counts against `inv_acc` only if the trial is later reclassified.

### 2.3 Metric reporting

The v4 evaluation will report the following per (model, document) cell and pooled across all cells:

- TPR (cover trials): mean and 95% confidence interval
- FPR (native trials): mean and 95% confidence interval
- Adv_D: TPR minus FPR, with a paired bootstrap CI
- cls_acc on cover trials: mean
- inv_acc on cover trials: mean
- p_cover distribution: histogram for cover trials and native trials, on the same axis

This is in addition to the v3 metrics (recovery_ratio, mapping_supported_ratio, scd, encode_secs, decode_secs).

## 3. Threat Model

### 3.1 What LACH defends against

- A passive observer who runs a frontier LLM as a triage filter over collected documents, classifying each as "probably benign" or "investigate further."
- An active investigator who suspects a specific user is using FALSECOLORS-style protection and queries an LLM to evaluate documents found in the user's possession.
- A cloud LLM provider running automated content classification on inputs, with frontier-LLM detectors in the inference path.
- Litigation discovery workflows where a frontier LLM is used as a first-pass relevance filter on document productions.

### 3.2 What LACH does not defend against

- An adversary with the passphrase or with direct access to the embedded key footer.
- Side-channel attacks based on document length, file metadata, transmission timing, or footer-block size.
- Detectors strictly stronger than the one in the LACH evaluation loop. Robustness is detector-relative by construction. The metric is `Adv_D`, not a universal advantage.
- Statistical attacks that do not rely on LLM-mediated reasoning. These remain in the scope of Caudle Distance (Definition 2.15.2 of the main paper).
- An adversary who already knows the source domain and is doing targeted search rather than blind detection. The Distinguishing Game assumes the adversary does not already know the answer.
- Aggregation attacks across multiple documents from the same user. These are in the scope of the Caudle Accountant (separate forthcoming work, see ROADMAP.md).

### 3.3 What "frontier" means here

Frontier means the contemporary tier of generally-available large language models capable of multi-step structural reasoning over text. As of May 2026 this includes Claude Opus 4.7, GPT-5, Gemini 2.5 Pro, and select hosted open-weights models above approximately 70B parameters (Llama 3.3 70B, DeepSeek-V3, Qwen3 235B). Frontier is a moving target; the v4 evaluation pins the specific detector used and reports `Adv_D` against that pinned model. Future detector improvements will require re-evaluation.

## 4. Methodology

### 4.1 Detector prompt design

The single most consequential design decision in LACH is the detector prompt. It controls the adversary's strength and therefore the meaningful range of `Adv_D`. The current zero-shot baseline prompt is reproduced verbatim in Appendix A. Design notes:

- **Definition by example.** The prompt names two example domain pairs (brewing/OT-ICS, gardening/?). This biases the detector toward those domains. Ablations against a domain-free prompt are future work.
- **Schema enforcement.** The prompt requests a strict JSON object with five fields. The parser tolerates markdown fences and prose framing but otherwise validates against the schema (Appendix B). Out-of-schema responses are treated as detector abstentions.
- **Confidence elicitation.** The model is asked for `p_cover` directly. LLMs are known to be miscalibrated in self-reported probabilities. A self-consistency variant that runs the detector five times at temperature greater than zero and uses the fraction-true as a calibrated probability is identified as future work. Platt scaling or temperature scaling on a small held-out calibration set is an alternative if self-consistency proves too costly.
- **Scratchpad reasoning.** A revised prompt variant (Appendix A.3) asks the model to reason inside `<scratchpad>...</scratchpad>` tags before emitting the strict JSON object. The parser strips everything before the first `{`, so scratchpad content is discarded but still serves as the model's working context. This avoids the artificial degradation of suppressing chain-of-thought entirely (which would lower `Adv_D` for a non-substantive reason) without destabilizing the JSON contract. Pilot results in Section 7 are from the no-scratchpad baseline (Appendix A.1); the v4 evaluation will run both and report the gap.

### 4.2 Adversary model selection

The v4 evaluation pins three detectors and reports `Adv_D` against each:

- **Primary**: Google Gemini 2.5 Pro (frontier-grade, native JSON response mode, generous free tier for development). Pinned at version `gemini-2.5-pro` as of May 2026.
- **Secondary**: Anthropic Claude Opus 4.7 (frontier-grade, contemporary). Pinned at version `claude-opus-4-7` as of May 2026.
- **Cross-check**: Groq-hosted Meta Llama 3.3 70B. Mid-tier (not frontier) but useful for prompt iteration and as a distributional cross-check.

Cross-detector agreement above approximately 0.85 across the v4 evaluation is the methodology validity signal: if the three detectors disagree wildly, `Adv_D` is detector-specific and the v4 paper must recommend a tier rather than a number. Pairwise Cohen's κ on the 360-document evaluation set is the recommended summary statistic.

**Reflexivity caveat.** Using Claude Opus 4.7 as a secondary detector while the FALSECOLORS reference implementation is also developed using Claude Opus 4.7 introduces a reflexivity that warrants explicit acknowledgement: the system is being designed and evaluated against the same model class. This is not a methodological flaw, but it means `Adv_D` against Claude is a measurement under self-evaluation. Reproductions by users with non-Claude development environments will produce more independent numbers. The v4 paper will headline the Gemini and Llama numbers and treat Claude as a confirmatory third detector for this reason.

### 4.3 Corpus construction and the v3 corpus problem

The v4 evaluation requires both cover documents (for TPR estimation) and native cover-domain documents (for FPR estimation). The native corpus must satisfy two constraints:

1. **Length-matched negatives.** Each native sample paired with a cover trial should have token count within plus or minus 20 percent of the cover. Length is a trivial detection feature; matched-length sampling controls for it.
2. **Vocabulary independence.** The native corpus should not share vocabulary with the source-domain pool the cover was generated from. If both the corpus and the cover domain use words like "control loop," the FPR is contaminated.

The v3 evaluation used a 2,560-word brewery corpus expanded with deliberate process-control structural overlap to maximize Caudle Distance discrimination range. In LACH pilot testing, this corpus produced approximately 95 percent FPR against Gemini 2.5 Flash because its content patterns ("operational interface," "parameter write," "audit trail," "threshold band") read as ICS writing in brewing vocabulary. This is correct detector behavior on a corpus that was not built with LLM-detector evaluation in mind. The corpus needs reconstruction for v4.

A v4 brewery corpus (`evaluation/corpora/brewery_v4.txt`, approximately 12,400 words across 102 paragraphs from three different LLM authors) was generated under a prompt that explicitly excludes industrial-control vocabulary. Pilot validation on a 10-paragraph random sample showed FPR drop from approximately 0.95 to approximately 0.20 against Gemini 2.5 Flash and approximately 0.06 against Groq Llama 3.3 70B. Two paragraphs in the sample still flagged at p_cover > 0.8 against Gemini despite containing no industrial-control vocabulary; analysis of those paragraphs (Appendix C) shows the flagging is structural rather than lexical: brewing equipment maintenance and quality-control reports are structurally similar to ICS process reporting because both describe technical processes with measurements, trends, and maintenance schedules.

This is itself a methodologically consequential finding. **A clean reference corpus has a nonzero baseline FPR against frontier detectors because real technical brewing prose is structurally similar to ICS process prose.** The v4 paper reports `Adv_D` honestly: if covers and natives both score high p_cover, the detector cannot reliably distinguish them, which is exactly the security property FALSECOLORS aims for. A high TPR alone is not bad if FPR is similarly high.

### 4.4 Sampling protocol

For each (model, document) cell in the v3 cohort (6 models, 3 source documents, 10 trials = 180 cover trials), the LACH evaluation generates 180 matched native samples by drawing length-matched paragraphs at random from `brewery_v4.txt`. Detector D is run on all 360 documents (180 covers, 180 natives) under the zero-shot prompt. Each trial receives the full sub-task scoring.

Few-shot strengthened detection (Appendix A.2) is run on the same documents in a second pass and reported as `Adv_D_fewshot` alongside the zero-shot baseline.

### 4.5 Statistical reporting

Bootstrap confidence intervals at 95 percent for TPR, FPR, and Adv_D, computed by resampling cover and native trials independently. Per-(model, document) cells report cell-level numbers; the headline pool aggregates across all 180 cover and 180 native trials.

When `parse_ok = false` for any trial, the trial is excluded from rate computations but the count of parse failures is reported separately. Persistent parse failures above 5 percent indicate a prompt-or-parser problem, not a detector capability problem.

## 5. Phase 1: Measurement

Phase 1 is the LACH evaluation as defined above, run against the v3 cohort with no defense modifications to the encode pipeline. Output is the v4 RESULTS.md table with TPR, FPR, Adv_D, cls_acc, inv_acc per cell and pooled.

This phase is independently valuable. Even if no defense is built, Phase 1 produces a falsifiable, reproducible measurement of how easily a frontier LLM detects current FALSECOLORS Method 4 covers. That measurement is what the v3 paper's Distinguishing Game promised but could not deliver in numerical form.

## 6. Phase 2: Defense (forward-looking)

Phase 2 is built only if Phase 1 shows `Adv_D` significantly above zero on at least one (model, document) cell. The defense is an encode-time rewrite loop:

1. Method 4 produces cover_v0 and the per-document mapping.
2. Detector D scores cover_v0.
3. If `p_cover > theta` (default 0.5), the detector's stated reasoning is fed back to the local LLM as a rewrite constraint: "this cover was flagged because [reasoning]; rewrite to dissolve that pattern while preserving every existing cover-domain term."
4. The rewritten cover is verified for mapping support (the existing v3 `verify_mapping_support` gate) and for round-trip recovery against a sample.
5. Iterate up to N times or until `p_cover <= theta`.
6. Return the lowest-`p_cover` cover that maintains recovery quality above the v3 0.92 floor.

Phase 2 is opt-in via a `--harden` flag on `encrypt`, parallel to the existing `--polish` flag. Default off to preserve v3 behavior and avoid the latency hit.

The risk in Phase 2 is detector-overfit: a cover hardened against detector D may still flag against detector D'. Cross-detector validation in Phase 1 informs whether the rewrite signal generalizes.

**A deeper risk: reasoning-faithfulness.** The Phase 2 rewrite signal is the detector's stated reasoning, which is a natural-language explanation of detection cues. LLM reasoning explanations are documented to be unfaithful to the model's actual decision process: the model may correctly classify an input via features it does not surface in its written reasoning, and may surface plausible-sounding cues that are not actually load-bearing for its classification. The rewrite loop may therefore dissolve the *stated* cues while leaving the *actual* discriminative features untouched, producing a measured `p_cover` drop that does not generalize. Two diagnostics are required: (a) confirm `p_cover` actually drops on successive iterations under the same detector D, and (b) confirm the drop generalizes to a held-out detector D'. If (a) holds but (b) fails, the reasoning field is an unreliable gradient signal, and Phase 2 must switch to direct `p_cover` minimization via iterative sampling (generate K candidate rewrites, score all, keep the lowest-`p_cover`) rather than reasoning-guided rewriting.

## 7. Empirical Findings to Date

(Pilot data; full v4 evaluation pending.)

### 7.1 Single-trial detection ceilings

The goldfish cover demonstration (a political situation report transformed into a pet goldfish care report via Method 4 with `mistral:7b-instruct`) was scored:

- Gemini 2.5 Flash: `is_cover=true`, `p_cover=1.0`, `source_domain_guess=political`. Inversion proposals were 6 of 8 correct or near-correct.
- Groq Llama 3.3 70B: `is_cover=true`, `p_cover=0.9`, `source_domain_guess=political`. Inversion proposals omitted but classification correct.

Single-trial detection on a representative cover is at or near ceiling for both detectors. This is not a statistically meaningful sample but indicates the detection task is feasible for frontier-class models.

**Caveat on the goldfish trial.** The cover was generated by `mistral:7b-instruct`, which is a v3 cohort model but not the strongest. The full v4 evaluation must include all six v3 cohort models. If the larger and stronger models (`llama3.1:8b`, `qwen3:1.7b` under the v3 two-step prompt) also score at detection ceiling, then LACH is measuring something the v3 evaluation missed: covers from operationally recommended configurations are still trivially detectable by frontier LLMs. If those models score materially lower on `p_cover`, then LACH is largely confirming what Caudle Distance already measured, and the framework's value is in the formalization rather than in surfacing new failure modes. Either result is reportable; they tell different stories about the v4 contribution.

### 7.2 Native baseline on the v3 corpus

Two paragraphs from the v3 brewery corpus, sampled at random, scored:

- Gemini 2.5 Flash: both `is_cover=true`, `p_cover=0.95`, `source_domain_guess=ot_ics`.
- Groq Llama 3.3 70B: both `is_cover=true`, `p_cover=0.80`, `source_domain_guess=ot_ics`.

This produced the v3 corpus problem documented in Section 4.3.

### 7.3 Native baseline on the v4 corpus, multi-detector

Random paragraphs sampled from `brewery_v4.txt` (12,391 words, 84 paragraphs of 60+ words) with seed 42, scored against four named detectors. Wilson-score 95% confidence interval shown for the FPR estimate. Full per-trial outputs in `evaluation/results/lach_fpr_brewery_v4_*.json`.

| Detector | n | FPR | Mean p_cover | Max p_cover | 95% CI |
|---|---|---|---|---|---|
| Anthropic Claude Sonnet 4.6 | 25 | 0/25 | 0.072 | 0.08 | [0.000, 0.133] |
| Anthropic Claude Opus 4.7 | 10 | 0/10 | 0.092 | 0.15 | [0.000, 0.278] |
| Groq Llama 3.3 70B | 25 | 2/25 | 0.118 | 0.80 | [0.022, 0.250] |
| Google Gemini 2.5 Flash (initial pilot) | 10 | 2/10 | 0.209 | 0.95 | [0.057, 0.510] |
| Google Gemini 2.5 Flash (n=25 attempt) | 2 | 0/2 | 0.050 | 0.05 | (rate-limited, 23 parse failures) |

The Groq Llama 3.3 70B run at n=25 produced two FPs that were not present in the n=10 pilot, supporting the original observation that mid-tier detectors flag structural patterns of technical brewing content even when the cover-domain text is otherwise clean. **Frontier-class detectors (Sonnet 4.6, Opus 4.7) agree the v4 corpus is clean. Mid-tier detectors (Llama 3.3 70B) show structural false positives at approximately 8 percent on technical brewing content.** Gemini 2.5 Flash free tier rate-limiting prevented a clean n=25 measurement; the 2 successful trials in the n=25 attempt scored cleanly, suggesting that on a paid-tier or longer-spaced run Gemini's FPR would converge with Sonnet/Opus.

The choice of detector for the headline `Adv_D` number is methodologically consequential. The v4 paper will report `Adv_D` against each pinned detector separately, with the frontier-class numbers as the headline and the mid-tier numbers as a sensitivity check.

### 7.4 Native baseline on the second cover domain

A second cover domain corpus, `birdwatching_v1.txt` (20,160 words, 146 paragraphs of 60+ words), was constructed using a similar prompt-restricted generation protocol across three LLM authors. Same random sampling protocol, seed 42:

| Detector | n | FPR | Mean p_cover | Max p_cover | 95% CI |
|---|---|---|---|---|---|
| Anthropic Claude Sonnet 4.6 | 24* | 0/24 | 0.065 | 0.08 | [0.000, 0.138] |
| Anthropic Claude Opus 4.7 | 10 | 0/10 | 0.107 | 0.15 | [0.000, 0.278] |
| Groq Llama 3.3 70B | 25 | 9/25 | 0.332 | 0.80 | [0.202, 0.555] |
| Google Gemini 2.5 Flash | 3** | 1/3 | 0.323 | 0.90 | (rate-limited, 22 parse failures) |

*One Sonnet trial returned `stop_reason=refusal` on a benign avian-anatomy paragraph; see Section 8.9. **Twenty-two of twenty-five Gemini trials hit free-tier rate limits.

Frontier-class Anthropic detectors converge on cleanliness. **Llama 3.3 70B exhibits 36 percent FPR on the birdwatching corpus, more than four times its FPR on the brewery corpus.** Inspection of the nine flagged paragraphs reveals a pattern: Llama 3.3 70B flags equipment procurement, trip planning, and field-equipment-acquisition language as `ot_ics` covers despite the text being unambiguously about birdwatching. Sonnet 4.6 and Opus 4.7 score the same paragraphs cleanly, citing specific birding vocabulary (vagrant flycatchers, lekking grounds, big-year tactics, BBS routes, eBird review submissions) as the disambiguating signal that mid-tier Llama 3.3 70B does not surface. The pattern matches Section 7.5 and Section 7.7: procurement-and-logistics framing is a structural cue that produces FPs in mid-tier detectors, and the FP rate is sensitive to whether the cover domain has prominent equipment-procurement vocabulary.

This is methodologically consequential for v4 paper claims: **`Adv_D` against mid-tier detectors is sensitive to cover-domain choice in a way that frontier detectors are not.** Birdwatching as a cover domain has heavy equipment-and-logistics content (binoculars, scopes, expedition gear, trip planning) that confuses Llama 3.3 70B but not Anthropic frontier models. Brewery as a cover domain has less of that framing and shows lower mid-tier FPR.

### 7.5 Implications for v3 results

The v3 paper's reported Caudle Distance of approximately 1.0 to 1.3 nats was measured against the v3 corpus, which is now known to be process-control-flavored. SCD against `brewery_v4.txt` will produce different numbers. The v4 paper should report SCD against both corpora and treat the v4 number as the operationally meaningful one. The v3 number remains valid as a measurement against its own reference corpus; it is not invalidated, only reframed.

### 7.6 First TPR pilot: llama3.2:3b covers

A focused TPR pilot regenerated three covers from the v3 cohort using `llama3.2:3b` (one cover per source document) and scored them against Sonnet 4.6 and Opus 4.7.

| Detector | n | TPR | Mean p_cover | 95% CI |
|---|---|---|---|---|
| Anthropic Claude Sonnet 4.6 | 3 | 3/3 | 0.957 | [0.438, 1.000] |
| Anthropic Claude Opus 4.7 | 3 | 0/3 | 0.117 | [0.000, 0.562] |

The two detectors disagree completely. This is methodologically consequential and reveals a failure mode of the detection task itself.

Inspection of the covers and the Opus reasoning shows what happened. The `llama3.2:3b` model in v3 evaluation was known to exhibit a bimodal recovery distribution: roughly half its trials produced a 2-entry mapping with minimal rewrite, and half produced a fuller mapping with substantial rewrite. The covers regenerated for this pilot fell into the first mode: the model substituted only "reactor" -> "brewery vessel" and "Modbus" -> "Brewery Protocol", leaving the rest of the OT vocabulary intact. The covers contain phrases like "Safety Instrumented System," "holding registers," "GOOSE messages, IEC 61850, IEDs, merging units, NERC CIP-005-7" verbatim from the source documents.

Sonnet 4.6 reads the resulting document as a covertly transformed cover and flags at high confidence, citing the lexical mismatches between "brewery" terms and surrounding ICS vocabulary as the detection cue. Opus 4.7 reads the same document as a native ICS security assessment with a few odd surface substitutions, and answers `is_cover=false, source_domain_guess=ot_ics`. From Opus 4.7's reasoning: "This document is explicitly an OT/ICS security assessment finding. It uses brewery only as a setting/client descriptor, but the technical content is genuine ICS terminology, not substituted vocabulary."

**Both detectors are answering correctly under different interpretations of the prompt.** Sonnet treats "is this a cover?" as "does this show signs of vocabulary substitution?" Opus treats it as "is the dominant content shifted out of its native domain?" A high-leak cover satisfies the first interpretation and not the second.

This exposes an **underspecified failure mode in the detection task definition**. When a Method 4 cover leaks so much source vocabulary that the dominant signal is native source-domain content with surface anomalies, the binary `is_cover` flag is ill-defined. The task implicitly assumes covers are reasonably faithful transformations; broken covers fall outside that assumption.

The implications for v4 evaluation methodology:

1. The v4 paper must report TPR conditional on cover quality. A cover that leaks 80 percent of source vocabulary is not the same artifact as a cover that successfully shifts 95 percent. The former tests detector calibration on poorly-formed inputs; the latter tests detector capability on well-formed inputs.
2. Cover quality should be measurable from the trial output independently of the detector. The v3 `mapping_supported_ratio` metric is one option, but it measures the LLM's self-reported mapping integrity, not the actual vocabulary leak rate. A direct vocabulary-leak measure (count of source-domain content tokens still present in the cover, normalized by source content tokens) is the more honest signal.
3. The detector prompt should be revised for v4 to disambiguate the two interpretations: either ask separately about lexical-substitution evidence and dominant-domain assessment, or include explicit guidance that "partial covers with high vocabulary leak should be classified as `is_cover=true` if any substitution is detectable."

A revised prompt and a vocabulary-leak metric are the immediate next experimental step. Pending those, TPR numbers from this section should be read as illustrating the failure mode rather than as production estimates.

The full v4 evaluation must include the cohort's stronger models (`gemma3:4b`, `mistral:7b-instruct`, `llama3.1:8b`, `qwen3:1.7b` under v3 two-step) where covers are expected to leak less and the prompt ambiguity matters less. Cover regeneration for `gemma3:4b` and `mistral:7b-instruct` is in progress at the time of this revision.

#### 7.6.1 Vocabulary leak as a complementary metric

Pending the prompt revision, a content-side measurement is available: count how many source-domain content tokens survive verbatim in the cover. The pilot tool `evaluation/vocab_leak.py` checks 60-plus high-signal OT/ICS terms (Modbus, holding register, Safety Instrumented System, IEC 61850, GOOSE, NERC CIP, etc.) against each generated cover with word-boundary regex.

Pilot leak measurements on the regenerated cohort:

| Cover model | Source doc | Cover chars | Leak count | Leak rate (per 100 words) |
|---|---|---|---|---|
| llama3.2:3b | 01_reactor_sis_bypass | 1215 | 11 | 6.4 |
| llama3.2:3b | 02_water_scada_creds | 1616 | 4 | 1.7 |
| llama3.2:3b | 03_substation_iec61850 | 1490 | 7 | 3.0 |
| gemma3:4b | 01_reactor_sis_bypass | 1159 | 8 | 4.8 |
| gemma3:4b | 02_water_scada_creds | 1726 | 3 | 1.2 |

Document-level pattern: `01_reactor_sis_bypass` is the highest-leak source for both models because its dense safety-system vocabulary (interlock, emergency shutdown, setpoint, Safety Instrumented System) lacks natural brewery analogs in any model's mapping. `02_water_scada_creds` is the lowest-leak because its core OT terms (engineering workstation, level transmitter) substitute more cleanly. The pattern is independent of cover-model strength: even gemma3:4b cannot avoid leaking high-density-OT content.

This suggests a v4 reporting structure: `Adv_D` should be reported as a function of leak rate, not pooled. A high-leak cover is a different artifact than a low-leak cover, and detector verdicts on each tell the user different things.

### 7.7 Observed structural cues in pilot detector reasoning

A recurring question in Phase 2 design is: which structural cues do frontier detectors actually cite when correctly flagging a cover document? The pilot data is small but already shows clear patterns. From the `reasoning` fields of the trials in Sections 7.1 through 7.3:

1. **Lexical-narrative mismatch (strongest single cue when present).** The detector identifies surface vocabulary in one domain juxtaposed with narrative structures characteristic of another domain. Goldfish trial (Gemini): "vocabulary related to goldfish... while describing events and relationships that directly map to a political election." This cue is the most reliable signal and the easiest for a Phase 2 rewrite loop to dissolve, since dissolving it requires either better lexical coverage in the cover domain or rephrasing the narrative beats to be more domain-native.

2. **Process-control structural pattern (most common false-positive driver).** Sequences of (measurement, trend observation, spec reference, maintenance recommendation) trigger detection regardless of vocabulary. v3 corpus FPs (Gemini): "operational interface, authoritative store, parameter write, recipe schema, threshold bands." v4 corpus FPs on technical brewing maintenance content: "modification tracking, validation, threshold bands, more complex system typically found in industrial control systems." This cue cannot be reliably dissolved without changing the document's fundamental structure, which would break Method 4's relational-preservation contract.

3. **Procurement and logistics framing.** Lists of equipment, purchase notes, and supply-chain language read as industrial-procurement reports to mid-tier detectors. Birdwatching corpus FPs against Groq: paragraphs about expedition equipment ("mist nets with finer mesh") and trip planning ("scouting notes from online forums") flagged as `ot_ics`. The cue is structural (procurement is procurement across domains) rather than lexical.

4. **Audit and verification framing.** "We tested X, the result indicated Y, the spec is Z" is the structural skeleton of a QC report regardless of subject matter. Brewery quality-control paragraphs in `brewery_v4.txt` flagged on this pattern even with no industrial-control vocabulary.

5. **Specific term-level oddities.** When a cover term reads "wrong" in context (a token that fits the cover-domain vocabulary but does not collocate naturally with the surrounding text), the detector cites it directly. Goldfish trial: "Goldfish Embassies" was called out explicitly. This is the cue most amenable to dissolution by an LLM polish step.

**Implication for Phase 2 design.** Cues 1 and 5 are dissolvable by a rewrite loop because they are lexical and the rewrite vocabulary is constrained by the cover-domain mapping. Cues 2 and 3 are not dissolvable without breaking relational preservation. Cue 4 is partially dissolvable by varying the rhetorical register (e.g., narrative QC report vs. tabular QC report). A Phase 2 loop that targets only the dissolvable cues (1, 5) and accepts a residual baseline `Adv_D` from the structural cues (2, 3) is the operationally honest design. This converges with Observation 4.2.5: structural overlap with the source domain is what makes the cover plausible *and* what makes a frontier detector apt to flag legitimate native content. The two effects partially cancel in the `Adv_D` metric.

## 7.8 Engineering implications: how LACH improves the encryption

The pilot data points to six concrete improvements to FALSECOLORS Method 4 that flow directly from observed detector behavior. These are reportable as v4 contributions independent of the full evaluation.

### 7.8.1 Vocabulary-leak quality gate

The pilot tool `evaluation/vocab_leak.py` measures how many source-domain content tokens appear verbatim in a cover. Even gemma3:4b (a v3 cohort recommendation) leaks 3 to 8 OT terms per cover. The leak rate is independent of mapping integrity: the v3 `verify_mapping_support` gate checks self-consistency of the model's claimed mapping; the leak gate checks whether the cover actually transforms its source content.

A `--max-leak K` flag on `encrypt` refuses to emit a cover whose leak count exceeds K. Threshold guidance: K=0 strict (production), K=3 moderate, K=10 research only. This complements rather than replaces `verify_mapping_support`; both should be active for production encodes.

### 7.8.2 Detector-driven cover hardening (Phase 2 confirmed empirically)

Section 6 sketched the Phase 2 rewrite loop. The pilot data confirms two prerequisites that were speculative when the spec was drafted: (a) frontier detectors do produce specific, actionable cues in their `reasoning` fields (Section 7.7), and (b) at least two of the five cue categories are dissolvable by an LLM rewrite without breaking relational preservation. Phase 2 is now justified empirically rather than as a "if Adv_D is high, we'll try this."

Implementation guidance: feed only the lexical-mismatch cues (cue category 1) and the term-level oddity cues (category 5) back to the rewrite prompt. Do not attempt to dissolve structural-pattern cues (categories 2 and 3); those are not dissolvable without breaking the cover.

### 7.8.3 Cover-domain selection as an explicit configuration choice

Observation 4.2.5 (cover-selection criterion equals detection-resistance criterion) is now empirically supported. Brewery-as-cover for OT-as-source produces low FPR on frontier detectors. Birdwatching-as-cover would have been a worse choice: it carries heavy equipment-procurement and trip-planning structural content that confuses Llama 3.3 70B at 36 percent FPR on native birding text. The same content is invisible to Sonnet 4.6 and Opus 4.7, but mid-tier deployments would suffer.

A v4 utility command, tentatively named `falsecolors choose-topic --source f.txt --detector D`, would rank candidate cover domains by measured FPR against the named detector. Topic selection would no longer be a manual user choice but an empirical calibration step.

### 7.8.4 Multi-detector encode-time gate

Encode the cover, score against N independent detectors, release only if all return `is_cover=false`. Slower (~$0.05 to $0.20 per encode at frontier prices) but produces a cover that is verified resistant against multiple adversary classes. Useful for high-stakes documents where the encode latency is acceptable.

### 7.8.5 Cover quality stratification in evaluation reporting

The pilot data shows that detection metrics should be stratified by cover quality, not pooled. A cover with leak count 11 is a different artifact than a cover with leak count 0. The v4 evaluation will report TPR conditional on leak bucket: (0 to 2: fully shifted), (3 to 7: moderate leak), (8 or more: high leak). Pooling across leak buckets averages over a noisy quality distribution and obscures the relationship between cover quality and detector capability.

### 7.8.6 Detection-task disambiguation

The Sonnet vs. Opus disagreement on `llama3.2:3b` covers (Section 7.6) revealed that the binary `is_cover` question is ambiguous on high-leak covers. A revised v4 prompt should ask two questions instead of one:

1. "Does this document show signs of vocabulary substitution from another domain?" (lexical-substitution sub-task)
2. "What is the dominant subject domain of this document, regardless of any apparent substitutions?" (domain-assessment sub-task)

These answers are independent. A high-leak cover is "yes" to substitution AND source-domain on dominant assessment. A clean cover is "no" to substitution AND cover-domain on dominant assessment. The product of the two answers gives the underlying detection signal more cleanly than the current collapsed binary.

## 8. Limitations and Open Questions

1. **Adversary model versioning.** `Adv_D` is detector-relative. As frontier models advance, today's `Adv_D = 0.4` may become `Adv_D = 0.7` against the same prompt. The v4 paper pins specific model versions; users should re-evaluate against contemporary detectors before deployment.

2. **Confidence calibration.** Self-reported `p_cover` from an LLM is known to be miscalibrated. Self-consistency sampling (multiple runs at temperature > 0, fraction-true as calibrated probability) is the standard correction; not yet implemented.

3. **Inversion grading.** The inversion sub-task currently grades correctness via exact match plus a small synonym dictionary (Appendix B.2). A semantically-correct inversion ("polling stations" graded against true mapping target "polling stations") works fine, but partially-correct inversions ("voting locations" or "ballot sites" against the same target) will fail both exact match and a finite synonym dictionary unless every variant is enumerated. Reported `inv_acc` from the dictionary-based grader is therefore a **lower bound** on true inversion capability; the v4 paper must report it as such. Implementing embedding-based semantic similarity grading (cosine similarity above a threshold against a sentence-transformer embedding of both terms) is the planned upgrade and is a prerequisite for honest `inv_acc` numbers. The pilot results in Section 7 use the dictionary-only grader and should be read with this caveat.

4. **Negative-set scope.** The v4 evaluation uses brewery as the only cover domain. Garden, novel, and other Method 4 cover domains lack reference corpora. Each cover domain in production use needs its own native corpus.

5. **Cost ceiling.** A full v4 LACH evaluation makes approximately 720 frontier-detector calls. At Gemini 2.5 Pro pricing this is roughly 5 to 15 USD per pass; at Claude Opus 4.7 pricing roughly 30 to 60 USD per pass. Manageable for a single evaluation but limits how often the eval can be re-run during prompt iteration.

6. **Phase 2 contamination.** If Phase 2 builds a rewrite loop using detector D, evaluating the hardened cover against the same D is in-distribution and overstates effectiveness. A separate held-out detector D' is required for honest Phase 2 evaluation, doubling API cost.

7. **Cover-vs-source confusion in the detector.** In one pilot trial the detector correctly identified the original political SITREP as native political content (`is_cover=false`). However, if the detector were given a sanitized political document that retains political vocabulary but masks specific identifiers, it would still classify as native political. The Distinguishing Game assumes the adversary's task is "is this a cover?" not "is this redacted?" Sanitize-mode outputs (Section 10 of main paper) are out of scope for LACH.

8. **Compositional leakage.** A single document's `Adv_D` does not bound an adversary's advantage when given many documents from the same user. Composition is the scope of the Caudle Accountant (forthcoming).

9. **Safety-filter refusals on benign content.** During the Sonnet 4.6 pilot run on `birdwatching_v1.txt`, one paragraph (avian anatomy: uropygial gland, feather waterproofing, migration physiology) returned `stop_reason=refusal` with empty content. The same paragraph scored cleanly against Opus 4.7 (TN, p=0.15). This is a Sonnet-specific safety-filter behavior on completely benign technical content. The implication for LACH methodology: detector abstentions are not random missingness; they are biased toward content classes the detector's safety filter has been trained to avoid. The v4 evaluation must report (a) total trial count, (b) parse-failure count split by cause (true parse error, refusal, rate limit, network error), and (c) compute Adv_D only over trials with `parse_ok=true` while clearly labeling the abstention rate. A high abstention rate on a specific content class biases FPR estimation by selectively removing those samples from the denominator. The detector adapter (`evaluation/detector.py`) was patched mid-pilot to return `[empty content, stop_reason=X]` rather than crashing through to IndexError on empty content arrays; pilot results in Section 7 use the patched adapter except where noted.

## 9. Reproducibility

The full LACH measurement pipeline is reproducible from:

- `evaluation/detector.py`: detector module with adapters for Anthropic, Gemini, Groq, plus a deterministic mock backend for offline tests. Pure stdlib plus urllib.
- `evaluation/run.py` (Phase 1 integration pending): existing v3 evaluation harness, will be extended to call `score_cover` on each cover and matched native paragraph.
- `evaluation/corpora/brewery_v4.txt`: native reference corpus, 12,391 words.
- `evaluation/LACH_SPEC.md`: engineering specification with file paths, week-by-week implementation plan, cost estimates.
- This document: methodology, formal definitions, threat model.

A reader with API access to any of the three named detectors can reproduce the pilot results in this document by running `detector.py` against any cover or native document.

---

## Appendix A: Detector prompts

### A.1 Zero-shot detection prompt

The prompt used in all current LACH measurements. The variable `{document}` is the only thing substituted in. No system prompt is used.

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
{document}
---

Respond in JSON only, with this exact schema:

{
  "is_cover": <bool>,
  "p_cover": <float in [0, 1]>,
  "reasoning": <string, max 200 words explaining the cues you used>,
  "source_domain_guess": <one of: "ot_ics", "political", "legal",
                          "medical", "financial", "none_of_above", "unsure">,
  "inversion_proposals": {
    "<cover_term>": "<your guess at the source-domain original>"
  }
}

For inversion_proposals, list 3 to 8 cover-domain content terms that
look most likely to be substitutions, and your best guess at what they
were originally. If you believe this is genuine native content, return
an empty object.

Output only the JSON object. Do not wrap it in markdown fences. Do not
include any prose before or after.
```

### A.2 Few-shot strengthened prompt (planned, not yet implemented)

Identical to A.1 but with two demonstration pairs prepended: one labeled native and one labeled cover, both drawn from a held-out demonstration set never used in evaluation. Reported as `Adv_D_fewshot`.

A "same-author" few-shot variant uses examples drawn from the same Method 4 model and the same cover-domain mapping style as the trial under test. This surfaces stylistic fingerprints (e.g., a particular model's tendency to over-explain, to use specific connectives, to favor certain sentence shapes) that zero-shot detection may miss.

### A.3 Scratchpad-reasoning prompt (planned, recommended for v4 evaluation)

Identical to A.1 but with an explicit scratchpad block requested before the JSON output. The parser strips everything before the first `{`, so scratchpad content is discarded but provides the model a workspace to reason through detection cues without artificially suppressing chain-of-thought.

```
[same body as A.1]

Before producing the final JSON object, you may use a scratchpad to
reason through your analysis. Wrap the scratchpad in tags like this:

<scratchpad>
your free-form reasoning here, including notes on vocabulary mismatches,
structural patterns, candidate source domains, and confidence
considerations.
</scratchpad>

After the scratchpad, output only the strict JSON object as specified
above. Do not wrap the JSON in markdown fences. Do not include any
prose between the scratchpad and the JSON.
```

Pilot results in Section 7 are from the no-scratchpad baseline (A.1). The v4 evaluation runs both A.1 and A.3 against the same trials and reports both `Adv_D` numbers; the gap quantifies how much chain-of-thought reasoning improves detection.

## Appendix B: Response handling

### B.1 Parsing protocol

Detector responses are passed through a tolerant parser that:

1. Strips leading and trailing markdown fences (` ```json ... ``` ` or ` ``` ... ``` `).
2. Locates the first balanced `{ ... }` block, allowing the model to emit prose before or after the JSON.
3. Validates the schema with type coercion for `is_cover` (bool), `p_cover` (float, clamped to [0,1]), `reasoning` (string, truncated to 1000 characters), `source_domain_guess` (enum, mapped to `unsure` if invalid), and `inversion_proposals` (dict, defaulted to empty if not a dict).

Trials whose response cannot be parsed return abstaining defaults (`is_cover=false`, `p_cover=0.5`) with `parse_ok=false` and are excluded from rate computations.

### B.2 Inversion grading (planned)

The inversion sub-task accuracy `inv_acc` is graded as follows. For each proposed pair `(cover_term, source_guess)`:

1. Look up `cover_term` in the trial's true mapping. If not present in the mapping, the proposal is graded as 0.
2. Compare `source_guess` to the true source term. Exact match scores 1.
3. If exact match fails, check a per-domain synonym dictionary (e.g., for OT/ICS: `{"valve": ["actuator", "control valve"], "pressure": ["pressure reading", "psi"]}`). Synonym match scores 1.
4. Otherwise score 0.

`inv_acc` for the trial is the mean over proposed pairs.

## Appendix C: Sample trial outputs

### C.1 Cover trial (cover of political SITREP)

Input: 267-word goldfish-care cover document generated by FALSECOLORS Method 4 with `mistral:7b-instruct`, topic = "pet goldfish care report", source = a political situation report about parliamentary election results.

Detector D = Gemini 2.5 Flash. Response (truncated):

```json
{
  "is_cover": true,
  "p_cover": 1.0,
  "reasoning": "The document consistently uses vocabulary related to
   goldfish and their tank environment while describing events and
   relationships that directly map to a political election and its
   aftermath...",
  "source_domain_guess": "political",
  "inversion_proposals": {
    "schools of fish": "legislative seats",
    "feeding time": "election day",
    "feeding stations": "polling stations",
    "competitor goldfish group": "opposition party",
    "Tank Caretaker": "Head of State",
    "complete tank overhaul": "electoral reform",
    "Goldfish Embassies": "Foreign Embassies",
    "goldfish satisfaction level": "public approval rating"
  }
}
```

Scored: detection TP, classification correct (political), inversion 6 of 8 correct or near-correct.

### C.2 Native trial (v4 brewery corpus paragraph, scored as native)

Input: 122-word paragraph beginning "BJCP-style tasting notes for the barrel-aged imperial stout described a deep mahogany color..."

Detector D = Gemini 2.5 Flash. Response (truncated):

```json
{
  "is_cover": false,
  "p_cover": 0.01,
  "reasoning": "The document exhibits consistent and specific
   vocabulary, processes, and measurements directly pertaining to the
   brewing domain. Terms like 'amber ale', 'lager yeast', 'bright tank',
   'gravity', 'aromatic profile', 'hops', 'grain bill', 'malt',
   'conditioning', and 'barleywine' are all integral to beer
   production...",
  "source_domain_guess": "none_of_above",
  "inversion_proposals": {}
}
```

Scored: detection TN.

### C.3 Native trial flagged as cover (false positive)

Input: 187-word paragraph from `brewery_v4.txt` beginning "The bottling line is due for its quarterly maintenance as well..." (full text in main body Section 7.3). Contains zero industrial-control vocabulary but describes equipment maintenance with measurements, trends, and replacement schedules.

Detector D = Gemini 2.5 Flash. Response (truncated):

```json
{
  "is_cover": true,
  "p_cover": 0.95,
  "reasoning": "The document uses brewing terminology, but the
   underlying structure and concepts, such as modification tracking,
   validation, and threshold bands, suggest a more complex system
   typically found in industrial control systems...",
  "source_domain_guess": "ot_ics",
  "inversion_proposals": {}
}
```

Detector D' = Groq Llama 3.3 70B on the same input: `is_cover=false`, `p_cover=0.05`. Cross-detector disagreement.

Scored: FP against Gemini, TN against Groq. The detector pair disagrees, which is informative: structural-pattern flagging is detector-specific. The v4 paper will report `Adv_D` separately for each pinned detector and call out cells where cross-detector variance exceeds a threshold.

---

## References

This document inherits the reference list of the main Eris FALSECOLORS paper. Additional LACH-specific references:

- Mitchell, E., Lee, Y., Khazatsky, A., Manning, C., Finn, C. (2023). DetectGPT: Zero-shot machine-generated text detection using probability curvature. ICML 2023.
- Kirchenbauer, J., et al. (2023). A watermark for large language models. ICML 2023.
- Bai, Y., et al. (2022). Constitutional AI: Harmlessness from AI feedback. Anthropic.
- Liang, P., et al. (2023). HELM: Holistic evaluation of language models. TMLR.

---

**License:** This companion paper is released under the same terms as the main Eris FALSECOLORS paper. Methods are published as prior art. Reference implementation is AGPL-3.0 with commercial carve-out.

**Copyright:** (C) 2026 River Caudle.

---

*The v3 paper formalized what an adversary cannot do in principle. This document measures what an adversary actually does in practice. Both numbers matter; they are not the same.*
