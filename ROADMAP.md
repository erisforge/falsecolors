# Eris FALSECOLORS v4 Research Roadmap

## Context

v3 shipped a working two-step LLM prompt that lifted recovery to 0.92 median across the 6-model evaluation cohort, formalized two metrics in the paper (Caudle Distance / Native-Text Drift, Rinaldi Distance / Self-Report Gap), and reframed the project around its actual use case: anyone who needs to openly carry or publish text with a hidden message.

The v4 question opened when considering whether to build a separate tool for "obfuscate so a cloud LLM can analyze without seeing identities." The trivial version (NER + placeholder substitution + reverse-substitute) is what Microsoft Presidio, Skyflow LLM Privacy Vault, AWS Comprehend, and Google DLP already do. Reinventing PII redaction is not a research contribution. The question became: what is genuinely novel in the cloud-LLM-meets-sensitive-content space?

Ten research directions were surveyed via parallel expert consultation. This document captures all ten, ranks them by novelty, and recommends the v4 build path.

---

## Survey: 10 directions

### 1. Cover-Mapping Differential Privacy (CM-DP)

DP accountant for FALSECOLORS-style mapping randomization under repeated cloud-LLM queries. Treats the bijective source-to-cover mapping as the noisy mechanism. Per-query mapping sampled from a distribution over cover domains and intra-domain permutations, accounted via Rényi DP across K queries.

Novelty against Yue et al. (2023, DP synthetic text), Mattern et al. (2022, DP rewriting limits), Igamberdiev and Habernal (DP-BART, 2023): all inject noise into logits, embeddings, or training gradients. CM-DP shifts the noise mechanism from "perturb generation" to "randomize the bijection." None of the rewriting-DP line models the adversary-side aggregation problem.

Defends against an honest-but-curious provider doing offline schema-recovery from logged covers. Does not defend against side channels, key compromise, or the answer channel itself.

Killer failure: source content is correlated across a user's queries (same pentest, same SITREP), so the adversary's posterior concentrates even with fresh mappings. May force ε to grow linearly in K rather than sub-linearly.

Buildable in 6 weeks: extend FALSECOLORS to sample mappings from a parameterized family, implement Mironov's Rényi accountant (~200 lines), build empirical adversary, measure ε vs source-token recovery.

### 2. Commit-and-Prove Cover Analysis (CPCA)

Merkle commitment over (cover_text, transformation_nonce, query_template) before sending to cloud LLM. Provider returns answer plus a Fiat-Shamir derived attestation transcript binding the answer to the committed input. User locally verifies the LLM did not silently substitute or correlate across the session.

Novelty against zkML (EZKL, Modulus, Giza, Daniel Kang), FHE-NN (CryptoNets, Zama Concrete-ML), MPC inference (CrypTen, Cheetah, MPC-Former): all hide the input from the server. CPCA inverts the trust direction. The user verifies the provider, accepting that the provider sees plaintext (cover) tokens. What gets proved is answer-to-input binding and session non-correlation, which no current protocol delivers for commercial LLMs.

Defends against silent answer substitution, cross-query correlation by the provider, and man-in-the-middle answer swapping. Does not defend against an honest provider exfiltrating the cover text or against semantic leakage from the cover itself.

Killer failure: the logprob-attestation channel depends on providers exposing logprobs at chosen positions. OpenAI restricts; Anthropic does not expose. Falls back to weaker semantic-consistency checks via paraphrase challenges.

Buildable in 6 weeks: Merkle + Fiat-Shamir in pure stdlib, logprob verifier against OpenAI plus Ollama baseline, paraphrase-challenge fallback, evaluation on synthetic substitution attacks.

### 3. FPE-Anchored Cover Documents (FACD)

Apply FF1 format-preserving encryption to the high-entropy numeric and identifier tokens that resist cover-domain shifting. Re-tokenize the FF1 ciphertext into the cover domain's value space (a brewery temperature, a fermentation timestamp). FALSECOLORS handles bulk semantic transformation around it.

Novelty against Bellare-Rogaway-Spies FF1 (NIST SP 800-38G) and Skyflow vault-based FPE: their ciphertext occupies the same field as plaintext (an IP-address ciphertext is still recognizably an IP). FACD re-tokenizes ciphertext into native cover-domain content, inheriting FALSECOLORS deniability.

