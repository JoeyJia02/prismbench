# PrismBench deployment report

Session: 7e7dd83db9484cd2bb04fd202305bb0e · 2026-09-21T23:25:22.162145+00:00

Model: Qwen/Qwen3-8B · Quantization: Q4\_K\_M

**Local observations; results apply to this model, runtime, hardware and workload.**
VRAM values are sampled whole-device usage, including other applications; sampling can miss short peaks. Process RSS and system RAM are separate metrics.
TTFT is client-observed; PP and generation throughput come from the engine. Load time measures process start to ready, including startup overhead.

Attempt outcomes: OOM=1, SUCCESS=1.

Largest successfully **tested allocated context: 2048 tokens**. This is not a discovered maximum or evidence that every token in the window was used. See actual input/output lengths below.

## Exact deployment configurations

Each row keeps one case, exact requested configuration, observed effective settings, prompt hash and runtime version. Changed fallback configurations have separate rows; failed attempts remain in the ledger.

| ID | Case | Context/input/output | GPU layers requested | K/V | Threads/batch/micro | FA | Success/attempts | Mean TTFT s | Mean generation tok/s | Sample SD tok/s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | kv-allocation-recovery | 524288/128/16 | 99 | f16/f16 | 6/128/64 | on | 0/1 | — | — | — |
| C2 | kv-allocation-recovery | 2048/128/16 | 99 | f16/f16 | 6/128/64 | on | 1/1 | 0.056 | 81.35 | — |

## Matched workload comparison

No recommendation: there are fewer than two complete, successful, real configurations with a matching workload.

## Attempt ledger

| Attempt/evidence | Config | Repeat | Try | Status | TTFT s | Generation tok/s | Peak VRAM MiB | GPU layers loaded/total | CPU offload | Cleanup | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [kv-allocation-recovery-r1-a0](./attempts/kv-allocation-recovery-r1-a0) | C1 | 1 | 0 | OOM | — | — | 5920.0 | —/— | unknown | True | Server exited during load (1); inspect server logs |
| [kv-allocation-recovery-r1-a1](./attempts/kv-allocation-recovery-r1-a1) | C2 | 1 | 1 | SUCCESS | 0.056 | 81.35 | 6250.0 | 37/37 | False | True | — |

## Quality and limitations

Lightweight quality probes are regression checks, not a model capability score. Quantization quality loss is unmeasured without a paired reference evaluation. No percentage quality-loss claim or universal best configuration is inferred.

Recorded warnings:

- Opt-in real CUDA allocation-rejection experiment under external 8 GiB host Job commit ceiling; not a maximum usable context or sustained VRAM exhaustion measurement. Uncontrolled desktop; unchanged installed alpha CLI.
- kv-allocation-recovery-r1-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- kv-allocation-recovery-r1-a1: Preload GPU utilization exceeds 5%; background load may affect results.

Full metrics, requested and runtime settings, provenance, quality probe output and all failures are preserved in [results.json](results.json) and [results.csv](results.csv). Missing metrics are null in JSON and blank in CSV.
