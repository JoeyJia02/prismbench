# Try PrismBench with your own model

Get a deployment report for a local GGUF: first-text latency, generation speed,
sampled memory and the evidence behind successful or failed attempts. This guide
uses the published **0.1.0a1 experimental alpha**. No Git clone, GitHub account,
Hugging Face login or administrator terminal is needed for the commands below.
Installation needs network access to GitHub and the Python package index.

Choose your starting point:

| What you have | Start here | What it establishes |
|---|---|---|
| Python, no model or GPU setup | Install and demo below | The package works; all demo measurements are synthetic |
| A working llama.cpp runtime and local GGUF | Install, then use your existing model below | A measurement of one configuration on your machine |
| No runtime/model, want the recorded Windows baseline | [Pinned download recipe](quickstart-rtx4070-super.md) | The specific Qwen3-8B/b10964 experiment; about 5.67 GB of model/runtime downloads |

## 1. Install and inspect a sample report

Use **Python 3.10+** (64-bit for Windows x64), a terminal in a new working
directory, and the appropriate block. `python --version` must work first. On
Linux, use `python3` if that is your Python command; install your distribution's
Python venv support if environment creation fails. No shell activation is needed.
The wheel URL pins the release and its SHA256; pip checks the downloaded wheel
against that hash. Dependencies are resolved from the package index.

Windows PowerShell:

```powershell
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment' }
.\.venv\Scripts\python.exe -m pip install "https://github.com/JoeyJia02/prismbench/releases/download/v0.1.0a1/prismbench-0.1.0a1-py3-none-any.whl#sha256=7488f2378bc6dabbf045dd6c5d2e775dd5f5be1b17d69f3c25234178e51b44d9"
if ($LASTEXITCODE -ne 0) { throw 'Installation failed; keep the error for feedback' }
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\prismbench.exe --version
.\.venv\Scripts\prismbench.exe demo --output outputs/demo
if ($LASTEXITCODE -ne 0) { throw 'Demo failed; keep the error for feedback' }
Get-Content outputs/demo/report.md
```

Linux/WSL, in a Linux shell:

```sh
python3 -m venv .venv &&
.venv/bin/python -m pip install 'https://github.com/JoeyJia02/prismbench/releases/download/v0.1.0a1/prismbench-0.1.0a1-py3-none-any.whl#sha256=7488f2378bc6dabbf045dd6c5d2e775dd5f5be1b17d69f3c25234178e51b44d9' &&
.venv/bin/python -m pip check &&
.venv/bin/prismbench --version &&
.venv/bin/prismbench demo --output outputs/demo &&
cat outputs/demo/report.md
```

Expect version `0.1.0a1`, no broken dependencies, and a report marked
**SYNTHETIC** with `SUCCESS`, `OOM`, `SUCCESS` attempts. The OOM is simulated.
Open `outputs/demo/report.md` in a Markdown viewer, or read its plain text.
This demo neither downloads a model nor measures your GPU. Installation time
depends on the network; it is not included in benchmark latency.

