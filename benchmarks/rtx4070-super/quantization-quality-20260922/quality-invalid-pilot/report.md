# Quantization perplexity study

Status: **ERROR**

Fixed raw-text corpus and 32 non-overlapping 2K chunks. These observations measure
cross-entropy/perplexity on this corpus, not general intelligence or percent quality retained.

| Model | Repeat | Status | PPL | Whole-device peak MiB | Evidence |
|---|---:|---|---:|---:|---|
| F16 | 1 | INVALID_WORKLOAD | — | 5292.0 | [logs](perplexity/F16-r1) |

Comparisons and paired corpus uncertainty are in [results.json](results.json).
The additional F16 run measures numerical drift separately from corpus uncertainty.
Whole-device sampled memory includes other applications and can miss transients.
Tokenizer stdout is corpus-derived and remains local; it is not covered by the tool's MIT license.

Failure: ValueError: Missing or unexpected effective context: []