Defends against adversaries with cloud LLM logs who can brute-force low-entropy fields exposed by pure cover-shift (CVE-2024-3094 has ~30 bits of entropy in public CVE space). Does not defend against analytical loss on the FPE'd values themselves (they become semantic dead-ends inside the cover).

Killer tradeoff: cloud LLM analysis cannot reason about the FPE'd values. Position-leak if the adversary knows which tokens are anchored.

Buildable in 6 weeks: FF1 implementation (~300 lines on top of AES), token classifier (regex + entropy heuristic), integration as a layer between identifier encoding and domain shift.

### 4. Threshold Semantic Sharding (TSS)

Decompose a sensitive analytical query into n cover-domain shards, each routed to a distinct LLM provider. Any k-1 providers' logs are individually indistinguishable from benign domain queries. Local client reconstructs the answer from any k responses via Lagrange-style interpolation over a constrained answer-space embedding.

Novelty against Shamir secret sharing (1979), split learning (Vepakomma 2018), confidential FL: all assume opaque payloads, model-splitting, or trusted hardware. TSS is the first framework treating commercial LLM providers as semi-honest oracles whose useful inferential work is preserved per-shard while threshold-secrecy is preserved across shards.

Defends against any k-1 colluding providers and simultaneous subpoena of all n providers' logs. Does not defend against global passive adversaries doing fine-grained timing correlation, k-or-more colluding providers, cover-domain fingerprinting, or the client endpoint.

Killer assumption: non-collusion is doing all the work. If Anthropic, OpenAI, and Google share a "suspicious-query" feed, the scheme degrades to single-provider. Lagrange reconstruction over LLM prose outputs is fragile and needs a constrained answer schema.

Buildable in 6 weeks for a constrained query class (numeric-comparison and ranking only). Generalizing the answer-space embedding is the publishable research contribution.

### 5. k-Cover Anonymity via Adversarial Cover Construction (k-CAC)

Generate each cover document so it is simultaneously a valid cover for at least k distinct source documents drawn from a published decoy corpus. Provider's posterior over the true source is flat across k candidates rather than concentrated.

Novelty against Sweeney's k-anonymity (2002), Machanavajjhala l-diversity (2007), Li t-closeness (2007), Dwork DP (2006): all designed for tabular data with fixed schema. None apply to free-text documents whose "schema" is the relational graph the document induces. FALSECOLORS already gives semantic entropy as a counting measure over R-equivalent documents; what is missing is the adversarial dual: not "how many covers can D produce" but "how many D's could have produced this cover."

Defends against a provider trying to attribute a single cover to a specific source from a known candidate population. Does not defend against repeated queries from the same account unless the joint-distribution variant is used.

Killer failure: "k mathematically valid sources" vs "k plausible sources" gap. An adversary with a prior over the decoy corpus collapses the anonymity set. The CSP for shared-cover construction may be infeasible for high-entropy D when k is large.

Buildable in 6 weeks: build a 500-document decoy corpus from public ICS-CERT advisories, implement shared-cover CSP solver on top of FALSECOLORS bijectivity machinery, measure achieved k vs semantic-fidelity tradeoff.

### 6. COLORWASH (Mix relay for FALSECOLORS queries)

Single-host proxy that pools FALSECOLORS-encoded queries from many users into fixed-size, fixed-cadence batches submitted under a shared cloud-LLM account. Provider observes a stream of indistinguishable consulting traffic instead of N separable users.

Novelty against Chaum mixes (1981) and Tor (Dingledine 2004): both assume the content is opaque to relay and destination. Cloud LLMs invert that assumption (the destination must read the plaintext to do useful work). FALSECOLORS makes the plaintext semantically opaque to the provider while leaving it functionally usable. COLORWASH composes the two so the anonymity set is over query semantics, not just IP and timing.

Defends against per-user topical and stylistic profiling, subpoena-mapping a query history to a person. Does not defend against a malicious relay operator (trust shifts to the relay), global passive adversaries doing tight timing correlation, or response-content side channels.

Killer assumption: operator trust. Mitigations: stateless relay design, public batch logs (Certificate Transparency style), eventual federation across independent relays. Stylometric leakage in the cover domain re-identifies users across batches and needs a cover-domain rotation policy.

Buildable in 6 weeks: FastAPI relay, batch scheduler, per-query token routing, Ollama or OpenAI backend adapter reusing existing FALSECOLORS LLM path, threat-model evaluation harness.

### 7. Rotated-Embedding Inference (REI)

