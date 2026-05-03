# Changes

## Unreleased

### Added
- `sanitize` and `desanitize` subcommands. Sanitize mode strips all domain-specific identities into opaque labels (`ASSET_001`, `PARAM_003`, `SYS_007`, ...) and shifts every numeric value by a constant derived from `hash(document + timestamp_salt)`. Math, structure, and relational logic are preserved; identities are gone. Intended for LLM analysis: a model can reason about vulnerability patterns, detection gaps, and remediation against the sanitized form without knowing what physical system it sees. Round-trip is exact via the embedded passphrase-protected key. Usage: `python falsecolors.py sanitize --source f.txt --passphrase X --output s.txt`.
- `measure` subcommand: computes the Caudle Distance (SCD per Definition 2.15.2) of a cover document against a native cover-domain corpus. Pure stdlib. Builds PPMI co-occurrence vectors from the corpus, scores cosine similarity over adjacent content tokens, and returns the KL divergence between the document's TAD and the corpus's TAD with Laplace smoothing. Usage: `python falsecolors.py measure --source cover.txt --corpus brewery_native.txt`. A native document scored against its own corpus returns SCD ≈ 0; an unshifted source-domain document returns a high SCD with very few adjacent pairs scored.
- `OLLAMA_TIMEOUT` environment variable controls the Ollama request timeout for `llm_translate` (default 120s). Thinking-class local models (e.g., qwen3 thinking variants) routinely exceed 120s on a standard finding document; bump to 600 with `OLLAMA_TIMEOUT=600 python falsecolors.py encrypt ...` when using such models.

### Fixed
- IdentEncoder placeholder collision past 40 unique identifiers. The pool of 40 NATO/word names was indexed with `% len(POOL)`, so the 41st unique identifier silently reused the 1st placeholder and decoding became ambiguous. Past the first cycle, placeholders are now suffixed with the cycle number (`alpha`, ..., `nectar`, `alpha2`, ..., `nectar2`, `alpha3`, ...), preserving uniqueness without bound.
