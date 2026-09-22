# Published evidence directory

These are **real new-runner observations**, not synthetic demo outputs. The complete raw artifacts are included so measurements can be inspected, including unsuccessful or unhelpful experimental protocols. Model weights and runtime binaries are not distributed here.

Read [validation and reproduction](../docs/validation.md), [methodology](../docs/methodology.md), and [the independent benchmark audit](../docs/reviews/benchmark-audit.md) before comparing numbers.

## RTX 4070 SUPER, Windows, Qwen3-8B Q4_K_M

- [Context sweep report](rtx4070-super/context-sweep/report.md): 1K, 2K, 4K, 8K and 16K; three lifetimes each.
- [Placement/probe report](rtx4070-super/offload-quality/report.md): full GPU vs 20 GPU layers with CPU offload, same 4K workload and version 2 probes.
- [Original version 1 quality pilot](rtx4070-super/quality-protocol-v1-pilot/report.md): unconstrained raw completions, preserved unchanged at 0/8. It is not a baseline for version 2 score comparison.
- [Fresh installation, 2026-09-22](rtx4070-super/fresh-install-20260922/report.md): three new 2K lifetimes from a separate directory and Python 3.14.5 virtual environment. The released wheel was downloaded; cached model/runtime artifacts were independently hashed. This is same-machine reproduction, not another GPU or a clean OS installation.
- [Bounded CUDA failure/fallback, 2026-09-22](rtx4070-super/oom-recovery-20260922/benchmark/report.md): one rejected 72 GiB CUDA allocation and an explicit successful 2K fallback, with [external guard and settling evidence](rtx4070-super/oom-recovery-20260922/audit.json). The 8 GiB host Job cap is a possible cause of the rejection; physical VRAM exhaustion is not proven.

Each directory includes schema-valid results, CSV, report, resolved local config and raw attempt subdirectories. All source, model and Windows bundled-library hashes are recorded. Paths in provenance describe the original execution machine; adjust config paths for your checkout. Runtime API keys visible in recorded local commands were random per-attempt loopback tokens for servers which were terminated; they are not external service credentials.

The machine was an active desktop, and the report retains preload GPU-utilization warnings. Whole-device VRAM includes desktop applications and sampled peaks can miss transients. Cleanup confirms owned processes exited; it is not a guarantee of sustained VRAM recovery or a clean laboratory environment. Largest tested context is not an exact limit.

## Quantization reference pilot

[Qwen3-1.7B F16/Q8/Q4 evidence](rtx4070-super/quantization-quality-20260922/README.md)
contains a paired 32-chunk English corpus diagnostic and separate deployment
measurements. See [its validation report](../docs/validation-quantization-20260922.md)
for lineage, deliberately omitted corpus-derived files and limits. PPL change is
not a percentage of general quality lost.
