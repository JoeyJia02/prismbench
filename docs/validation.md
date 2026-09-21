# v0.1 validation record

Status: final real-hardware validation in progress, 2026-09-21. This file is updated from saved evidence before release-readiness signoff.

## Scope and machine

New measurements run the **installed wheel** from a separate working directory using upstream llama-server build **10964**, commit **b29c606e2**, version string `0.4.1-dev`. Machine: Windows 10 build 19045, Ryzen-class 6-core/12-thread CPU, 32 GB system RAM, RTX 4070 SUPER (12,282 MiB visible), NVIDIA driver 610.88. The supplied runtime bundle uses CUDA 12.4 libraries; the driver-reported CUDA compatibility is not the linked runtime version.

Model: `Qwen/Qwen3-8B-GGUF`, revision `7c41481f57cb95916b40956ab2f0b139b296d974`, `Qwen3-8B-Q4_K_M.gguf`, 5,027,783,488 bytes, SHA256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`. Quantization/source identity is backed here by the existing publisher lock; for general inputs the CLI records a user-supplied label and actual file hash.

This is an uncontrolled desktop session: GPU utilization at the single preload snapshot can include background rendering or recently completed own work. It is not a sustained-idle qualification. Keep all recorded warnings. Results are useful local deployment observations, not a clean laboratory leaderboard or estimates for other GPUs.

## Protocol

Each case has three independent process lifetimes. Exact input lengths are context minus 256; output is 128 tokens. Single sequence, 6 CPU threads, batch512/microbatch128, Flash Attention on, f16 K/V, fit disabled, context shift disabled, no internal warmup, explicit excluded128/16 warmup then cache erase. Each measured response must confirm fresh prompt count, zero cache hits, output count and no truncation.

Peak device VRAM is sampled over the whole lifetime at a nominal 0.5-second interval. It includes loading and all requests; quality sessions also include probes. Shared desktop consumption is included, process attribution is unavailable, and shorter spikes may be missed. Process-tree RSS may double-count shared pages. Startup timing excludes hashes and preflight commands; OS file cache is not flushed.

## Reproduction

Use [the context sweep](../examples/qwen3-context-sweep.json), changing local paths but retaining the model hash and recorded runtime. Reproduce into a new directory:

```console
prismbench run examples/qwen3-context-sweep.json --output outputs/reproduction
```

The complete final sessions live under `benchmarks/rtx4070-super/`. Source, binary and library hashes identify each run exactly. Older local lab results and the new runner's preliminary smoke/pilot sessions are not included in the final aggregate.

## Limits of the release candidate

- No FP16/BF16-versus-Q4 quality degradation was measured. Only same-weight placement probes are included.
- No deliberate hardware OOM was induced. OOM classification/fallback and process cleanup are exercised using deterministic real-subprocess fixtures.
- 16K is the largest requested test point, not a discovered maximum.
- Other GPU capacities, Linux GPU execution, transformers/vLLM/MLX and quantization conversion are unvalidated or deferred.
- GitHub CI is configured, but no remote repository/CI result or published package is claimed.

## Verification results

Final counts, numerical tables, install/build hashes and independent audit links are appended after the final runs complete.
