# PrismBench deployment report

Session: d11f69a53a5843fe92a0662395a1f42a · 2026-09-21T14:31:25.296620+00:00

Model: Qwen/Qwen3-8B · Quantization: Q4\_K\_M

**Local observations; results apply to this model, runtime, hardware and workload.**
VRAM values are sampled whole-device usage, including other applications; sampling can miss short peaks. Process RSS and system RAM are separate metrics.
TTFT is client-observed; PP and generation throughput come from the engine. Load time measures process start to ready, including startup overhead.

Attempt outcomes: SUCCESS=6.

Largest successfully **tested allocated context: 4096 tokens**. This is not a discovered maximum or evidence that every token in the window was used. See actual input/output lengths below.

## Exact deployment configurations

Each row keeps one case, exact requested configuration, observed effective settings, prompt hash and runtime version. Changed fallback configurations have separate rows; failed attempts remain in the ledger.

| ID | Case | Context/input/output | GPU layers requested | K/V | Threads/batch/micro | FA | Success/attempts | Mean TTFT s | Mean generation tok/s | Sample SD tok/s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | full4k | 4096/3840/128 | 99 | f16/f16 | 6/512/128 | on | 3/3 | 0.998 | 70.52 | 0.42 |
| C2 | offload4k | 4096/3840/128 | 20 | f16/f16 | 6/512/128 | on | 3/3 | 4.951 | 11.50 | 0.06 |

## Matched workload comparison

Only complete successful repeat sets within the same session model, runtime version, context, input and output lengths and prompt hash are ordered below. This is a generation-speed comparison, not a quality or value recommendation.

C1: 70.52 tok/s → C2: 11.50 tok/s

## Attempt ledger

| Attempt/evidence | Config | Repeat | Try | Status | TTFT s | Generation tok/s | Peak VRAM MiB | GPU layers loaded/total | CPU offload | Cleanup | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [full4k-r1-a0](./attempts/full4k-r1-a0) | C1 | 1 | 0 | SUCCESS | 0.986 | 70.08 | 6689.0 | 37/37 | False | True | — |
| [full4k-r2-a0](./attempts/full4k-r2-a0) | C1 | 2 | 0 | SUCCESS | 1.009 | 70.93 | 6624.0 | 37/37 | False | True | — |
| [full4k-r3-a0](./attempts/full4k-r3-a0) | C1 | 3 | 0 | SUCCESS | 0.999 | 70.55 | 6607.0 | 37/37 | False | True | — |
| [offload4k-r1-a0](./attempts/offload4k-r1-a0) | C2 | 1 | 0 | SUCCESS | 4.971 | 11.54 | 4501.0 | 20/37 | True | True | — |
| [offload4k-r2-a0](./attempts/offload4k-r2-a0) | C2 | 2 | 0 | SUCCESS | 4.947 | 11.43 | 4501.0 | 20/37 | True | True | — |
| [offload4k-r3-a0](./attempts/offload4k-r3-a0) | C2 | 3 | 0 | SUCCESS | 4.936 | 11.54 | 4501.0 | 20/37 | True | True | — |

## Quality and limitations

Lightweight quality probes are regression checks, not a model capability score. Quantization quality loss is unmeasured without a paired reference evaluation. No percentage quality-loss claim or universal best configuration is inferred.

| Attempt | Probe suite | Passed | Probe count |
| --- | --- | --- | --- |
| full4k-r1-a0 | prismbench-basic-probes | 8 | 8 |
| full4k-r2-a0 | prismbench-basic-probes | 8 | 8 |
| full4k-r3-a0 | prismbench-basic-probes | 8 | 8 |
| offload4k-r1-a0 | prismbench-basic-probes | 8 | 8 |
| offload4k-r2-a0 | prismbench-basic-probes | 8 | 8 |
| offload4k-r3-a0 | prismbench-basic-probes | 8 | 8 |

Recorded warnings:

- Uncontrolled local environment; no clean-room qualification asserted.
- full4k-r1-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- full4k-r2-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- full4k-r3-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- offload4k-r1-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- offload4k-r2-a0: Preload GPU utilization exceeds 5%; background load may affect results.
- offload4k-r3-a0: Preload GPU utilization exceeds 5%; background load may affect results.

Full metrics, requested and runtime settings, provenance, quality probe output and all failures are preserved in [results.json](results.json) and [results.csv](results.csv). Missing metrics are null in JSON and blank in CSV.
