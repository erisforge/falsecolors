# Changes

## Unreleased

### Added
- `measure` subcommand: computes the Caudle Distance (SCD per Definition 2.15.2) of a cover document against a native cover-domain corpus. Pure stdlib. Builds PPMI co-occurrence vectors from the corpus, scores cosine similarity over adjacent content tokens, and returns the KL divergence between the document's TAD and the corpus's TAD with Laplace smoothing. Usage: `python falsecolors.py measure --source cover.txt --corpus brewery_native.txt`. A native document scored against its own corpus returns SCD ≈ 0; an unshifted source-domain document returns a high SCD with very few adjacent pairs scored.

### Fixed
- IdentEncoder placeholder collision past 40 unique identifiers. The pool of 40 NATO/word names was indexed with `% len(POOL)`, so the 41st unique identifier silently reused the 1st placeholder and decoding became ambiguous. Past the first cycle, placeholders are now suffixed with the cycle number (`alpha`, ..., `nectar`, `alpha2`, ..., `nectar2`, `alpha3`, ...), preserving uniqueness without bound.