Locally encode the document into the cloud model's embedding space, apply a learned rotation R that maps the source-domain cluster onto a cover-domain cluster, run inference on rotated embeddings, apply R^-1 to output embeddings before decoding locally. Makes Section 2.3's geometric story the actual wire format.

Novelty against cross-lingual embedding alignment (Mikolov 2013, Smith 2017 MUSE, Conneau adversarial Procrustes): all align two static embedding spaces to translate between them. REI operates on contextual transformer embeddings, uses the rotation as a privacy primitive rather than translation, and runs inference in the rotated space rather than just lexicon induction.

Defends against honest-but-curious providers logging prompts, routine prompt-retention pipelines, subpoena of stored prompts. Does not defend against a provider running the decoder side themselves (they own the model weights). This is plausible deniability and friction, not cryptographic confidentiality.

Killer feasibility issue: most commercial APIs (OpenAI, Anthropic, Google) accept tokens only. Feasibility narrows to self-hosted vLLM or TGI endpoints, which reduces the "cloud" threat model to "rented GPU." Second: rotations preserve L2 geometry but transformer attention is not rotation-equivariant past layer 0, so R applied at the input embedding will be partially unrotated by learned weights.

Buildable in 6 weeks as a feasibility study. The negative result (attention destroys the rotation) is itself publishable.

### 8. LLM-Adversarial Cover Hardening (LACH)

Replace the static Caudle Distance bound with an empirically measured, LLM-bounded one. Instrument FALSECOLORS with a frontier-LLM detector inside both the evaluation harness and the encode-time loop. Covers are optimized against the actual adversary they will face, not against a fixed reference corpus.

Novelty against DetectGPT, GPTZero, Mitchell et al.'s curvature-based detectors: all ask "was this written by an LLM?" Kirchenbauer-style watermarking asks "did our LLM write this?" Neither asks the FALSECOLORS-relevant question: "is this an LLM-generated cover for a structurally-different source domain?" Adversarial NLP (TextFooler, BERT-Attack) operates token-level on a fixed semantic target; LACH optimizes at the cover-generation step against a generative adversary doing structural-domain inference.

Defends against an adversary running a frontier LLM prompted to flag the document as a probable cover, guess the source domain, propose a partial inverse mapping. Does not defend against passphrase compromise, side-channel access to the source, or future detector LLMs strictly stronger than the one in the loop.

