# Opt-in Windows allocation-failure validation

This directory contains validation tooling, not an additional PrismBench backend or an ordinary benchmark preset. The helper runs the **unchanged installed 0.1.0a1 wheel** and is separate from the installed CLI. Do not run the deliberately oversized config through the CLI without this supervisor.

The [2026-09-22 record](../docs/validation-20260922.md) reports one observed CUDA allocation rejection and successful explicit fallback. The external host-memory cap can contribute to CUDA allocation rejection: this does **not** isolate physical VRAM exhaustion, maximum context, or natural memory pressure.

## Prerequisites and invocation

- Windows x64, installed PrismBench **0.1.0a1** in a separate virtual environment, and GPU index 0.
- The exact Qwen3-8B Q4_K_M model and llama.cpp b10964 Windows CUDA 12.4 runtime from the [quickstart](../docs/quickstart-rtx4070-super.md). Verify both archive hashes; the executable is a launcher, so retaining matching DLLs matters.
- At least 12 GiB available system RAM at each of five baseline samples, valid GPU memory telemetry, and no existing `llama-server` process. Leave other applications alone; their background activity remains a confounder.
- A checkout containing this helper (it was added after the alpha tag). Copy the example config to your experiment directory and change only the model/server paths and descriptive labels. The helper rejects changes to its bounded workload, device, hash, deadlines or fallback policy.

For example, after preparing `D:\PrismBench-Repro-20260922\oom.local.json` with model/server paths relative to that file:

```powershell
& D:\PrismBench-Repro-20260922\.venv\Scripts\python.exe -I D:\LocalLargeModel\experiments\windows_oom_recovery.py --config D:\PrismBench-Repro-20260922\oom.local.json --output D:\PrismBench-Repro-20260922\outputs\oom-recovery --confirm-hardware-oom
```

Use your actual directory names. The output directory must not exist. `-I` and a site-packages installation are required to keep the repository's source out of the child CLI's import path. The sample config is [oom-recovery.json](oom-recovery.json).

## What the supervisor enforces

The case requests context 524,288 with f16 KV, but only 128 prompt tokens and 16 output tokens. That context is deliberately beyond the model's training context and is an allocation stress request, not a valid long-context capability evaluation. There is **one** allowed fallback: context 2,048 with the same token counts and GPU placement. No allocation-size search is performed.

Before the child CLI resumes, an outer Windows Job has kill-on-close plus an **8 GiB job-wide committed-memory limit**. A separate watchdog samples host available RAM and owned-tree RSS about every 100 ms, aborting below 8 GiB available RAM, above 8 GiB summed RSS, or after 120 seconds. Startup and request deadlines are 30 and 15 seconds. RSS can count shared pages repeatedly, and sampled guards can miss transients; the Job limit is the hard host committed-memory boundary, not a GPU memory limit.

The helper uses the pinned release's private Windows Job implementation only in its own supervisor process. This makes the helper version-sensitive; it does not patch the installed CLI or its child server. Tests check the queried native limits, process ownership and a separate harmless sentinel. Cleanup never targets processes by a global name.

## Evidence and interpretation

`audit.json` records the protocol, queried Job limits, helper/source hashes, five baseline samples, the watchdog observations, 1 Hz external telemetry and 15 post-chain samples. The `benchmark/` directory contains the unmodified CLI's failed and successful attempts and raw logs. The helper additionally records a sentinel outside the child Job surviving that Job's cleanup, then cleans up the sentinel itself.

A narrow `PASS` requires an explicit `cudaMalloc ... out of memory` diagnostic, an `OOM → SUCCESS` chain with correct parent linkage, confirmed owned cleanup, successful 128/16-token fallback, and the final three GPU samples at or below baseline median plus 256 MiB. A guard, timeout, host-only allocation error, unexpected success or missing evidence is inconclusive. `physical_vram_oom_proven` remains **false even on PASS**, because the Job cap can influence the allocation failure.

Post-chain settling is not a recovery admission check **before** the fallback. The released CLI retries immediately after confirming owned-process cleanup; it has no sustained-memory-recovery gate. One controlled sentinel does not prove that every desktop application was unaffected. Do not remove the cap or escalate the workload to turn an inconclusive result into a claim of physical exhaustion.
