# Benchmark methodology

This describes the implemented v0.1 protocol. A successful run
answers whether one exact workload completed under one exact configuration on
the measured machine. It does not predict every model, GPU, or application.
Historical laboratory measurements have a separate protocol; they must be
identified as imported evidence, never presented as runs of the new package.

## Workload and comparison unit

Use one local `llama-server` process, one sequence, and one outstanding request.
One comparison cell consists of model file hash, runtime identity, requested
configuration, effective configuration, input token IDs, output budget, and
sampling settings. Keep all of these fixed for repeats. Model labels such as
`Q4_K_M` describe an artifact; they do not prove its tensor types or provenance.
GGUF is a container, not a precision. FP16/BF16, weight quantization, and KV-cache
precision are separate settings.

The v0.1 target is a user-supplied local GGUF and compatible llama.cpp binary.
The sample recipes use Qwen GGUFs;
other model families need validation before they are advertised as supported.
No model-download, quantization, inference-kernel, or tokenizer implementation
is necessary. Reuse the selected runtime for these operations.

Context points are 1024, 2048, 4096, 8192, and 16384 tokens, with longer points
explicitly configured. A context value means the effective per-sequence token
capacity, not prompt length. Always reserve output and special-token space:

```text
prompt_tokens + generated_token_budget + safety_margin <= effective_context
```

Construct a deterministic public synthetic source, tokenize with the running
model, and take exactly the configured number of token IDs. Store those IDs,
their SHA256, and raw requests/responses. The source generator is preserved in
the package code, whose hashes are recorded. The performance path uses raw
completion with token IDs, so a chat template cannot silently change its size.
Check the final response's actual token counts, zero reused prompt tokens, and
absence of truncation/context shift. Force the requested output count with
`ignore_eos` only for the throughput workload; quality probes must allow EOS.
Increasing context while holding a tiny prompt constant tests allocation, not
long-input processing. Label that distinction in each result.

## Timing definitions

Use a monotonic high-resolution clock for client durations. Wall-clock UTC
timestamps identify artifacts and must not be used to calculate latency.

| Metric | Boundary / source | Interpretation |
| --- | --- | --- |
| Process-to-ready load time | Immediately before process start until the owned server is healthy | Includes process startup and model initialization; excludes model download and hashing |
| Client TTFT | Immediately before HTTP send to first nonempty generated text SSE event | First-text approximation; includes localhost transport, queueing, prompt processing, sampling, and stream delivery |
| Client total latency | Same request start to terminal completion event | User-observed completion latency; excludes model loading and warmup |
| Engine prompt throughput | Final `timings.prompt_per_second` | Runtime-reported prompt processing rate |
| Engine generation throughput | Final `timings.predicted_per_second` | Runtime-reported decode rate; retain runtime's denominator convention |

SSE comments, ping events, progress events, empty events, and terminal metadata
are not first text. The adapter measures first nonempty generated content. This
is an approximation to first token because Unicode bytes may be buffered across
multiple tokens; it is not an engine-internal token timestamp.
An absent first token yields `null`, never zero. A broken stream or missing
terminal timing record is a failed/incomplete measurement. Parse complete SSE
events and UTF-8 correctly across arbitrary network boundaries. A socket read
timeout alone does not limit an endless stream of pings; enforce a wall-clock
request deadline as well.

