# PrismBench deployment report

Session: b560ef8734eb49c0b6a4ff23c2b1696c · 2026-09-21T23:17:46.147526+00:00

Model: Qwen/Qwen3-8B · Quantization: Q4\_K\_M

**Local observations; results apply to this model, runtime, hardware and workload.**
VRAM values are sampled whole-device usage, including other applications; sampling can miss short peaks. Process RSS and system RAM are separate metrics.
TTFT is client-observed; PP and generation throughput come from the engine. Load time measures process start to ready, including startup overhead.

Attempt outcomes: SUCCESS=3.

Largest successfully **tested allocated context: 2048 tokens**. This is not a discovered maximum or evidence that every token in the window was used. See actual input/output lengths below.

## Exact deployment configurations

Each row keeps one case, exact requested configuration, observed effective settings, prompt hash and runtime version. Changed fallback configurations have separate rows; failed attempts remain in the ledger.

| ID | Case | Context/input/output | GPU layers requested | K/V | Threads/batch/micro | FA | Success/attempts | Mean TTFT s | Mean generation tok/s | Sample SD tok/s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | ctx2k | 2048/1792/128 | 99 | f16/f16 | 6/512/128 | on | 3/3 | 0.434 | 77.67 | 0.45 |

## Matched workload comparison

No recommendation: there are fewer than two complete, successful, real configurations with a matching workload.

## Attempt ledger

| Attempt/evidence | Config | Repeat | Try | Status | TTFT s | Generation tok/s | Peak VRAM MiB | GPU layers loaded/total | CPU offload | Cleanup | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [ctx2k-r1-a0](./attempts/ctx2k-r1-a0) | C1 | 1 | 0 | SUCCESS | 0.443 | 77.39 | 6268.0 | 37/37 | False | True | — |
| [ctx2k-r2-a0](./attempts/ctx2k-r2-a0) | C1 | 2 | 0 | SUCCESS | 0.430 | 77.43 | 6268.0 | 37/37 | False | True | — |
| [ctx2k-r3-a0](./attempts/ctx2k-r3-a0) | C1 | 3 | 0 | SUCCESS | 0.429 | 78.20 | 6268.0 | 37/37 | False | True | — |

## Quality and limitations

Lightweight quality probes are regression checks, not a model capability score. Quantization quality loss is unmeasured without a paired reference evaluation. No percentage quality-loss claim or universal best configuration is inferred.

Recorded warnings:

- Uncontrolled local environment; no clean-room qualification asserted.
- ctx2k-r1-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- ctx2k-r2-a0: Preload GPU utilization exceeds 5%; background load may affect results.

Full metrics, requested and runtime settings, provenance, quality probe output and all failures are preserved in [results.json](results.json) and [results.csv](results.csv). Missing metrics are null in JSON and blank in CSV.
