# Eris FALSECOLORS

**Noncryptographic Semantic Transformation for Deniable Document Protection**

*The best protection doesn't look like protection.*

---

FALSECOLORS is for anyone who needs to openly carry or publish text with a hidden message. Encryption hides content but signals that something is being hidden. FALSECOLORS produces a cover document that reads as legitimate text in an unrelated domain, recoverable to the original only with a passphrase.

## The Problem

Encryption protects data but advertises its value. A password-protected archive, an encrypted disk image, or a PGP file all signal to an adversary that something worth protecting is inside. In litigation discovery, device seizure, cloud storage compromise, or nation-state surveillance, the presence of encryption attracts exactly the attention it was meant to prevent.

In OT/ICS security, penetration test findings describe exactly how to compromise physical safety systems. A finding that documents unauthenticated write access to safety interlock registers at a chemical facility is, if intercepted, an attack playbook. The consequence isn't data breach. It's potential physical harm.

## The Solution

FALSECOLORS transforms sensitive documents into innocuous documents in unrelated domains. A pentest finding about a chemical reactor becomes a craft brewery quality audit. The logical structure is preserved. The vocabulary shifts completely. The cover document reads as a legitimate document in the cover domain.

There is no ciphertext. There is no encrypted container. There is no signal that anything has been done. An adversary who obtains the cover document has no reason to investigate further because there is nothing that appears to require investigation.

Recovery requires a passphrase. Without it, the cover document stands alone forever as a brewery audit.

## Quick Start

```bash
# Run the demo (zero dependencies, just Python 3.8+)
python falsecolors.py demo
```

```bash
# Encrypt a document
python falsecolors.py encrypt \
  --source finding.txt \
  --passphrase "my secret phrase" \
  --topic brewery \
  --output cover.txt

# Decrypt
python falsecolors.py decrypt \
  --source cover.txt \
  --passphrase "my secret phrase" \
  --output recovered.txt
```

```bash
# Any topic (requires local LLM via Ollama)
python falsecolors.py encrypt \
  --source finding.txt \
  --passphrase "my secret phrase" \
  --topic "bumblebee colony management" \
  --backend llm \
  --output cover.txt
```

```bash
# Interactive proxy: you speak OT, the cloud LLM sees brewery
python falsecolors.py proxy \
  --passphrase "my secret phrase" \
  --api anthropic
```

```bash
# Sanitize for LLM analysis: strip identities, preserve math
python falsecolors.py sanitize \
  --source finding.txt \
  --passphrase "my secret phrase" \
  --output sanitized.txt

# The LLM sees ASSET_001, PARAM_003, SYS_007. It can reason
# about vulnerability patterns. It can't identify the system.

# Recover original
python falsecolors.py desanitize \
  --source sanitized.txt \
  --passphrase "my secret phrase" \
  --output recovered.txt
```

## What It Does

**Before (sensitive OT pentest finding):**

> During the assessment of the client's ethylene oxide reactor control loop, the assessor identified that the Safety Instrumented System protecting the reactor overpressure condition accepts unauthenticated Modbus TCP writes to holding registers 40001 through 40016.

**After (brewery quality audit):**

> During the assessment of the client's imperial stout fermenter control loop, the auditor identified that the Quality Control System protecting the fermenter over-carbonation condition accepts unauthenticated Golf writes to recipe parameters foxtrot through echo.

The source tells an attacker how to bypass safety systems at a chemical plant. The cover tells someone a brewery has a recipe database access control issue. Same logical structure. Different domain. Perfect recovery with the passphrase.

## Threat Model

FALSECOLORS is deniable against **time-constrained pattern-matching adversaries**: customs officers and litigation reviewers under deadline, automated content classifiers running keyword filters, cloud providers performing routine log triage, and rubberhose interrogations where the artifact itself is the only available evidence. Against these adversary classes the system is deployable today.

FALSECOLORS is **not** deniable against adversaries who invoke a frontier-class LLM as a detection tool. Empirical evaluation (`Eris_FALSECOLORS_v4_LACH.md`) measures the realized adversary advantage and finds that current Method 4 covers are reliably identified as transformed source content under source-domain identification. If your threat model includes a state-level adversary or a workflow that auto-runs Claude / GPT / Gemini against intercepted documents, do not rely on Method 4 covers for deniability against that adversary; use sanitize mode for confidentiality instead, or wait for a v4+ implementation that specifically defends against LLM-mediated detection.

For the cloud-LLM-analysis use case (you want a frontier LLM to reason about your document without learning its identity), use `sanitize` rather than `encrypt`. Sanitize mode replaces identifying tokens with opaque labels and shifts numeric values, then the cloud LLM analyzes the abstracted structure and returns recommendations the user inverse-substitutes locally. This works against any adversary class because the document is visibly processed; it provides confidentiality, not deniability.

## How It Works

A document's meaning has two parts: its relational structure (what causes what, what measures what, what exceeds what) and its vocabulary (the domain-specific terms). FALSECOLORS changes the vocabulary while preserving the structure. The result is a new document that makes the same argument about a completely different subject.

Three layers compose in sequence:

1. **Identifier Encoding** strips technical identifiers (IP addresses, register numbers, protocol names, CVEs, measurement values) and replaces them with innocuous placeholders. Sensitive parameters are separated from operational context.

2. **Domain Shift** transforms the remaining vocabulary from the source domain to the cover domain using a structure-preserving mapping.

3. **Key Embedding** encrypts the combined mapping with the passphrase and embeds it as a compressed base64 footer in the cover document. The recipient needs only the file and the passphrase.

