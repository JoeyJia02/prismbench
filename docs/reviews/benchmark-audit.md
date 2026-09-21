# Independent benchmark evidence audit — 2026-09-21

**PASS for the observed Windows/RTX 4070 SUPER runs.** All 21 final model
lifetimes completed and the saved raw evidence agrees with the reported
metrics. This certifies the consistency of these local observations, not
performance on other GPUs or a clean-machine benchmark.

Reviewer: methodology / test engineering agent, independently inspecting
artifacts produced by the main engineer. No GPU inference was launched by the
reviewer. Checks used separate read-only Python assertions over raw files;
resource peaks and timing fields were not accepted merely because the product's
own report validator accepted them.

## Final evidence and installation identity

- [Context sweep](../../benchmarks/rtx4070-super/context-sweep/results.json):
  session `c4816faa4160441e9851a6eef9bc1b19`, 15/15 successful lifetimes,
  three repeats each at 1K, 2K, 4K, 8K and 16K.
- [Offload and quality](../../benchmarks/rtx4070-super/offload-quality/results.json):
  session `d11f69a53a5843fe92a0662395a1f42a`, 6/6 successful lifetimes,
  three repeats each at 37/37 and 20/37 GPU layers, both with 4K context.
- Both final sessions use the same installed package source hashes, model,
  runtime executable and 33 bundled runtime-library hashes.
- The built wheel's 14 Python files and two packaged JSON files byte-match the
  installed package under the isolated wheel-install environment, outside
  `src/`. Recorded source hashes match those installed Python files.
- Validation wheel SHA256:
  `07576ad9355c69a413581010a49250cb709c00a07c1ec1bbf1cace54cad0d349`.
- The model file was independently rehashed after inference finished:
  `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`,
  5,027,783,488 bytes. The runtime executable and all 33 recorded DLLs were
  likewise independently rehashed successfully.
- Runtime: upstream llama.cpp build 10964, commit `b29c606e2`, Windows CUDA
  distribution. Model: the user-labelled `Qwen/Qwen3-8B`, Q4_K_M GGUF.
  The artifact hash is verified; its base-model label is still a user assertion.

## Checks performed for every final attempt

1. The session row equals its individual `attempt.json`; status is `SUCCESS`,
   owned-process cleanup is confirmed, and remaining PID/error lists are empty.
2. Saved token count and canonical token-ID SHA256 match the request and runtime
   record. All three repeats within each case use identical prompt hashes.
3. Exactly one performance request matches the planned full prompt/output
   budget. Its raw request has streaming enabled, cache reuse disabled, and
   `ignore_eos=true`. Short warmup requests remain separate.
4. The saved SSE stream parses to the saved event array. Its terminal timings
   equal the normalized response's original timings. Actual input/output counts
   equal the requested counts, cached prompt count is zero, and truncation is
   false. Reported engine rates equal the runtime's rates without recomputation
   using a different decode denominator.
5. Joining `event_index` in the arrival JSONL to the first nonterminal event
   with nonempty content reproduces **each saved TTFT exactly**. Arrival indices
   are complete and ordered; elapsed timestamps are monotonic. Total latency is
   no earlier than the terminal event and includes a small finalization delay.
6. Runtime log evidence confirms 37/37 GPU layers in the context sweep and the
   requested 37/37 or 20/37 layers in the offload comparison. Effective context,
   f16 K/V caches and enabled Flash Attention match the configuration.
7. Independently taking the maxima of every attempt's raw resource samples
   reproduces peak device VRAM, process-tree RSS and system RAM exactly. Baseline,
   loaded-idle and post-cleanup values also agree with their corresponding
   sample files. Sample counts agree; no telemetry error was observed.

For the six quality runs, each of the eight saved item outputs was also matched
to its raw request/response using its token-ID fingerprint. Requests explicitly
use newline stopping, greedy generation, cache disabled and EOS enabled. The
raw prompt counts, cache counters, lack of truncation and returned text agree
with the scored items. Suite hashes and strict whole-answer scoring were
recomputed independently.

## Observed results

Means below use three independent lifetimes. VRAM is the largest sampled
whole-device peak among those lifetimes, in MiB.

| Allocated context | Input / output tokens | Mean TTFT s | Mean engine decode token/s | Largest sampled VRAM MiB |
| --- | --- | ---: | ---: | ---: |
| 1024 | 768 / 128 | 0.205 | 80.13 | 6177 |
| 2048 | 1792 / 128 | 0.439 | 77.95 | 6320 |
| 4096 | 3840 / 128 | 0.971 | 72.77 | 6600 |
| 8192 | 7936 / 128 | 2.134 | 66.40 | 7215 |
| 16384 | 16128 / 128 | 5.122 | 54.99 | 8501 |

The separate matched 4K workload demonstrates an observed deployment tradeoff:

| GPU layers | Mean TTFT s | Mean engine decode token/s | Largest sampled VRAM MiB | Version 2 probe passes |
| --- | ---: | ---: | ---: | --- |
| 37/37 | 0.998 | 70.52 | 6689 | 8/8 in each of three runs |
| 20/37 | 4.951 | 11.50 | 4501 | 8/8 in each of three runs |

These quality results show no difference on these eight elementary probes.
They do not establish zero general quality loss, and they compare placement of
the same Q4_K_M artifact rather than quantization against FP16/BF16.

## Pilot preservation and limitations

The [version 1 quality pilot](../../benchmarks/rtx4070-super/quality-protocol-v1-pilot/results.json)
still contains six successful inference lifetimes with **0/8** whole-answer
probe passes each. Those version 1 requests did not stop at newline. Correct
first lines followed by extra text failed the original exact-answer contract.
The original counts and answers were independently checked and remain unchanged.
Version 2 is a new one-line generation protocol, not rescoring of that pilot;
no quality improvement is inferred across the protocol boundary. See the
[protocol decision](quality-protocol-v2.md).

The final context sweep recorded nine pre-load utilization warnings, and the
offload session recorded six. Pre-load snapshots ranged from 1–98% in the sweep
and 7–61% in the offload session. A single snapshot can reflect background
activity or recent owned activity; it cannot certify a stable idle environment.
The reports correctly preserve these warnings. Differences of a few percent
between sessions must not be treated as established improvements.

TTFT is client-observed first text, including transport, parsing and evidence
instrumentation overhead; Unicode buffering can make it later than the first
underlying token. Device VRAM includes desktop applications, and sampling can
miss shorter peaks. RSS can double-count shared pages. Peaks span load, warmup,
performance, optional quality and shutdown sampling. Process disappearance and
a post-stop sample do not prove a sustained return to a resource baseline.

16K is the largest **tested** context, not an exact capacity ceiling or proof of
long-context answer quality. No deliberate hardware OOM was performed; real
partial offload was exercised, while OOM detection/fallback/timeout paths were
tested separately with controlled process fixtures. No other GPU size, Linux
CUDA execution, model family, higher-precision reference or external replication
is certified by this audit.

No unresolved blocking inconsistency was found in the final benchmark evidence.
