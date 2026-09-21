# v0.1 validation record

Status: **21/21 final real-hardware attempts completed successfully**, 2026-09-21. This record identifies the original measured wheel. Publication builds and remote CI are tracked separately in the [publication audit](reviews/publication-audit.md); the hardware limitations below still apply.

The [2026-09-22 follow-up](validation-20260922.md) adds same-machine fresh-environment reproduction and one bounded CUDA allocation-rejection/fallback experiment. Those are separate protocols and are not merged into this original 21-attempt aggregate.

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
- This original dataset did not induce hardware OOM. Deterministic subprocess fixtures cover the failure mechanics; the later bounded CUDA experiment is documented separately and does not establish unconfounded physical VRAM exhaustion.
- 16K is the largest requested test point, not a discovered maximum.
- Other GPU capacities, Linux GPU execution, transformers/vLLM/MLX and quantization conversion are unvalidated or deferred.
- These GPU measurements do not validate Linux GPU execution or additional Python versions. Remote CPU fixture/packaging CI is recorded separately in the publication audit.

## Verification results

**150 tests passed, 1 opt-in GPU test skipped** in the default suite; Ruff passed. Separate installed-wheel GPU validation completed 15 context attempts plus six placement/probe attempts. All actual prompt/output counts matched; cache counts were zero; owned-process cleanup succeeded. Final source: `a87b244` plus documentation/evidence-only commits. The installed wheel's 14 Python source files matched the checkout and the hashes recorded in the final sessions.

The [context sweep](../benchmarks/rtx4070-super/context-sweep/report.md) uses three independent lifetimes per row. TTFT and engine generation rate are means; peak VRAM is the maximum sampled whole-device value among the three lifetimes.

| Allocated context | Fresh input / output | Mean first-text TTFT s | Mean generation token/s | Sampled device peak MiB |
|---:|---:|---:|---:|---:|
| 1024 | 768 / 128 | 0.205 | 80.13 | 6177 |
| 2048 | 1792 / 128 | 0.439 | 77.95 | 6320 |
| 4096 | 3840 / 128 | 0.971 | 72.77 | 6600 |
| 8192 | 7936 / 128 | 2.134 | 66.40 | 7215 |
| 16384 | 16128 / 128 | 5.122 | 54.99 | 8501 |

All five context cases loaded **37/37 GPU layers**. 16K completed on this machine without CPU weight offload, but no larger point was tested. Prompt throughput, load time, RAM, individual runs and sample SD are preserved in JSON/CSV and the reports.

The separate [placement session](../benchmarks/rtx4070-super/offload-quality/report.md) keeps the same 4096 context / 3840 input / 128 output, with three lifetimes per placement:

| Actual GPU layers | CPU weight offload | Mean first-text TTFT s | Mean generation token/s | Sampled device peak MiB | v2 probes per repeat |
|---:|:---:|---:|---:|---:|:---:|
| 37/37 | No | 0.998 | 70.52 | 6689 | 8/8, 8/8, 8/8 |
| 20/37 | Yes | 4.951 | 11.50 | 4501 | 8/8, 8/8, 8/8 |

This demonstrates a concrete memory/speed tradeoff on the tested desktop. Do not combine its timings with the separate context-sweep session. The [paired probe comparison](../benchmarks/rtx4070-super/probe-comparison.json) reports **0 percentage-point probe-score change**, zero observed regressions, and changed placement fields. It compares identical Q4 weights at different placements, not Q4 versus FP16; eight easy answers at a ceiling cannot establish equivalent general quality.

Installed wheel: `prismbench-0.1.0a1-py3-none-any.whl`, 40,072 bytes, SHA256 `07576ad9355c69a413581010a49250cb709c00a07c1ec1bbf1cace54cad0d349`. Runtime executable SHA256: `aa2e1f5c67be55f11be26ae58d643a545ca07c6de498f6f870330ac2f4dfec73`; all bundled DLL hashes are in provenance. Clean-install demo and `pip check` passed. See [independent benchmark audit](reviews/benchmark-audit.md), [release audit](reviews/release-audit.md), and [final signoff](reviews/final-audit.md).

## Quality protocol correction before release

The initial unconstrained raw-completion probe protocol scored **0/8** at both full-GPU and CPU-offload placements. Inspection showed the answer appeared correctly on the first line, followed by further reasoning/examples; the exact whole-response checker rejected that continuation. This was an unhelpful floor for these simple answer-only probes, not evidence of lost model capability.

The original six attempts remain unchanged in [the version 1 pilot](../benchmarks/rtx4070-super/quality-protocol-v1-pilot/results.json). After independent ML review, version 2 explicitly added `stop=["\n"]` to the generation contract and recorded it in requests and evaluation provenance. The suite version/hash changed, the strict answer comparator did not. New runs were executed; the earlier answers were **not rescored**, and version 1/2 scores must not be compared as a quality improvement. An empty answer from an initial newline still fails. Version 2 is a small single-line sanity test with ceiling effects.
