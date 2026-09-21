# PrismBench

**Local llama.cpp deployment measurements, with the evidence behind every result.**

PrismBench starts a local model, checks the workload that actually ran, records latency and memory, and preserves failed attempts and explicit OOM fallbacks. It is a small Python CLI for developers working with consumer GPUs. **0.1.0a1 is an experimental alpha**, distributed through [GitHub Releases](https://github.com/JoeyJia02/prismbench/releases). It is not published on PyPI.

[![Tests and package](https://github.com/JoeyJia02/prismbench/actions/workflows/ci.yml/badge.svg)](https://github.com/JoeyJia02/prismbench/actions/workflows/ci.yml)

It answers: “Did this GGUF complete this context on my machine, at what cost, and what happened after a failure?” A successful 16K run means **16K was tested**, not that 16K is the model or device's maximum.

For model fit recommendations, start with [llmfit](https://github.com/AlexsJones/llmfit). For automatic configuration search, use [llama-autotune](https://github.com/Najafu/llama-autotune). For engine throughput microbenchmarks, use [llama-bench](https://github.com/ggml-org/llama.cpp/tree/master/tools/llama-bench). PrismBench focuses on owned server lifetimes, precise workload checks and inspectable failure evidence. See the [competitor analysis](docs/competitive-landscape.md) and [scope decision](docs/adr/0001-v01.md).

## Install and one-command demo

Python 3.10+ is required (use 64-bit Python for the Windows x64 runtime). Download the wheel from the [alpha release](https://github.com/JoeyJia02/prismbench/releases/tag/v0.1.0a1), then install it in a virtual environment:

```console
python -m venv .venv
```

Windows PowerShell (no activation needed):

```powershell
.\.venv\Scripts\python.exe -m pip install .\prismbench-0.1.0a1-py3-none-any.whl
.\.venv\Scripts\prismbench.exe demo
```

Linux/WSL:

```sh
.venv/bin/python -m pip install ./prismbench-0.1.0a1-py3-none-any.whl
.venv/bin/prismbench demo
```

For a source checkout, activate a virtual environment and run:

```console
python -m pip install .
prismbench demo
```

The demo needs no model, GPU, server or network after installation. It produces `results.json`, `results.csv`, and `report.md` under a new `outputs/` directory, including a **simulated OOM and successful fallback**. Every demo result is marked **synthetic**; its numbers are not hardware measurements.

For development, use a virtual environment:

```console
python -m venv .venv
```

Windows PowerShell: ` .\.venv\Scripts\Activate.ps1`. Linux/WSL: `source .venv/bin/activate`.

```console
python -m pip install -e ".[dev]"
python -m pytest
```

## Run a real model

For complete Windows download, checksum and first-run commands, follow the [RTX 4070 SUPER quickstart](docs/quickstart-rtx4070-super.md). The model alone is about 5 GB; the offline demo above does not download it.

1. Obtain a compatible [llama.cpp release](https://github.com/ggml-org/llama.cpp/releases) for your OS/GPU, keeping its bundled libraries beside `llama-server`. Tested release details are recorded in [validation](docs/validation.md); this is a version-sensitive adapter.
2. Download a GGUF from its publisher, comply with its model license, and keep it locally. PrismBench does not download weights or need Hugging Face credentials.
3. Inspect hardware and create an editable config. Example PowerShell paths:

```powershell
prismbench doctor
prismbench init --server C:\llama\llama-server.exe --model C:\models\Qwen3-8B-Q4_K_M.gguf --model-id Qwen/Qwen3-8B --quantization Q4_K_M
prismbench run prismbench.local.json
```

On Linux/WSL, supply the Linux `llama-server` binary and Linux model paths. Do not use a Windows binary inside a Linux config. No Docker or extra service is required.

`init` writes a 2K workload with three independent server lifetimes. Edit the JSON to adjust context, prompt/output token counts, GPU layers, KV cache types and repetitions. Use [the 1K–16K sample](examples/qwen3-context-sweep.json) or [offload fallback sample](examples/offload-fallback.json). Paths in JSON resolve **relative to that config file**. The CLI refuses to reuse an existing output directory.

```console
prismbench run my-config.json --output outputs/my-experiment
prismbench report outputs/my-experiment/results.json --output outputs/export
```

Report export validates saved data without inference. Raw evidence remains in the original experiment directory; copy that complete directory when sharing a report.

## What is measured

| Metric | Meaning |
|---|---|
| Model size and SHA256 | Actual local file; label/source identity is supplied by the user |
| Startup time | Process launch to healthy server, including runtime initialization; excludes downloading and hashing |
| TTFT | Client request start to first nonempty generated text chunk; includes HTTP/prefill, excludes model load; Unicode buffering makes this a first-text approximation |
| Prompt / generation token/s | llama.cpp's own terminal timings, retained without changing its denominator |
| Total latency | Client request start through the terminal streaming event |
| Idle / peak VRAM | Preload, loaded-idle and sampled lifecycle usage of the entire selected GPU |
| RAM | Sampled process-tree RSS and system RAM; shared pages can be counted more than once in tree RSS |
| Context and placement | Requested context checked against runtime; loaded GPU layers parsed from logs |

Peaks include loading, warmup, performance and optional quality probes. GPU sampling is best effort; unavailable values are `null`, never zero. Windows WDDM often cannot attribute VRAM to a process. Other desktop apps can affect device memory and timing. The report keeps environment warnings and raw samples; it does not certify a clean environment. See [methodology](docs/methodology.md) for boundaries and limitations.

Performance uses exact saved token IDs, one sequence, fixed seed, no context shifting, `--fit off`, explicit placement, a short excluded warmup and cache erase. A run with unexpected input/output counts, cache reuse, missing timing data or truncation is invalid. A capacity scan is a synthetic workload, not representative of every chat or reasoning workload.

## Failures and recovery

Each attempt has its own directory and terminal status. Confirmed OOM can advance through a **finite list of explicit fallback overrides**, after owned-process cleanup. Each override is relative to the original case, not cumulative. Changed contexts and placements retain separate identities; failed attempts remain in JSON, CSV and Markdown. Errors and timeouts do not automatically trigger OOM fallback. Cleanup failure stops the queue.

The adapter owns a Windows Job Object (suspended assignment before execution), or a process group on Linux. Timeouts and normal cancellation terminate its owned tree. It never kills unrelated GPU applications. Abrupt controller exit is covered on Windows; a Linux controller killed with SIGKILL can leave its process group alive (see limitations). Deterministic process fixtures exercise the failure paths. A separate [bounded Windows experiment](docs/validation-20260922.md) observed a real CUDA allocation rejection and successful 2K fallback under an external host-memory cap; it does not establish physical VRAM exhaustion or memory recovery before retry.

Exit codes: `0` all requested case/repetition chains ultimately succeeded; `1` any chain failed or was cancelled; `2` configuration/input error. A recovered OOM remains in the evidence even when the command exits `0`.

## Lightweight quality checks

Enable `quality` for bundled deterministic raw-completion probes, or supply `quality_suite` as a local JSON file following [the bundled format](src/prismbench/data/probes.json). The version 2 protocol requests a **single-line answer**, stops generation at the first newline, and compares the entire returned answer exactly after Unicode/whitespace normalization. It does not extract a correct substring from a longer response. They are **smoke probes, not a general benchmark or a percentage of quality retained**. Some instruction models require custom prompt templates; the bundled suite deliberately does not apply a hidden chat template.

Compare two results only with matched model identity, suite, seed, runtime and workload. When a session has multiple eligible attempts, select the desired attempt IDs:

```console
prismbench compare-quality reference/results.json candidate/results.json --reference-attempt ctx4k-r1-a0 --candidate-attempt ctx4k-r1-a0
```

The output is a paired **probe score delta**, with changed settings listed. It does not claim FP16-relative quantization degradation without a comparable measured reference. Perplexity and [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) integration are future work.

## Evidence and reproducibility

Each experiment contains the resolved config, model/runtime/source hashes, hardware snapshot, attempts, raw server logs, command line, token IDs, requests, responses, timestamped stream events and sampled telemetry. JSON conforms to the packaged [result schema](src/prismbench/data/result.schema.json). Failed attempts are usable diagnostic evidence; only valid successful runs enter performance tables, and different workloads are not combined into a “best” score.

New measurements produced by this package are documented in [validation](docs/validation.md). Prior laboratory scripts and historical model experiments, if present locally, remain outside the distributable project and do not count as validation of this package. Weights, DLLs and personal local outputs are ignored by Git.

The [2026-09-22 follow-up](docs/validation-20260922.md) verifies a public wheel installation in a new directory/venv on the same machine, three new 2K runs and one guarded CUDA failure/fallback chain. It includes the inherited OS dependencies and cache-reuse boundary; it is not independent hardware replication.

To reproduce a result, install the recorded tool/runtime versions, obtain the recorded model hash, restore its config paths, and rerun into a fresh output directory. Bit-for-bit timing or output equality across GPU builds is not promised. All supported claims are restricted to tested combinations.

## Contributing and release status

See [CONTRIBUTING](CONTRIBUTING.md), [open issues](https://github.com/JoeyJia02/prismbench/issues), [backlog and roadmap](docs/backlog.md), [release checklist](docs/release-checklist.md), and [independent reviews](docs/reviews/). CI exercises CPU fixture tests and wheel installation on Windows/Linux; real GPU integration is opt-in. The [publication audit](docs/reviews/publication-audit.md) records the release checks and their limits. Independent GPU reproduction, ordinary memory-pressure recovery and a pre-retry memory admission policy remain open work.

MIT license for this tool. Models and llama.cpp distributions retain their separate upstream licenses.
