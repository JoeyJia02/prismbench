# Paired quantization diagnostic: protocol 1

This small experiment measures changes in next-token prediction on a fixed English
text prefix. It is not a general capability score, a chat benchmark, or a percentage
of intelligence retained. It reuses upstream `llama-quantize` and
`llama-perplexity`; PrismBench owns the processes, checks comparability, retains
evidence and summarizes the measured tradeoffs.

## Predeclared comparison

The parent is the community `bartowski/Qwen_Qwen3-1.7B-GGUF` BF16 artifact at
revision `dcb19155b962dbb6389f4691a982043a8e651022`, SHA256
`199b4df12194e24ac097d4fcbd279ce62bd4959bed9f0d4719d05a6ab1501861`.
The preparation recipe converts it to F16, then independently quantizes that same
F16 file to Q8_0 and Q4_K_M, without an importance matrix or requantization.
The reference is therefore a **derived F16 baseline**, not the original BF16
checkpoint. Equivalence between the community parent and the official checkpoint
has not been independently verified. Q4_K_M is mixed tensor precision, not four
bits for every tensor.

The pinned engine is llama.cpp b10964, commit
`b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`, Windows CUDA 12.4. Executable and
all adjacent DLL hashes are retained. The preparation checks complete tokenizer
metadata, tensor names/shapes and tensor-type inventories across all artifacts.
Every model and corpus file is rehashed before evaluation.

All three variants use context 2,048, batch 512, microbatch 128, six CPU threads,
one sequence, all layers on the selected GPU, flash attention on, F16 K/V cache,
and automatic fitting off. Effective context, placement and cache types must be
confirmed by logs. There is no prompt template, sampling, generation, or thinking
budget in the likelihood measurement. Qwen3-1.7B is post-trained; its raw-text
perplexity must not be interpreted as chat or reasoning performance.

## Exact input and scoring

Use `Salesforce/wikitext`, revision
`b08601e04326c79dfdd32d625aee71d232d685c3`, file
`wikitext-2-raw-v1/test-00000-of-00001.parquet`, SHA256
`5f1bea067869d04849c0f975a2b29c4ff47d867f484f5010ea5e861eab246d91`.
Read every `text` row in its original order, retaining empty rows, join rows with
two LF characters, remove terminal LF characters, and encode UTF-8 without a BOM.
Record the extracted file hash and row count. No Unicode normalization or other
whitespace cleanup is applied.

The **first 32 nonoverlapping 2,048-token chunks** are selected before examining
scores. This is a *WikiText-2 raw test prefix pilot*, not the complete WikiText-2
score. The engine uses the first half of each chunk as unscored context. At this
pinned revision it scores target positions 1,025 through 2,047 (zero based):
**1,023 targets per chunk; 32,736 scored targets in total**. There are 65,536
processed input positions. The tail and unselected chunks are not scored.

The upstream perplexity file loader removes one terminal newline, while the
tokenizer executable retains it. The extracted input deliberately has no terminal
newline. Token fingerprinting uses the same pinned runtime, `--no-escape` and
`--no-parse-special`, matching the perplexity tokenizer's defaults. Compare the
complete token arrays and store full-input and evaluated-prefix hashes/counts.
Record BOS/EOS metadata; the engine may replace the first token of each chunk
with BOS only when the model's `add_bos` policy enables it. `add_eos` must be false.

Do not enable stride, parallel chunk batching or saved full-vocabulary logits.
The fixed non-strided `--ppl-output-type 1` output contains cumulative mean NLL
and PPL for each chunk. The parser rejects incomplete rows, unexpected offsets,
nonfinite values, inconsistent printed precision and absent final estimates.

## Paired metrics and uncertainty

Let `a_i` be the printed cumulative mean negative log likelihood after chunk
`i`, numbered from 1. Equal scored-token counts allow reconstruction of each
chunk mean as `i*a_i - (i-1)*a_(i-1)`. Compare the same chunks with F16 using:

- Signed mean NLL difference, in nats per scored target; positive means worse
  next-token prediction on this input.
- PPL ratio `exp(candidate_mean_NLL - reference_mean_NLL)` and relative PPL
  change; these are not percentages of overall model quality lost.
- Paired chunk differences retained for inspection.

For an exploratory interval, group the 32 chunks into eight contiguous,
nonoverlapping blocks of four. Resample those paired block means with replacement
10,000 times using Python's seeded RNG (seed 42); retain percentile 2.5/97.5
endpoints. This describes sensitivity to resampling the observed prefix blocks.
Adjacent blocks can still share articles. Prefix selection, training contamination
and document dependence prevent interpreting it as a general capability confidence
interval. Do not claim statistical significance or equate crossing zero with no
degradation.

Upstream prints cumulative NLL to six decimal places. Reconstructed chunk `i`
has up to `(2*i-1)*0.5e-6` nats/target rounding error per model; a paired difference
can have twice that bound. Avoid overstating tiny Q8 effects. The upstream
`PPL +/-` is an approximate token-level standard-error propagation, not the paired
interval or hardware variability. Retain it separately.

The quality order is F16, Q8_0, Q4_K_M, then one extra F16 run to inspect numerical
drift. The repeat does not add independent corpus observations and does not enter
the bootstrap as more text. Retain failures; do not silently rerun or select the
better result.

## Performance and resources

Measure deployment performance separately with the existing PrismBench workload:
2K context, 1,792 fresh prompt tokens, 128 generated tokens, one excluded warmup,
zero cache reuse, F16 K/V and full GPU placement. Use three independent lifetimes
per variant in rotating order: F16/Q8/Q4, Q8/Q4/F16, Q4/F16/Q8. Rotation reduces
one simple order confound but does not certify a quiet or thermally controlled
machine. Report all runs and mean TTFT/TPS with sample variation, without a
universal winner ranking.

Keep perplexity and deployment resource peaks separate: full-vocabulary likelihood
processing has different memory/workload costs from generation. Device VRAM is
sampled whole-device usage and includes desktop applications; RSS may double-count
shared pages. Every tool runs in an owned process tree with a deadline and cleanup
record. Preparation/evaluation stop on low available host RAM or failed cleanup;
this study does not deliberately induce OOM.

## Data distribution and upstream references

The model, dataset and runtime keep their upstream terms. The WikiText card's
metadata declares CC BY-SA 3.0 and GFDL while its prose links CC BY-SA 4.0. Record
those declarations without resolving the discrepancy or relicensing the corpus
as MIT. Published evidence contains scalar scores, hashes, counts and commands;
the downloaded corpus and reconstructible token arrays remain local. The recipe
downloads neither implicitly and lets readers recreate both from the pinned source.

- [Community parent and provenance](https://huggingface.co/bartowski/Qwen_Qwen3-1.7B-GGUF/tree/dcb19155b962dbb6389f4691a982043a8e651022)
- [Official model card](https://huggingface.co/Qwen/Qwen3-1.7B)
- [Pinned dataset card](https://huggingface.co/datasets/Salesforce/wikitext/blob/b08601e04326c79dfdd32d625aee71d232d685c3/README.md)
- [Pinned perplexity source](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/tools/perplexity/perplexity.cpp)
- [Upstream metric interpretation](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/tools/perplexity/README.md)
- [Tokenizer file handling](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/tools/tokenize/tokenize.cpp)
