# Quantization diagnostic, 2026-09-22

The optional [experiment recipe](../experiments/quantization-README.md) now has
real evidence for a derived F16 reference, Q8_0 and Q4_K_M of Qwen3-1.7B on the
same Windows RTX 4070 SUPER. All **four likelihood lifetimes and nine deployment
lifetimes succeeded**. This addresses the scoped quality-reference study in
[issue #3](https://github.com/JoeyJia02/prismbench/issues/3); other GPUs, chat/task
accuracy and broad quantization recommendations remain outside this result.

## Observed tradeoffs

Likelihood uses the preselected first 32 chunks of WikiText-2 raw test, with 2K
contexts and **32,736 scored next-token targets**. Lower PPL means better
prediction on this particular text. Performance uses a separate synthetic
1,792-input/128-output workload, with three independent lifetimes per variant.

| Variant | File GB (decimal) | Prefix PPL | PPL change vs F16 | Mean TTFT, s | Mean generation token/s | Deployment peak, MiB |
|---|---:|---:|---:|---:|---:|---:|
| F16 reference | 4.070 | 15.0861 | reference | 0.2050 | 104.14 | 5,197 |
| Q8_0 | 2.165 | 15.1083 | +0.147% | 0.1767 | 167.33 | 3,645 |
| Q4_K_M | 1.282 | 16.3602 | +8.446% | 0.1791 | 233.20 | 2,953 |

Q8 reduced file size by 46.8% and showed a small observed PPL change. Q4 reduced
file size by 68.5%, generated faster in this workload and showed a larger text
prediction penalty. These observations do not make either format universally
optimal. **An 8.446% PPL increase is not an 8.446% loss of reasoning, task accuracy
or overall model quality.** The Q8/Q4 TTFT difference is small relative to these
three-run observations; it is not a reliable latency ranking.

Generation throughput sample standard deviations were 0.16, 0.60 and 0.69
token/s respectively. All nine runs verified 1,792 fresh input tokens, 128 output
tokens, zero cache reuse, full 29/29 GPU-layer placement, F16 K/V and owned-process
cleanup. Whole-device peaks include desktop applications and are sampled, not
exact allocator peaks. Background utilization was not controlled. Full GPU-layer
placement does not imply the absence of host buffers or CPU work.

## Paired prediction differences

The signed candidate-minus-F16 mean NLL differences and exploratory paired
block intervals are:

| Candidate | Delta NLL, nats/target | Exploratory 95% interval |
|---|---:|---:|
| Q8_0 | +0.001473 | [-0.000203, +0.003258] |
| Q4_K_M | +0.081079 | [+0.064253, +0.100405] |

These percentile intervals resample eight contiguous, disjoint four-chunk blocks
10,000 times with seed 42. They describe the observed prefix's resampling
sensitivity, not general model capability or guaranteed population coverage.
Blocks may share articles. The Q8 interval crossing zero does not establish zero
degradation. Cumulative NLL is printed to six decimals; the parser retains the
associated rounding limits.

The final F16 repeat matched all 32 printed cumulative NLL rows and the final
PPL of 15.0861. That establishes agreement at this output precision for two
lifetimes, not bitwise equality of all internal logits or guaranteed determinism.
The repeat is not counted as additional evaluation text.

## Lineage, costs and evidence

The community BF16 parent was pinned and verified by SHA256, converted to F16,
then quantized independently from that exact F16 file to Q8_0 and Q4_K_M. All
four files have identical complete tokenizer metadata and 311 tensor name/shape
identities. The quantized tensor inventories are 198 Q8_0 + 113 F32, and
169 Q4_K + 29 Q6_K + 113 F32 respectively. No importance matrix or requantization
was used. The community parent's equality to the official checkpoint was not
independently established; the baseline is explicitly a derived F16 artifact.

The unchanged PrismBench 0.1.0a1 runtime was installed in a separate Python 3.12
environment. The experiment helpers remain outside the installed package. All
four tools and 33 adjacent DLLs were hashed; independent review checked the
manifest against the actual runtime files. The corpus was reconstructed from its
pinned Parquet file: 4,358 rows, 1,296,367 UTF-8 bytes. Three complete token arrays
matched before scoring.

The first F16, Q8 and Q4 likelihood lifetimes took approximately 14.06, 12.11
and 11.45 seconds including their own process startup, but excluding the
controller's earlier hashing and tokenization. Their sampled VRAM peaks were
5,292, 3,706 and 3,014 MiB; sampled process-tree RSS peaks were approximately
4,750, 3,100 and 2,405 MiB. These likelihood costs are separate from deployment
costs in the table. No full-vocabulary reference-logit dump was created.

Two implementation checks failed before the accepted experiment. The first
preparation rejected an unchanged name/shape mapping because quantization changed
physical tensor order; the check now hashes a name-keyed mapping and rejects
duplicate names. The first PPL pilot completed F16 scoring but lacked the log
verbosity needed to verify effective configuration. It remains **INVALID_WORKLOAD**,
and its queue stopped before evaluating quantized candidates. Adding explicit
verbosity 4 changed logging only. The subsequent four-lifetime study used the
same predeclared corpus, windows and metric rules; no best-score selection or
retroactive admission of the invalid pilot was used.

- [Machine-readable summary](../benchmarks/rtx4070-super/quantization-quality-20260922/summary.json)
- [Accepted PPL ledger and paired differences](../benchmarks/rtx4070-super/quantization-quality-20260922/quality/results.json)
- [Retained invalid PPL pilot](../benchmarks/rtx4070-super/quantization-quality-20260922/quality-invalid-pilot/results.json)
- [Preparation manifest and lineage](../benchmarks/rtx4070-super/quantization-quality-20260922/preparation/manifest.json)
- [Rotating deployment sequence](../benchmarks/rtx4070-super/quantization-quality-20260922/performance/sequence.json)
- [Publication inventory and intentional omissions](../benchmarks/rtx4070-super/quantization-quality-20260922/publication.json)
- [Independent protocol and evidence audit](reviews/quantization-audit-20260922.md)

Raw text and reconstructible token arrays remain local because they are
third-party dataset content. The public inventory gives hashes/counts and the
exact reproduction recipe; it does not relicense the corpus as MIT. The
[protocol](quantization-methodology.md) describes upstream license declarations,
chunk alignment, BOS/EOS handling, statistical limits and source references.