If you stop here, [first-run feedback](https://github.com/JoeyJia02/prismbench/issues/new?template=first_run.md)
is already useful. An unsuccessful installation is a valid report; no attachment
or GPU result is required.

## 2. Use an existing llama.cpp runtime and GGUF

The measured reference runtime is **llama.cpp b10964**. Other releases may change
flags or response fields; we do not claim they all work. Keep the runtime's
matching libraries beside its executable. On Windows, install the Microsoft
Visual C++ v14 **x64** Redistributable if `llama-server.exe --version` reports a
missing MSVC DLL; see the [prerequisites and verified runtime](quickstart-rtx4070-super.md).
On Linux/WSL use a Linux binary and Linux paths. Hosted Linux CI tests installation
and fixtures; it does not establish Linux GPU compatibility.

Start with a GGUF you already know can run on your machine with a 2K context.
Check its license. This is an existing-model path, not a promise that an arbitrary
model fits an 8 GB GPU. GPU memory telemetry currently uses NVIDIA `nvidia-smi`;
AMD/Intel/Apple memory measurements are not supported by this collector.

Replace the four example values with your executable, model path, publisher/model
identity and actual quantization. Paths with spaces work when quoted.

Windows PowerShell:

```powershell
$server = 'C:\llama\llama-server.exe'
$model = 'C:\models\Qwen3-8B-Q4_K_M.gguf'
& $server --version
if ($LASTEXITCODE -ne 0) { throw 'Fix the runtime preflight before continuing' }
.\.venv\Scripts\prismbench.exe doctor --gpu-index 0
.\.venv\Scripts\prismbench.exe init --server "$server" --model "$model" --model-id 'Qwen/Qwen3-8B' --quantization 'Q4_K_M'
```

Linux/WSL:

```sh
server='/path/to/llama-server'
model='/path/to/Qwen3-8B-Q4_K_M.gguf'
"$server" --version &&
.venv/bin/prismbench doctor --gpu-index 0 &&
.venv/bin/prismbench init --server "$server" --model "$model" --model-id 'Qwen/Qwen3-8B' --quantization 'Q4_K_M'
```

Open the generated `prismbench.local.json` in a text editor before running:

- Set **`"quality": false`** for this first deployment measurement. `init`
  otherwise enables the separate eight-probe smoke suite by default.
- Set **`"repetitions": 1`** for a first smoke run. Keep the 2,048-context /
  1,792-input / 128-output workload. Use three repetitions later for a measured
  comparison; a single attempt is not a repeatability study.
- Check `gpu_index: 0` against the device shown by `doctor`. `gpu_layers: 99`
  requests all available layers; lower it if your known working configuration
  needs CPU offload. Record that change and inspect effective placement afterward.
- Leave `fallbacks: []` for this first run. Do not deliberately exhaust memory.
  Close other GPU-heavy workloads yourself if practical and record background use
  in `notes`. `doctor` is a snapshot, not a model-fit or clean-environment check.

`doctor` can exit successfully with unavailable GPU telemetry: inspect
`snapshot.gpu_telemetry_error` and the memory fields. `init` checks file paths and
configuration; it does not test runtime compatibility or load the model.

Model/runtime hashes are recorded automatically. To reproduce someone else's
artifact, also set `expected_model_sha256` to their recorded model hash; a name
or quantization label alone does not establish identical weights.

Run the experiment (Windows PowerShell):

```powershell
.\.venv\Scripts\prismbench.exe run prismbench.local.json --output outputs/first-2k
if ($LASTEXITCODE -ne 0) { throw 'Run failed; inspect outputs/first-2k before retrying' }
Get-Content outputs/first-2k/report.md
```

Or Linux/WSL:

```sh
.venv/bin/prismbench run prismbench.local.json --output outputs/first-2k &&
cat outputs/first-2k/report.md
```

This starts one model lifetime, with hashing, loading and warmup in addition to
the measured request. Hashing runs before the first progress line and can take
time on a large file or slow disk. CPU offload can take much longer. There is no
automatic model/runtime download.

## 3. Read the result and give feedback

A successful first real run has `synthetic: false`, one `SUCCESS` attempt,
`cleanup_confirmed: true`, 1,792 prompt tokens, 128 generated tokens and zero
cache tokens for each attempt in `results.json`. Read the report's warnings and
effective placement. Missing memory telemetry is `null`, not zero. Device-wide
sampled VRAM includes other applications. Completing 2K establishes that tested
point, not maximum context or general model quality.

To collect repeated evidence, change `repetitions` to `3` and rerun with a fresh
output such as `outputs/repeated-2k`. Expect three independent `SUCCESS` attempts
with the same checks. Keep settings fixed within that session; do not substitute
three reruns with different placement/context or select only the fastest result.

| If you see this | Next step |
|---|---|
| Install/download error | Keep the exact failing step and error; use the short feedback form |
| Missing DLL or runtime cannot start | Fix runtime prerequisites; do not diagnose this as model OOM |
| `gpu_telemetry_error` or null VRAM | Check `nvidia-smi` and selected GPU; the run cannot establish VRAM usage |
| `INVALID_WORKLOAD` or unsupported flag | Retain logs and exact runtime version; this can be adapter incompatibility |
| `OOM` or `TIMEOUT` | Preserve the attempt; a failure is useful evidence. Change config only as a new experiment |
| Output directory/config already exists | Choose a new output/config name; preserve the earlier experiment |

`run` returns 0 for ultimately successful chains, 1 for failed chains and 2 for
input errors. Early input/hash errors may leave no report and an empty output
directory; preserve the terminal error and use a new path when retrying.
`report` validates saved result structure; it is not an independent
verification that the hardware experiment happened. Re-export without inference:

```powershell
.\.venv\Scripts\prismbench.exe report outputs/first-2k/results.json --output outputs/first-2k-export
```

On Linux use `.venv/bin/prismbench` for the same arguments. Exported reports link
back to the original evidence directory; keep it. Retrying either a demo, a real
run or export needs a fresh output path, such as `outputs/first-2k-retry`.

- [Short first-run feedback](https://github.com/JoeyJia02/prismbench/issues/new?template=first_run.md):
  OS/Python, step reached, outcome and one confusing point. No pull request needed.
- [Hardware reproduction](https://github.com/JoeyJia02/prismbench/issues/new?template=reproduction.md):
  optional fuller evidence when you have a measured result. Failed runs count too.
- Before attaching anything, follow [sharing results](sharing-results.md).
  Results are local; this alpha has no automatic upload or anonymization.

External user reports are still needed. Repeating this guide on the maintainer's
machine checks the instructions but is not independent hardware replication.