Killer risks: detector-overfitting (covers robust to D may fail against D'); rewrite loop degrades recovery below the v3 0.92 floor; rewrite signal may itself leak information if the detector's chain-of-thought is logged.

Buildable in 6 weeks. The eval harness is the entire first three weeks and is independently valuable as a paper artifact even if the defense fails.

### 9. Per-Document Generative Fictional Cover Worlds (Apocrypha Layer)

Replace the fixed real cover domain with a freshly synthesized fictional world per document. Ontology, terminology, and "regulations" are generated to be structurally isomorphic to the source. An LLM-attacker has no real-world prior against which to test the cover for plausibility.

Novelty against Park et al. Generative Agents (2023), Andreas-style world-modeling, Shaker et al. PCG, Ziegler et al. and Meteor steganography: none treats world-generation itself as the security primitive. FALSECOLORS today maps to real domains (brewery, garden), which is exactly where an LLM-adversary's prior is sharpest. Apocrypha removes that prior by making the cover domain not exist anywhere in the attacker's training corpus.

Defends against an LLM-equipped reader checking domain plausibility, internal procedural consistency against real-world process knowledge, named-entity verifiability. Does not defend against traffic-analysis or metadata leaks, structural fingerprints of the source document that survive translation, or a custodian who already knows the source genre.

Killer risks: structural isomorphism may still leak (if source has 7 numbered controls, so does cover); LLMs drift toward training-distribution tropes (Tolkien, SCP, D&D) so "fictional" worlds become a recognizable genre; numeric values are hard to fictionalize without breaking arithmetic relations.

Buildable in 6 weeks: skeleton extractor, World Spec schema (~1-3 KB JSON for a 500-word source), generator and bijection compiler bolted onto existing LLM backend, key-embedding extension, evaluation via held-out LLM-judge classification.

### 10. Caudle Accountant (compositional leakage)

Treat each FALSECOLORS query as a one-shot mechanism emitting cover c from source s under mapping M. Track Rényi divergence between joint distributions of K covers under two neighboring source-streams. Cover-document user gets a hard, auditable budget that triggers mapping rotation before the joint stream becomes distinguishable.

Novelty against Abadi et al. (2016 moments accountant), Mironov (2017 Rényi DP), Dwork-Rothblum-Vadhan advanced composition: all assume per-query mechanism injects calibrated stochastic noise. FALSECOLORS injects no noise; given M the mechanism is deterministic. Existing multi-document steganalysis (Ker's pooled steganalysis, 2006-2011) measures cumulative detectability empirically but provides no composition theorem and no budget. The Caudle Accountant gives the first formal composition framework for deterministic-given-key bijective semantic transformations. Surpasses Section 2.16.6 (which only chains transformations of one document) by handling the orthogonal axis of K independent documents under shared key.

Defends against an adversary collecting K covers from the same user and trying to link them to a common source-domain user, or distinguish "this user's K covers" from "K covers from a generic cover-domain user." Does not defend against side-channel access to source documents, semantic content leakage detectable by Caudle Distance within a single cover, or adaptive prompt-injection in chat workflows.

Killer issue: deterministic mechanisms can have infinite Rényi divergence at α = ∞ if any cover token uniquely identifies M, collapsing the accountant to "rotate after one query." Requires a δ smoothing term that ignores rare-token events, but choosing δ is a research problem.

Buildable in 6 weeks: formalize neighboring-stream definition, prove basic linear composition theorem, implement accountant logging per-query Rényi estimates, implement Ker-style pooled steganalysis as empirical calibrator, build rotation policy.

---

## Novelty ranking

| Rank | Direction | Novelty against literature | Risk | Notes |
|---|---|---|---|---|
| 1 | LACH | LLM-as-adversary against semantic domain shift is unexplored | Low | Builds on existing v3 eval infrastructure |
| 2 | Apocrypha | World-generation as security primitive has no precedent | High | Most striking; execution risk on world coherence |
| 3 | Caudle Accountant | No composition theorem exists for deterministic bijective mechanisms | Medium | Fills the obvious paper gap |
| 4 | REI | Negative result publishable; positive result shifts the field | High | Commercial API support is the gating constraint |
| 5 | k-CAC | Adapts k-anonymity to relational graphs | High | CSP feasibility uncertain |
| 6 | CPCA | Inverts zkML trust direction | Low | Solves substitution detection, not secrecy |
| 7 | CM-DP | Mapping-as-mechanism framing is new but DP-text is crowded | Low | Caudle Accountant is the better framing |
| 8 | FACD | FPE composition is the novelty; FPE itself is well-understood | Low | Useful narrow tool |
| 9 | TSS | Multi-provider sharding is being commercialized | Low | Useful but Skyflow circling |
| 10 | COLORWASH | Mixnets are well-trod; FALSECOLORS-aware twist is the only novelty | Low | Useful service, not a research contribution |

---

## Recommended v4 arc

The top three (LACH, Apocrypha, Caudle Accountant) compose into a coherent research thesis worth ~5 months of one-engineer time.

### Step 1: LACH (~6 weeks)

The measurement instrument. Without a frontier-LLM-adversary baseline, no claim about Apocrypha's effectiveness or the Caudle Accountant's calibration is meaningful. The eval harness already exists from v3.

Deliverables:
1. Detector-Bounded Distinguishing Game formalized in paper (extension of Section 2.17). Replace TV-distance-to-native with `Adv_D` for a named detector.
2. Eval harness extension: feed v3 cover corpus to a frontier LLM adversary, score three-way detection, classification, and partial-inversion accuracy.
3. Adv_D as a first-class metric reported alongside Native-Text Drift and Round-Trip Loss in all future evals.
4. Optional defense layer: encode-time rewrite loop using the detector's reasoning as a constraint signal.

Why first: the measurement upgrade is independently valuable even if the defense fails. Every subsequent v4 result becomes citable against a real adversary baseline.

### Step 2: Apocrypha (~6 weeks)

Now you can test whether removing the LLM-adversary's domain prior actually moves Adv_D. Hypothesis: real-domain covers (brewery) score worse on Adv_D than fictional-world covers because the adversary has no anchor for the fictional world. If true, Apocrypha is the headline finding. If false, structural fingerprinting is the dominant attack and you redirect.

Deliverables:
1. Skeleton extractor that builds a relational graph from arbitrary source.
2. World Spec generator producing novel proper nouns, governing bodies, process taxonomies, and constraint physics, all isomorphic to the source skeleton.
3. Lexicon compiler enforcing FALSECOLORS bijectivity and longest-key-first.
4. Cover generator using World Spec as system context.
5. Key-embedding extension carrying both lexicon and World Spec.
6. Comparative eval: real-domain covers vs Apocrypha covers under the LACH detector.

Why second: depends on the LACH measurement. Cannot evaluate without it.

### Step 3: Caudle Accountant (~8 weeks)

Now formalize the multi-query story. Empirical work from LACH and Apocrypha gives the calibration data; theory work fills the obvious Section 2.16.6 gap.

Deliverables:
1. Formal definition of neighboring source-streams and per-query leakage L_i.
2. Composition theorem: linear baseline plus a window-decorrelated tighter bound.
3. Accountant module logging per-query Rényi divergence estimates against a held-out cover corpus.
4. Rotation policy integrated with existing key-embedding layer.
5. Empirical AUC-vs-budget curve calibrated against pooled steganalysis classifiers (Ker-style).
6. Open-problems section in the paper for adaptive composition under chat workflows.

Why third: depends on having an LLM-adversary in the loop (LACH) and on having multiple cover types to compose over (real-domain plus Apocrypha).

### Aggregate output

A v4 paper with three additions:
- New Section 2.17 reframing the Distinguishing Game as Detector-Bounded.
- New Section 7.10 introducing Apocrypha as a fifth method with its own eval.
- New Section 2.18 (formerly Shannon) bumped to 2.19; new Section 2.18 introduces the Caudle Accountant with a basic composition theorem.

---

## What to skip and why

**TSS, COLORWASH, FACD, CPCA**: systems engineering. Useful, possibly worth shipping as side projects, not research that distinguishes FALSECOLORS as a body of work. Two of them (TSS, COLORWASH) require coordinating multiple providers or users and are not single-author PoCs.

**REI**: too feasibility-uncertain for a 6-week commitment. Worth a 2-week feasibility study after LACH gives you the eval harness, then either pursue or kill.

**k-CAC**: real CSP-feasibility cliff. Could become an Apocrypha sub-problem if Apocrypha's K-distinct-worlds analysis succeeds (a fictional world is a candidate decoy source by construction).

**CM-DP**: overlaps with crowded DP-text-rewriting literature. Caudle Accountant is the better framing for the same intuition because it does not pretend to be DP when the mechanism is deterministic.

---

## Build order (5 months total, one engineer)

```
Weeks 1-6:    LACH (eval harness + detector + optional rewrite loop)
Weeks 7-12:   Apocrypha (skeleton + World Spec + cover gen + comparative eval)
Weeks 13-20:  Caudle Accountant (theory + accountant + rotation + empirical calibration)
Weeks 21-22:  Paper integration: write up new sections, update CHANGES.md, tag v4 release
```

Optional 2-week REI feasibility study can slot in after week 6 or after week 12 depending on momentum.

---

## Open questions and risks

1. **The whole v4 arc presumes a single sophisticated adversary class** (frontier LLM running detection). If the real-world adversaries are still passive observers (customs officers, litigation reviewers), the v3 results already cover the operationally relevant case and v4 is academic.
2. **Apocrypha may fail.** The hypothesis that removing the domain prior helps the cover document needs empirical validation. If LLMs can detect "this is a synthesized fictional world" as easily as they detect "this is a brewery cover," the whole direction collapses.
3. **The Caudle Accountant may not be tight.** Deterministic-mechanism Rényi composition could yield bounds so loose they are operationally useless (rotate after every query). The δ-smoothing path is uncharted.
4. **LACH's encode-time rewrite loop may degrade Round-Trip Loss below 0.92.** The v3 baseline could be the ceiling for any defense that requires post-hoc rewriting.
5. **Method 4's existing Self-Report Gap (Rinaldi Distance) bounds Apocrypha's quality.** If the LLM cannot faithfully maintain a fictional world while preserving relational structure, Apocrypha inherits Method 4's failure modes plus new ones from world-generation.
6. **Publication venue is unclear.** USENIX Security, IEEE S&P, PoPETs, NDSS are obvious targets but the work crosses ML, cryptography, and steganalysis; reviewers from any one community may underweight the others.

---

## Status

Drafted as a planning artifact. No code or paper changes yet. Pending decision on whether to commit to the v4 arc.