## Features

**Three commands.** `encrypt`, `decrypt`, `proxy`. That's the interface.

**Zero dependencies.** Python 3.8+ standard library only for core functionality.

**Offline operation.** Built-in static mapping tables work with no network, no API, no compute beyond string matching.

**Any cover topic.** With the `--backend llm` flag and a local model (Ollama), encrypt into any topic: bumblebees, 1800s Ethiopian fashion, competitive dog grooming, whatever.

**LLM proxy mode.** Interactive chat where you speak in your native domain (OT/ICS security) and the cloud LLM (Anthropic, OpenAI, or local) sees only the cover domain (brewery operations). Responses are automatically decoded back to your domain.

**Sanitize mode.** Strip all domain-specific identities while preserving mathematical relationships. Every token becomes an opaque label (ASSET_001, PARAM_003, SYS_007). Numeric values shift by a constant derived from hash(document + timestamp salt). The LLM can reason about vulnerability patterns, detection gaps, and remediation approaches without knowing what physical system it's analyzing.

**Self-contained output.** The encrypted mapping is embedded in the cover document itself. No separate key files to manage. The recipient needs only the file and the passphrase.

**Perfect recovery.** Round-trip is exact. Wrong passphrase is rejected, not silently garbled.

## Local-Model Backend Performance

The static `encrypt` / `decrypt` path is deterministic and always works. Round-trip recovery is exact. The static path is the recommended one for high-stakes use.

The `--backend llm` path uses a local LLM via Ollama for arbitrary cover topics. Recovery quality depends on the model. Three rounds of formal evaluation across six 1.7B-8B models, three sensitive OT/ICS test documents, and 180 trials per round (n=10 per model per doc) are documented in [`evaluation/RESULTS.md`](evaluation/RESULTS.md). Harness, raw per-trial data, and reference corpus are all in `evaluation/` for reproducibility.

Headline (v3, two-step prompt, default since `LLM_TWO_STEP = True`):

| Use case | Recommended model | Median recovery | P(rec ≥ 0.95) | P(rec < 0.30) |
|---|---|---|---|---|
| Highest peak quality | **`mistral:7b-instruct`** | 0.92 | 0.43 | 0.00 |
| Smallest viable model | **`qwen3:1.7b`** | 0.92 | 0.40 | 0.00 |
| Highest mapping fidelity | **`gemma3:4b`** | 0.87 | 0.17 | 0.00 |
| Largest in cohort | `llama3.1:8b` | 0.91 | 0.07 | 0.00 |
| Avoid for now | `phi3:mini` (median 0.55) | | | |

`P(rec < 0.30) = 0.00` across five of six models in v3, including the four production/beta-tier picks above. The catastrophic-tail failure mode that v2 documented for mistral:7b is gone; the silent hallucinated-mapping failure that v2 documented for qwen3:1.7b (mapping support 0.01) is also gone (now 0.86). The two-step prompt lifted every model in the cohort and reversed the v2 conclusion that production use required a polish step or a much larger model.

The evaluation surfaced one silent-integrity failure mode worth knowing about: a model can emit a parseable mapping JSON whose entries do not correspond to the substitutions actually made in the cover. The two-step prompt makes this rare for the four recommended models but does not eliminate it. The `verify_mapping_support` gate in `falsecolors.py` spot-checks five random `(src, tgt)` pairs against the cover and warns on stderr when fewer than 80% are supported; pass `--strict` to `encrypt` to turn the warning into a hard error. If you build automation on top of the LLM backend, leave `--strict` on.

## The Paper

`Eris_FALSECOLORS_v3.md` contains the full theoretical foundation, including:

- **The Caudle Semantic Secrecy Theorem**: extends Shannon's 1949 perfect secrecy result from symbol strings to labeled relational graphs.
- **The Caudle Distance**: a metric for measuring the statistical distinguishability of domain-shifted text from native text.
- **The Distinguishing Game**: a formal cryptographic game proving information-theoretic deniability under perfect domain isomorphism.
- Four methods (Recolor, Split, Semantic Pad, Dynamic Shift), the LLM middleware proxy architecture, and the simple interface.

## Prior Art

The methods described in the paper are published as prior art to ensure they remain freely available to the security community and to prevent future patenting by any party. Anyone is free to implement the described methods independently.

## Dependencies

| Feature | Requires |
|---------|----------|
| Core encrypt/decrypt (static) | Python 3.8+, nothing else |
| LLM backend (any topic) | Ollama + 4B+ model (gemma3:4b recommended; see `evaluation/RESULTS.md`) |
| Proxy mode (Anthropic) | ANTHROPIC_API_KEY env var |
| Proxy mode (OpenAI) | OPENAI_API_KEY env var |
| Proxy mode (local) | Ollama |
| Proxy mode (demo) | Nothing |

## License

**AGPL-3.0 with dual licensing.** See [LICENSE.md](LICENSE.md).

Free for personal, academic, research, and open-source use under AGPL-3.0 terms.

Commercial use requires a separate commercial license from the copyright holder. This includes incorporating FALSECOLORS into commercial products, offering it as part of a paid service, or deploying it in a closed-source environment without AGPL compliance.

The underlying methods (as described in the paper) are published as prior art and are not subject to the software license. Anyone may independently implement the described concepts. The AGPL-3.0 applies to this specific codebase and its derivatives.

## Author

River Caudle

ISA-99 Committee Member

---

*Eris FALSECOLORS. The ship is real. The flag is real. Only the allegiance is false.*
