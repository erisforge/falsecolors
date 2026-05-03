# Changes

## Unreleased

### Fixed
- IdentEncoder placeholder collision past 40 unique identifiers. The pool of 40 NATO/word names was indexed with `% len(POOL)`, so the 41st unique identifier silently reused the 1st placeholder and decoding became ambiguous. Past the first cycle, placeholders are now suffixed with the cycle number (`alpha`, ..., `nectar`, `alpha2`, ..., `nectar2`, `alpha3`, ...), preserving uniqueness without bound.
