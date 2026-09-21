# Independent follow-up audit, 2026-09-22

Decision: **PASS for the two specifically bounded validation claims below.** This is additional evidence for the unchanged published alpha, not a new release or a declaration that external GPU replication and ordinary VRAM-pressure recovery are complete.

## Fresh installation audit

A reviewer independent of the run controller rehashed the public wheel, copied 5 GB model, runtime executable, all 33 DLLs and both cached runtime ZIPs. Fourteen installed source hashes match the recorded benchmark evaluator; both packaged JSON files match the measured wheel. The new Python 3.14.5 environment imports from its own site-packages with system site-packages disabled and passes the dependency check.

All three 2K attempts have 1,792 fresh input and 128 output tokens, zero cache reuse, no truncation, effective context 2,048, full 37/37 GPU layers and confirmed cleanup. The reviewer reconstructed every TTFT from event-arrival records, checked all six SSE/event pairs and recomputed GPU/RSS/system RAM peaks. All 248 copied experiment files match the external-directory originals byte-for-byte; the additional onboarding receipts retain the new environment and cached-asset disclosures. Report links resolve.

The omitted Visual C++ prerequisite was established from PE imports and the existing System32 DLLs, then added to the quickstart using Microsoft's official dependency guidance. The machine's existing driver and OS libraries remain inherited dependencies. This review supports **same-machine fresh-directory/venv reproduction**, not clean-OS or other-hardware validation.

## Before the live CUDA experiment

A separate protocol reviewer required a single oversized allocation request, exact asset/configuration gates, finite deadlines, RAM admission and watchdog checks, an outer pre-resume Windows Job cap, a separate sentinel, and explicit post-chain telemetry. The helper was corrected during review to use the CLI's positional config argument, retain sentinel-cleanup errors and reject existing model-server work.

The final reviewed helper SHA256 is `4ff903467ba219331d0a8615632cc3fe989c009e075825b671c0e2c24c002411`. The reviewer independently ran its **41 hardware-free tests**, including a native Windows Job query verifying the 8 GiB commit limit and kill-on-close flag, child membership, sentinel exclusion and owned cleanup. No reviewer GPU run was used in place of the actual controller experiment.

## Actual failure/fallback evidence audit

The independent post-run review verified all **150 OOM experiment files** against their external-directory originals, validated result schema and relations, and compared source/runtime identities with both the fresh installation and the original benchmark. The raw server log records a request for **73,728 MiB** rejected by `cudaMalloc` with **out of memory**; that quantity was requested, not allocated.

The failed attempt remains `OOM` with null performance metrics and confirmed cleanup. Its linked fallback completed 128/16 tokens, zero cache reuse and effective context 2,048; raw request, token hash, terminal event and TTFT arrival agree. Both attempts and the outer Job report empty remaining PID lists and no cleanup errors. No watchdog abort was recorded; the separate sentinel survived the child Job cleanup and was then independently cleaned up.

Five baseline samples and fifteen post-chain samples all record 1,303 MiB device memory. Post-chain samples span **14.0046 seconds from first to last**, approximately one-second intervals; this is sampled evidence, not continuous monitoring of every allocation. The minimum observed available RAM was 14.268 GiB and maximum owned-tree RSS 4.827 GiB. Desktop utilization confirms the environment was uncontrolled.

The reviewer required the claim to stay **CUDA allocator rejection and fallback under an 8 GiB Windows Job cap**. The cap can contribute to allocation rejection even when sampled RSS is below it. Physical VRAM exhaustion, a maximum context, ordinary uncapped memory-pressure recovery and memory settling before retry remain unproven. `physical_vram_oom_proven` is correctly false.

## Engineering checks and remaining work

Local Windows/Python 3.12 checks after adding the helper: **192 tests passed, one opt-in GPU test skipped**, Ruff passed for source, tests and experiments. Hosted CPU CI must also pass before merging; it does not execute the opt-in GPU experiment. The helper stays outside the installed runtime package and pins the private Windows Job interface to the tested alpha version. No product backend, model loader or evaluator source changed.

No open P0/P1 finding remains for these evidence claims. External reproduction, a pre-retry recovery policy and a high-precision quality reference remain in the public backlog. Original release artifacts and prior raw measurements are retained unchanged.
