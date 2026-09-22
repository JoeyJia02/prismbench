# Quantization perplexity study

Status: **SUCCESS**

Fixed raw-text corpus and 32 non-overlapping 2K chunks. These observations measure
cross-entropy/perplexity on this corpus, not general intelligence or percent quality retained.

| Model | Repeat | Status | PPL | Whole-device peak MiB | Evidence |
|---|---:|---|---:|---:|---|
| F16 | 1 | SUCCESS | 15.0861 | 5292.0 | [logs](perplexity/F16-r1) |
| Q8_0 | 1 | SUCCESS | 15.1083 | 3706.0 | [logs](perplexity/Q8_0-r1) |
| Q4_K_M | 1 | SUCCESS | 16.3602 | 3014.0 | [logs](perplexity/Q4_K_M-r1) |
| F16 | 2 | SUCCESS | 15.0861 | 5292.0 | [logs](perplexity/F16-r2) |

Comparisons and paired corpus uncertainty are in [results.json](results.json).
The additional F16 run measures numerical drift separately from corpus uncertainty.
Whole-device sampled memory includes other applications and can miss transients.
Tokenizer stdout is corpus-derived and remains local; it is not covered by the tool's MIT license.
