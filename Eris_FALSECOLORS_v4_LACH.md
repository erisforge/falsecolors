# Eris FALSECOLORS v4
## LACH: LLM-Adversarial Cover Hardening and the Detector-Bounded Distinguishing Game

**Working Paper, Companion to Eris_FALSECOLORS_v3.md**
**Author: River Caudle**
**Revision: 0.1**
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

**Theorem 4.2.3 (Detector advantage is bounded by information-theoretic advantage).** For any computable detector D operating in polynomial time:

    Adv_D <= Adv_information-theoretic <= TV( P(C_doc) || P(N) )

where the first inequality follows because D is a specific computable strategy and the information-theoretic adversary may use any strategy, and the second inequality is Theorem 2.17.3 of the main paper.

**Corollary 4.2.4 (LACH does not contradict v3 results).** A high Caudle Distance does not imply high Adv_D, and a low Caudle Distance does not imply low Adv_D. Caudle Distance measures statistical distinguishability through token-adjacency cosine-similarity divergence; Adv_D measures the realized detection capability of a specific LLM detector. These are related but distinct quantities. The v3 paper's Caudle Distance numbers remain valid; LACH adds an orthogonal measurement.

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
- **Confidence elicitation.** The model is asked for `p_cover` directly. LLMs are known to be miscalibrated in self-reported probabilities. A self-consistency variant that runs the detector five times at temperature greater than zero and uses the fraction-true as a calibrated probability is identified as future work.
- **No reasoning chain shown to the model.** The prompt does not request chain-of-thought reasoning before the JSON output, since some models would emit reasoning that breaks the parser. The `reasoning` field captures the model's stated cues.

### 4.2 Adversary model selection

The v4 evaluation pins three detectors and reports `Adv_D` against each:

- **Primary**: Google Gemini 2.5 Pro (frontier-grade, native JSON response mode, generous free tier for development). Pinned at version `gemini-2.5-pro` as of May 2026.
- **Secondary**: Anthropic Claude Opus 4.7 (frontier-grade, contemporary). Pinned at version `claude-opus-4-7` as of May 2026.
- **Cross-check**: Groq-hosted Meta Llama 3.3 70B. Mid-tier (not frontier) but useful for prompt iteration and as a distributional cross-check.

Cross-detector agreement above approximately 0.85 across the v4 evaluation is the methodology validity signal: if the three detectors disagree wildly, `Adv_D` is detector-specific and the v4 paper must recommend a tier rather than a number.

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

## 7. Empirical Findings to Date

(Pilot data; full v4 evaluation pending.)

### 7.1 Single-trial detection ceilings

The goldfish cover demonstration (a political situation report transformed into a pet goldfish care report via Method 4 with `mistral:7b-instruct`) was scored:

- Gemini 2.5 Flash: `is_cover=true`, `p_cover=1.0`, `source_domain_guess=political`. Inversion proposals were 6 of 8 correct or near-correct.
- Groq Llama 3.3 70B: `is_cover=true`, `p_cover=0.9`, `source_domain_guess=political`. Inversion proposals omitted but classification correct.

Single-trial detection on a representative cover is at or near ceiling for both detectors. This is not a statistically meaningful sample but indicates the detection task is feasible for frontier-class models.

### 7.2 Native baseline on the v3 corpus

Two paragraphs from the v3 brewery corpus, sampled at random, scored:

- Gemini 2.5 Flash: both `is_cover=true`, `p_cover=0.95`, `source_domain_guess=ot_ics`.
- Groq Llama 3.3 70B: both `is_cover=true`, `p_cover=0.80`, `source_domain_guess=ot_ics`.

This produced the v3 corpus problem documented in Section 4.3.

### 7.3 Native baseline on the v4 corpus

Ten paragraphs sampled at random from `brewery_v4.txt` (12,391 words) with seed 42:

- Gemini 2.5 Flash: mean p_cover = 0.209, max p_cover = 0.95, FP count = 2 of 10.
- Groq Llama 3.3 70B: mean p_cover = 0.060, max p_cover = 0.10, FP count = 0 of 10.

Cross-detector agreement: 8 of 10 paragraphs receive consistent verdicts. Two flagged paragraphs against Gemini contained zero industrial-control vocabulary; the detector flagged them on structural grounds (brewing equipment maintenance and quality-control reports are structurally similar to ICS process reports).

Interpretation: the v4 corpus is acceptable for evaluation; Gemini's residual approximately 20 percent FPR on technical brewing content is part of the adversary, not part of the corpus, and should be reported alongside TPR as the empirical baseline.

### 7.4 Implications for v3 results

The v3 paper's reported Caudle Distance of approximately 1.0 to 1.3 nats was measured against the v3 corpus, which is now known to be process-control-flavored. SCD against `brewery_v4.txt` will produce different numbers. The v4 paper should report SCD against both corpora and treat the v4 number as the operationally meaningful one. The v3 number remains valid as a measurement against its own reference corpus; it is not invalidated, only reframed.

## 8. Limitations and Open Questions

1. **Adversary model versioning.** `Adv_D` is detector-relative. As frontier models advance, today's `Adv_D = 0.4` may become `Adv_D = 0.7` against the same prompt. The v4 paper pins specific model versions; users should re-evaluate against contemporary detectors before deployment.

2. **Confidence calibration.** Self-reported `p_cover` from an LLM is known to be miscalibrated. Self-consistency sampling (multiple runs at temperature > 0, fraction-true as calibrated probability) is the standard correction; not yet implemented.

3. **Inversion grading.** The inversion sub-task currently grades correctness via exact match plus a small synonym dictionary (Appendix B.2). A more rigorous grading function based on cross-domain semantic similarity is future work.

4. **Negative-set scope.** The v4 evaluation uses brewery as the only cover domain. Garden, novel, and other Method 4 cover domains lack reference corpora. Each cover domain in production use needs its own native corpus.

5. **Cost ceiling.** A full v4 LACH evaluation makes approximately 720 frontier-detector calls. At Gemini 2.5 Pro pricing this is roughly 5 to 15 USD per pass; at Claude Opus 4.7 pricing roughly 30 to 60 USD per pass. Manageable for a single evaluation but limits how often the eval can be re-run during prompt iteration.

6. **Phase 2 contamination.** If Phase 2 builds a rewrite loop using detector D, evaluating the hardened cover against the same D is in-distribution and overstates effectiveness. A separate held-out detector D' is required for honest Phase 2 evaluation, doubling API cost.

7. **Cover-vs-source confusion in the detector.** In one pilot trial the detector correctly identified the original political SITREP as native political content (`is_cover=false`). However, if the detector were given a sanitized political document that retains political vocabulary but masks specific identifiers, it would still classify as native political. The Distinguishing Game assumes the adversary's task is "is this a cover?" not "is this redacted?" Sanitize-mode outputs (Section 10 of main paper) are out of scope for LACH.

8. **Compositional leakage.** A single document's `Adv_D` does not bound an adversary's advantage when given many documents from the same user. Composition is the scope of the Caudle Accountant (forthcoming).

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
