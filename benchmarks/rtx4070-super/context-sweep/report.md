# PrismBench deployment report

Session: c4816faa4160441e9851a6eef9bc1b19 · 2026-09-21T14:29:30.347434+00:00

Model: Qwen/Qwen3-8B · Quantization: Q4\_K\_M

**Local observations; results apply to this model, runtime, hardware and workload.**
VRAM values are sampled whole-device usage, including other applications; sampling can miss short peaks. Process RSS and system RAM are separate metrics.
TTFT is client-observed; PP and generation throughput come from the engine. Load time measures process start to ready, including startup overhead.

Attempt outcomes: SUCCESS=15.

Largest successfully **tested allocated context: 16384 tokens**. This is not a discovered maximum or evidence that every token in the window was used. See actual input/output lengths below.

## Exact deployment configurations

Each row keeps one case, exact requested configuration, observed effective settings, prompt hash and runtime version. Changed fallback configurations have separate rows; failed attempts remain in the ledger.

| ID | Case | Context/input/output | GPU layers requested | K/V | Threads/batch/micro | FA | Success/attempts | Mean TTFT s | Mean generation tok/s | Sample SD tok/s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | ctx1k | 1024/768/128 | 99 | f16/f16 | 6/512/128 | on | 3/3 | 0.205 | 80.13 | 1.06 |
| C2 | ctx2k | 2048/1792/128 | 99 | f16/f16 | 6/512/128 | on | 3/3 | 0.439 | 77.95 | 1.16 |
| C3 | ctx4k | 4096/3840/128 | 99 | f16/f16 | 6/512/128 | on | 3/3 | 0.971 | 72.77 | 0.19 |
| C4 | ctx8k | 8192/7936/128 | 99 | f16/f16 | 6/512/128 | on | 3/3 | 2.134 | 66.40 | 0.72 |
| C5 | ctx16k | 16384/16128/128 | 99 | f16/f16 | 6/512/128 | on | 3/3 | 5.122 | 54.99 | 2.19 |

## Matched workload comparison

No recommendation: there are fewer than two complete, successful, real configurations with a matching workload.

## Attempt ledger

| Attempt/evidence | Config | Repeat | Try | Status | TTFT s | Generation tok/s | Peak VRAM MiB | GPU layers loaded/total | CPU offload | Cleanup | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [ctx1k-r1-a0](./attempts/ctx1k-r1-a0) | C1 | 1 | 0 | SUCCESS | 0.215 | 80.00 | 6177.0 | 37/37 | False | True | — |
| [ctx1k-r2-a0](./attempts/ctx1k-r2-a0) | C1 | 2 | 0 | SUCCESS | 0.193 | 79.14 | 6176.0 | 37/37 | False | True | — |
| [ctx1k-r3-a0](./attempts/ctx1k-r3-a0) | C1 | 3 | 0 | SUCCESS | 0.207 | 81.26 | 6176.0 | 37/37 | False | True | — |
| [ctx2k-r1-a0](./attempts/ctx2k-r1-a0) | C2 | 1 | 0 | SUCCESS | 0.443 | 77.59 | 6320.0 | 37/37 | False | True | — |
| [ctx2k-r2-a0](./attempts/ctx2k-r2-a0) | C2 | 2 | 0 | SUCCESS | 0.451 | 79.24 | 6316.0 | 37/37 | False | True | — |
| [ctx2k-r3-a0](./attempts/ctx2k-r3-a0) | C2 | 3 | 0 | SUCCESS | 0.423 | 77.01 | 6312.0 | 37/37 | False | True | — |
| [ctx4k-r1-a0](./attempts/ctx4k-r1-a0) | C3 | 1 | 0 | SUCCESS | 0.971 | 72.78 | 6600.0 | 37/37 | False | True | — |
| [ctx4k-r2-a0](./attempts/ctx4k-r2-a0) | C3 | 2 | 0 | SUCCESS | 0.969 | 72.57 | 6595.0 | 37/37 | False | True | — |
| [ctx4k-r3-a0](./attempts/ctx4k-r3-a0) | C3 | 3 | 0 | SUCCESS | 0.973 | 72.96 | 6597.0 | 37/37 | False | True | — |
| [ctx8k-r1-a0](./attempts/ctx8k-r1-a0) | C4 | 1 | 0 | SUCCESS | 2.168 | 65.58 | 7215.0 | 37/37 | False | True | — |
| [ctx8k-r2-a0](./attempts/ctx8k-r2-a0) | C4 | 2 | 0 | SUCCESS | 2.149 | 66.68 | 7202.0 | 37/37 | False | True | — |
| [ctx8k-r3-a0](./attempts/ctx8k-r3-a0) | C4 | 3 | 0 | SUCCESS | 2.085 | 66.93 | 7181.0 | 37/37 | False | True | — |
| [ctx16k-r1-a0](./attempts/ctx16k-r1-a0) | C5 | 1 | 0 | SUCCESS | 5.056 | 57.46 | 8334.0 | 37/37 | False | True | — |
| [ctx16k-r2-a0](./attempts/ctx16k-r2-a0) | C5 | 2 | 0 | SUCCESS | 5.038 | 54.22 | 8428.0 | 37/37 | False | True | — |
| [ctx16k-r3-a0](./attempts/ctx16k-r3-a0) | C5 | 3 | 0 | SUCCESS | 5.271 | 53.27 | 8501.0 | 37/37 | False | True | — |

## Quality and limitations

Lightweight quality probes are regression checks, not a model capability score. Quantization quality loss is unmeasured without a paired reference evaluation. No percentage quality-loss claim or universal best configuration is inferred.

Recorded warnings:

- Uncontrolled local environment; no clean-room qualification asserted.
- ctx1k-r1-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- ctx1k-r2-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- ctx1k-r3-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- ctx2k-r1-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- ctx4k-r1-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- ctx4k-r2-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- ctx8k-r3-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- ctx16k-r2-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- ctx16k-r3-a0: Preload GPU utilization exceeds 5%; background load may affect results.

Full metrics, requested and runtime settings, provenance, quality probe output and all failures are preserved in [results.json](results.json) and [results.csv](results.csv). Missing metrics are null in JSON and blank in CSV.