Store original final timings alongside normalized fields. Do not replace
`predicted_per_second` with `predicted_n / predicted_ms`: runtime revisions may
treat the first sampled token differently. In the local historical 8B example,
128 predicted tokens and 1593.501 ms accompany 79.6987 token/s, which uses 127
timed decode intervals. A regression test protects this distinction. The server
documents raw token IDs, streaming events, cache counters, and timing fields;
pin a tested runtime release because these interfaces evolve.
[llama.cpp server API](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

Process restart does not evict Windows/Linux filesystem caches. Repeated
process-to-ready measurements are normally warm filesystem-cache loads and
must not be called cold disk loading. v0.1 does not drop system caches.

## Resource measurements

| Metric | Measurement | Limitation |
| --- | --- | --- |
| Model size | Exact local file size in bytes plus SHA256 | File size is not resident VRAM or RAM |
| Pre-load idle VRAM | One explicit sample before launch | Includes desktop and other applications; not a quiet-period median |
| Loaded idle VRAM | One explicit sample after readiness, before warmup | Snapshot rather than a stable idle-period estimate |
| Peak VRAM | Maximum device memory sample during the owned process lifetime | Sampled peak; short allocation spikes can be missed |
| Process RAM | Sampled sum of owned process-tree RSS | Shared pages can be counted more than once |
| System RAM | Used/available physical RAM from the OS | Includes unrelated processes and filesystem caching |

Use MiB = 1024² bytes. Samples include monotonic time and phase; config records
the requested interval, default 0.5 seconds. Actual gaps can be longer because
`nvidia-smi` and explicit samples take time. Sampling continues through loading,
warmup, inference, optional quality probes and process shutdown; the reported
peak spans that lifetime. These are not exact allocator high-water marks.
Unavailable values stay `null`. Raw samples retain telemetry errors, and failed
resource finalization creates an attempt warning. Windows commit memory and
process-attributed GPU memory are not measured by the package.

Use NVIDIA's device-wide `memory.used`/NVML equivalent for portable NVIDIA
telemetry. Windows WDDM can return N/A for process GPU memory because Windows
manages it; do not substitute zero or invent process-level attribution.
[NVIDIA nvidia-smi documentation](https://docs.nvidia.com/deploy/nvidia-smi/index.html).
An all-layers-on-GPU log still does not imply zero CPU activity or zero CPU
weight buffers. Derive layer placement from effective runtime logs; missing
placement evidence gives an unknown offload state. Record CPU model, threads,
RAM, driver, OS, and runtime build whenever offload results are compared.

The package records pre-load GPU utilization and warns above 5%. A normal desktop
session can support a useful diagnostic run, but small performance differences
need quiet-machine repeats. Do not label an unattended diagnostic run
`CLEAN_LOCAL` merely because the benchmark succeeded. The historical lab's
30-second admission gate is stronger than a short v0.1 baseline and should not
be implicitly inherited as a claim of the package.

## Repeats and cache policy

The default is three independent server lifetimes per configured case, with
one performance request per lifetime. Raw attempts, failures, warmup outcomes,
and sample counts are retained. The report shows mean TTFT, mean generation
rate, sample standard deviation of generation rate, and success/attempt counts.
A single run is a smoke test. No p95 is inferred from three samples. Small
differences require additional repeats; configuration order is sequential,
so deliberate comparisons should also consider thermal/order effects.

Warm up once per loaded configuration using a separately recorded small
workload, then exclude that request from inference statistics. Set
`cache_prompt=false`, erase the slot before warmup and again before measurement,
and require the final cache counter to be zero. The adapter rejects runtimes
without the required slot/cache interfaces instead of changing this protocol.

The effective context/parallel settings and actual processed/generated token
counts must match the planned workload. An allocation success is not an
inference success. The largest successful configured context is a **maximum
tested context**, not an exact maximum or proof of long-context answer quality.
An untested higher context remains unknown. A failed higher point bounds only
that precise artifact, placement, workload, and available-memory state.

## Failure, OOM, and fallback

Outcomes are `SUCCESS`, `INVALID_WORKLOAD`, `ERROR`, `OOM`, `TIMEOUT`,
`CANCELLED`, and `CLEANUP_FAILED`. Load and other runtime errors use `ERROR`
with a diagnostic message. Classify OOM
from an explicit allocation/CUDA out-of-memory diagnostic or structured backend
error. Exit code 137, an HTTP 500, a timeout, or low sampled free VRAM alone does
not prove OOM. Preserve enough bounded log output to audit the classification.

After an owned attempt exits or fails, terminate and reap its owned process
tree. On Windows, a kill-on-close Job Object assigned before child execution is
used by the adapter. Linux uses an owned process group. No global process-name
termination is used. Owned process cleanup must be confirmed before retry.
Post-stop samples are saved when available; the package does not wait for a
stable return to baseline. Process disappearance alone does not prove VRAM
recovery. Cleanup failure stops the sequence. Windows Job ownership covers an
abrupt controller exit; Linux SIGKILL can leave the owned process group alive.

Fallback is an opt-in ordered list of explicit configurations with a bounded
attempt count. A safe initial policy is fewer GPU layers at the same context;
smaller context may follow only as a separate workload. Each retry has its own
requested/effective configuration, status, and metrics and links to the failed
parent attempt. Do not retry invalid configurations or arbitrary runtime
errors as OOM. Never silently download a smaller model, change quantization, or
retry indefinitely.

Changing GPU layers changes CPU participation and throughput. Reducing context
changes both memory demand and prompt work. These are useful deployment options,
but must not be averaged into the original benchmark cell. A successful
fallback does not make its failed parent successful. Reports should say which
option completed, what it cost, and what remains untested. A future ranking can
show Pareto choices by memory, latency, and measured probe score; v0.1 need not
invent a universal best-value scalar.

## Lightweight quality assessment

v0.1 includes eight versioned public copy, extraction and arithmetic probes.
Scoring is a case-sensitive exact match after Unicode NFKC and whitespace
normalization. Records save every prompt, raw answer, expected answer, score,
seed, token-ID fingerprint, EOS policy and generation budget. The adapter uses
greedy raw completion, no implicit chat template, a 64-token output budget, and
an explicit newline stop. The stopping sequence is saved in both request and
generation provenance. Scoring still checks the entire returned answer; it
does not extract a favorable first line from an unconstrained response.
Every prompt must fit with output plus an eight-token margin. Instruction
models that require a template may need a custom suite with explicit formatting.
The result is **probe pass rate**, not model quality or retained intelligence.

Bundled suite version 2 defines this one-line completion contract. A pre-release
version 1 pilot had no newline stop: the tested model often produced a correct
first line followed by more examples/reasoning, which failed strict whole-answer
matching. Those original 0/8 pilot outcomes remain unchanged and are excluded
from version 2 comparisons. Fresh version 2 runs are required; historical
outputs are never rescored by truncating them. An 8/8 result on this basic suite
also has a ceiling effect and cannot establish general quality preservation.

To estimate a change, run exactly the same suite against an explicit reference
artifact and candidate. Report paired item outcomes and percentage-point score
change. The reference must share model revision, tokenizer, prompt formatting,
and evaluator; a different base model is a deployment comparison, not isolated
quantization loss. The comparison validates suite, token-ID hashes, seed,
context/workload, runtime executable/library hashes, and known GPU placement.
Quantization, GPU-layer and KV changes are explicitly listed. The `model_id`
is user asserted; the package cannot prove a common base-model revision.
Multiple eligible attempts require explicit selection, and inconsistent paired
pass/fail outcomes across same-configuration repeats block comparison.
A missing baseline means loss is unknown. CPU placement with
the same weights is not itself lower precision, although backend numerical
differences can alter generation. Record such changes instead of attributing
them automatically to quantization.

Three easy capital/arithmetic checks in the legacy lab detect catastrophic
breakage only. They cannot estimate quality loss, and identical outputs alone
do not prove equal quality. Small fixed suites have ceiling effects, sampling
variance, and possible training contamination; report counts and caveats rather
than a misleading decimal quality score.

For a later optional stronger quantization check, reuse `llama-perplexity` with
a fixed, licensed corpus slice and hash. Compare perplexity only with matching
model/tokenizer/context/chunking and an explicit reference. Relative PPL change
is a next-token prediction difference on that corpus, not task accuracy loss.
KL comparison of reference and quantized logits is available upstream, but its
reference-logit storage and FP16 run can be expensive for 12 GB machines. This
does not belong in the required first-run demo.
[llama.cpp perplexity tool](https://github.com/ggml-org/llama.cpp/blob/master/tools/perplexity/README.md).

## Existing evidence and reuse audit, 2026-09-21

The starting directory already contains a functioning, specialized Windows
laboratory. Preserve it while extracting general interfaces. Useful references:

| Local component | Reusable evidence or design | Packaging limitation |
| --- | --- | --- |
| `bench/worker.py` | Exact token IDs, warmup, slot erase, workload checks, raw responses | Fixed 4096/3840/128 workload and non-streaming measurement |
| `bench/system.py` | Device samples, RAM/commit guard, Win32 process ownership, atomic JSON | Windows imports, first-GPU assumption, system-specific admission policy |
| `benchmark.py` | Runtime/model hashes, effective config parsing, independent runs, recovery | Hard-coded cases, paths, port, and prior experiment authorization |
| `bench/gguf_meta.py` | Header metadata, tokenizer/template fingerprint, file hashing | Harden bounds before using it for arbitrary user files |
| `scripts/check_protocol.py`, `scripts/check_guard.py` | Synthetic protocol and guard checks | Convert reusable expectations into packaged automated tests |
| `runs/*/result.json` and original reports | Real hardware observations with provenance | Historical protocol, not proof that the new package works |

Inspection of the three original 2026-09-19 Qwen3-8B-Q4_K_M formal records gives:

| Run suffix | Prompt token/s | Decode token/s | Sampled device peak MiB |
| --- | ---: | ---: | ---: |
| `071411_primary_1` | 4324.6993 | 79.6987 | 7183 |
| `071501_primary_2` | 4319.8877 | 79.6050 | 7183 |
| `071550_primary_3` | 4318.2409 | 79.3043 | 7155 |

These records report success, 3840 fresh input / 128 generated tokens, 4096
context, 37/37 GPU layers, successful recovery, and clean-local eligibility.
Their runtime is the PrismML llama.cpp fork at commit
`7dffb158de30ebb8ef9d64f33c6b0b2d7c1e6313`, not an unspecified upstream build.
The records contain engine PP/decode rates and 1 Hz device VRAM samples. They
contain neither streamed TTFT nor a normalized process-to-ready load-time field.
Do not backfill either from engine prompt time or total session duration.
The original full artifacts remain the authority; publishing sanitized samples
must retain numeric values and source hashes while removing personal paths,
process inventories, and device UUIDs where unnecessary.

The 12-run Bonsai packing pilot is further evidence that task shape can matter,
but it is not a general ranking of models or quantization quality. Its proposed
selector and holdout results were not executed and cannot be counted as product
features or validation.

## Validation and release gates

Unit tests must exercise malformed configuration, token reservation, streaming
first-token boundaries, nonfinite/missing timing fields, cache hits, OOM
classification, fallback lineage, and failed-run export. HTTP integration tests
need a controlled local stub with split SSE chunks, early disconnect, load
failure, timeout, and cleanup paths. These runs are synthetic protocol tests
and must not enter a hardware benchmark table.

A release additionally needs an installed-wheel CLI run against a real local
GGUF and supported runtime, with report artifacts independently inspected for
timing validity, context verification, telemetry, and process cleanup. Preserve
at least one small real sample and its full provenance; expand to three repeats
for a performance claim. A sample from only an older script is insufficient.
Hardware-free CI verifies packaging and protocol behavior on Windows and Linux;
it does not certify CUDA compatibility or claim real GPU execution.

Unsupported or unmeasured quality loss, other GPU capacities, exact maximum
context, and alternate backends remain explicit backlog items. Honest unknowns
and reproducible failed attempts are part of the product's value.
