# Reproduce the RTX 4070 SUPER experiment

This guide starts with a 2K context and three independent server lifetimes on Windows. It uses the exact upstream llama.cpp build and Qwen GGUF from [the recorded validation](validation.md). The optional sections expand to 1K–16K and compare full GPU placement with CPU weight offload. No existing recorded configuration or result needs editing.

The reference machine has a 12 GB RTX 4070 SUPER and 32 GB system RAM. You need 64-bit Python 3.10+ (the original measurements used 3.12.3; the follow-up used 3.14.5), an NVIDIA driver with working `nvidia-smi`, and internet access for installation and downloads. GitHub or Hugging Face login is not needed for these public assets. Read the [publisher's model card and license](https://huggingface.co/Qwen/Qwen3-8B-GGUF/tree/7c41481f57cb95916b40956ab2f0b139b296d974) before use. The tool, runtime and model have separate licenses.

The Windows x64 llama.cpp runtime also needs the **Microsoft Visual C++ v14 x64 Redistributable**. Its `MSVCP140.dll`, `VCRUNTIME140.dll` and `VCRUNTIME140_1.dll` dependencies are not in the two CUDA archives. If the runtime preflight below reports a missing one, install or repair the x64 package from [Microsoft's supported downloads](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist), then repeat `llama-server.exe --version`. A new Python virtual environment does not isolate this operating-system dependency; the Redistributable must be at least as recent as the runtime's MSVC build tools.

Allow **about 10 GB of free disk space** for this recipe; this is a planning estimate including retained archives, extraction, model, Python environment and results. The model is exactly 5,027,783,488 bytes (5.03 GB / 4.68 GiB). The two runtime ZIPs total 645,511,278 bytes (about 616 MiB), and their extracted files total 1,167,991,069 bytes (about 1.09 GiB). Python and pip dependencies add a variable amount. These are disk/download sizes, not VRAM requirements.

The roughly 5.67 GB model-plus-runtime download takes an idealized 7.6 minutes at a sustained 100 Mbit/s or 38 minutes at 20 Mbit/s, before server overhead and retries. Download duration is not benchmark latency.

## 1. Install the pinned alpha

Open an ordinary PowerShell terminal. Use a new directory; change `D:\PrismBench-Repro` if needed. Run the blocks in this guide in the same terminal, from that directory. Activation and administrator privileges are unnecessary.

```powershell
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path D:\PrismBench-Repro -Force | Out-Null
Set-Location D:\PrismBench-Repro
New-Item -ItemType Directory -Path downloads, models, runtimes\upstream -Force | Out-Null

function Get-Asset([string]$Uri, [string]$OutFile) {
    & curl.exe --fail --location --retry 3 --continue-at - --output $OutFile $Uri
    if ($LASTEXITCODE -ne 0) { throw "Download failed: $OutFile" }
}
function Assert-Sha256([string]$Path, [string]$Expected) {
    $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $Expected) { throw "SHA256 mismatch: $Path" }
    Write-Host "Verified $Path"
}

$release = 'https://github.com/JoeyJia02/prismbench/releases/download/v0.1.0a1'
$wheel = 'prismbench-0.1.0a1-py3-none-any.whl'
Get-Asset "$release/$wheel" "downloads/$wheel"
Get-Asset "$release/SHA256SUMS.txt" 'downloads/SHA256SUMS.txt'
$wheelLine = @(Get-Content downloads/SHA256SUMS.txt | Where-Object { ($_ -split '\s+')[-1] -eq $wheel })
if ($wheelLine.Count -ne 1) { throw 'Wheel checksum entry missing or ambiguous' }
Assert-Sha256 "downloads/$wheel" (($wheelLine[0] -split '\s+')[0])

python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed' }
& .\.venv\Scripts\python.exe -m pip install "downloads/$wheel"
if ($LASTEXITCODE -ne 0) { throw 'Package installation failed' }
& .\.venv\Scripts\prismbench.exe --version
& .\.venv\Scripts\prismbench.exe demo
if ($LASTEXITCODE -ne 0) { throw 'Synthetic demo failed' }
```

The version should be `0.1.0a1`. The demo creates a timestamped `outputs/` directory containing JSON, CSV and Markdown, including a **simulated** OOM/fallback. It runs without downloading a model and does not measure your GPU. If a download was interrupted, `Get-Asset` attempts to resume it; do not continue after a checksum mismatch. Release assets and their checksum manifest are linked on the [alpha release page](https://github.com/JoeyJia02/prismbench/releases/tag/v0.1.0a1).

For a source installation instead, obtain the `v0.1.0a1` tag of [this repository](https://github.com/JoeyJia02/prismbench) and install that checkout with `python -m pip install .` in its own virtual environment. Do not silently substitute the moving `main` branch when reproducing alpha measurements. The original benchmark's evaluator sources were at `a87b244`; [validation](validation.md) records the relationship to the packaged release. The saved evidence hashes identify the actual files used.

## 2. Download and verify the Windows runtime

Use **both** CUDA 12.4 ZIPs from upstream [llama.cpp b10964](https://github.com/ggml-org/llama.cpp/releases/tag/b10964), commit `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`. The executable archive alone does not include the required CUDA runtime DLLs. Keep all extracted files together, without mixing other releases. Asset names, sizes and SHA256 digests below were checked against the official release API.

```powershell
$llamaRelease = 'https://github.com/ggml-org/llama.cpp/releases/download/b10964'
$serverZip = 'llama-b10964-bin-win-cuda-12.4-x64.zip'
$cudaZip = 'cudart-llama-bin-win-cuda-12.4-x64.zip'
Get-Asset "$llamaRelease/$serverZip" "downloads/$serverZip"
Get-Asset "$llamaRelease/$cudaZip" "downloads/$cudaZip"
Assert-Sha256 "downloads/$serverZip" '264f20d7ee3860aecca9ec12418357a9f3e80349a2b186f66c63859ded1a9593'
Assert-Sha256 "downloads/$cudaZip" '8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6'
Expand-Archive -LiteralPath "downloads/$serverZip" -DestinationPath runtimes/upstream -Force
Expand-Archive -LiteralPath "downloads/$cudaZip" -DestinationPath runtimes/upstream -Force
Assert-Sha256 'runtimes/upstream/llama-server.exe' 'aa2e1f5c67be55f11be26ae58d643a545ca07c6de498f6f870330ac2f4dfec73'
& .\runtimes\upstream\llama-server.exe --version
if ($LASTEXITCODE -ne 0) { throw 'Runtime preflight failed; inspect missing DLL or driver errors' }
```

Expect `0.4.1-dev (build 10964, commit b29c606e2)` in the version output. Running this prebuilt distribution uses its bundled CUDA libraries; it does not require compiling llama.cpp or installing the full CUDA developer toolkit. The reference driver was 610.88. Your driver and desktop activity may differ; the report records these differences. A driver-reported CUDA compatibility version is not the linked CUDA runtime version.

## 3. Download the pinned model and inspect hardware

The download uses the publisher's immutable repository revision, rather than `main`. PrismBench will also check the model hash before running.

```powershell
$modelRevision = '7c41481f57cb95916b40956ab2f0b139b296d974'
$modelUrl = "https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/$modelRevision/Qwen3-8B-Q4_K_M.gguf?download=true"
Get-Asset $modelUrl 'models/Qwen3-8B-Q4_K_M.gguf'
Assert-Sha256 'models/Qwen3-8B-Q4_K_M.gguf' 'd98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785'
& .\.venv\Scripts\prismbench.exe doctor --gpu-index 0
```

Check `snapshot.gpu_name`, `vram_total_mib` and `gpu_telemetry_error`. Unknown telemetry is reported as `null`; it is not zero memory consumption. If `nvidia-smi` is unavailable, resolve the driver/PATH issue before attempting to reproduce VRAM measurements. For multiple GPUs, choose the same index in both `doctor` and the config. Close GPU-intensive apps yourself if practical and record remaining background work; a single idle snapshot cannot certify a clean environment.

## 4. Run the first real 2K experiment

This writes a new config beside `models/` and `runtimes/`. Its relative paths resolve from **the JSON file's directory**, not from the shell's current directory. `Set-Content -Encoding ascii` is intentional here: the example contains only ASCII and works without a UTF-8 BOM on Windows PowerShell 5.1 as well as PowerShell 7.

```powershell
@'
{
  "backend": "llama_cpp",
  "server": "runtimes/upstream/llama-server.exe",
  "model": "models/Qwen3-8B-Q4_K_M.gguf",
  "model_id": "Qwen/Qwen3-8B",
  "quantization": "Q4_K_M",
  "expected_model_sha256": "d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785",
  "repetitions": 3,
  "seed": 42,
  "gpu_index": 0,
  "quality": false,
  "cases": [{
    "name": "ctx2k",
    "context_size": 2048,
    "prompt_tokens": 1792,
    "output_tokens": 128,
    "gpu_layers": 99,
    "threads": 6,
    "batch_size": 512,
    "ubatch_size": 128,
    "cache_type_k": "f16",
    "cache_type_v": "f16",
    "flash_attention": "on"
  }]
}
'@ | Set-Content -LiteralPath quickstart.local.json -Encoding ascii
& .\.venv\Scripts\prismbench.exe run quickstart.local.json --output outputs/first-2k
if ($LASTEXITCODE -ne 0) { throw 'Experiment failed; inspect outputs/first-2k before retrying' }
Get-Content outputs/first-2k/report.md
```

Requesting 99 GPU layers asks the runtime to offload all available layers; this model actually loaded 37/37 in the reference run. Check the **effective** placement in your results. The request uses 1,792 fresh input tokens and 128 generated tokens inside a 2,048-token allocated context, with a separate excluded warmup. It is a fixed raw-completion workload, not a chat latency test.

The original 2K attempts each loaded in 2.31–2.35 seconds and completed the measured request in 2.05–2.08 seconds. Their mean first-text TTFT was 0.439 seconds, mean engine generation rate was 77.95 token/s, and maximum sampled whole-device VRAM was 6,320 MiB. These are observations from an uncontrolled desktop, not pass/fail thresholds. For planning, allow **1–3 minutes after downloads** for the three-lifetime first run, model/library hashing and setup; this is an estimate, not measured end-to-end wall time. Cold disks, antivirus, drivers and background load can change it substantially.

Success means three `SUCCESS` attempts, `synthetic: false`, the expected input/output counts, zero cache hits and confirmed owned-process cleanup in `results.json`. It does not prove that larger contexts fit. A nonzero exit leaves diagnostic evidence; inspect the report and attempt's server log. The CLI refuses an existing output directory: retry using a new name such as `outputs/first-2k-retry`, preserving the failed run.

To re-export a report without another GPU run:

```powershell
& .\.venv\Scripts\prismbench.exe report outputs/first-2k/results.json --output outputs/first-2k-export
```

## 5. Optional context and placement comparisons

Create separate configs from the working first-run config. This retains the verified local paths and model hash while leaving the initial config and all recorded benchmark files unchanged.

For the recorded 1K–16K context sweep, use three repetitions per point and no quality probes:

```powershell
$sweepConfig = Get-Content quickstart.local.json -Raw | ConvertFrom-Json
$sweepConfig.cases = @(foreach ($context in 1024, 2048, 4096, 8192, 16384) {
    $case = $sweepConfig.cases[0].PSObject.Copy()
    $case.name = 'ctx' + ($context / 1024) + 'k'
    $case.context_size = $context
    $case.prompt_tokens = $context - 256
    $case
})
$sweepConfig | ConvertTo-Json -Depth 10 | Set-Content context-sweep.local.json -Encoding ascii
& .\.venv\Scripts\prismbench.exe run context-sweep.local.json --output outputs/context-sweep
```

This requests 15 independent lifetimes. Allow roughly 3–10 minutes on a similar desktop after downloading; this is a planning estimate. The reference completed all points, with a sampled device peak of 8,501 MiB at 16K. **16K is the largest tested point, not a discovered maximum.** Smaller GPUs may fail sooner; keep those attempts as evidence.

For a separate comparison at 4K, run both placements explicitly. An OOM fallback configuration only runs later settings after a confirmed OOM, so it is not a way to guarantee a paired placement comparison:

```powershell
$placementConfig = Get-Content quickstart.local.json -Raw | ConvertFrom-Json
$placementConfig.quality = $true
$placementConfig.cases = @(foreach ($layers in 99, 20) {
    $case = $placementConfig.cases[0].PSObject.Copy()
    $case.name = if ($layers -eq 99) { 'full4k' } else { 'offload4k' }
    $case.context_size = 4096
    $case.prompt_tokens = 3840
    $case.gpu_layers = $layers
    $case
})
$placementConfig | ConvertTo-Json -Depth 10 | Set-Content placement.local.json -Encoding ascii
& .\.venv\Scripts\prismbench.exe run placement.local.json --output outputs/placement
& .\.venv\Scripts\prismbench.exe compare-quality outputs/placement/results.json outputs/placement/results.json --reference-attempt full4k-r1-a0 --candidate-attempt offload4k-r1-a0
```

This makes six lifetimes with the bundled version 2 single-line probes. Allow roughly 3–10 minutes as a planning estimate. The reference's full placement versus 20-layer placement used 6,689 versus 4,501 MiB sampled peak VRAM and generated 70.52 versus 11.50 token/s. Both answered 8/8 probes in each repeat. Those easy probes compare the **same Q4 weights** at different placements; they do not establish general quality equivalence or quantify Q4-versus-FP16 degradation. The comparison command above selects repetition 1 only; select `r2` and `r3` explicitly to inspect the other pairs. Keep this session separate from the context sweep when comparing timings.

For explicit failure recovery, see [the fallback example](../examples/offload-fallback.json) and [methodology](methodology.md). Copy it into your own config and adjust paths/hash first. The published alpha has no deliberate real-hardware OOM validation; deterministic process fixtures validate its fallback mechanics.

## Linux and WSL pointers

Install the same wheel into a Linux virtual environment and use `.venv/bin/prismbench`. Use Linux paths and a **Linux** `llama-server`; Windows DLLs and the `.exe` are not a Linux runtime. Real GPU execution on Linux/WSL is not validated by the published Windows results.

The pinned b10964 release does not provide a Linux CUDA binary archive. A CUDA source build is an option once the Linux C++ toolchain, CMake and compatible NVIDIA CUDA toolkit are installed. Follow the [pinned upstream CUDA build instructions](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/docs/build.md#cuda); in WSL, first make GPU access work in that Linux environment. These commands are build pointers, not a claim that this combination has been benchmarked:

```sh
git clone --branch b10964 --depth 1 https://github.com/ggml-org/llama.cpp.git llama.cpp-b10964
git -C llama.cpp-b10964 rev-parse HEAD
# Verify b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 before building.
cmake -S llama.cpp-b10964 -B llama.cpp-b10964/build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp-b10964/build --config Release --target llama-server -j 6
./llama.cpp-b10964/build/bin/llama-server --version
```

Set `server` in your JSON to `llama.cpp-b10964/build/bin/llama-server`, relative to the config above that directory. Keep the matching shared libraries in place. Download the same pinned model URL with `curl -fL -C - -o models/Qwen3-8B-Q4_K_M.gguf "$model_url"` after assigning `model_url` to the full URL shown in step 3, and verify it using `sha256sum`. The model hash stays the same; a locally compiled Linux executable will **not** match the Windows executable hash. Preserve compiler/build information and keep its measurements separate. This alpha records adjacent Windows DLL hashes, but does not comprehensively inventory Linux shared-library dependencies.

Share the complete experiment directory, the config and enough environment details to reproduce the run. Review it for local paths or other information you do not want public; do not include weights or runtime archives. See [contribution guidance](../CONTRIBUTING.md) and the [open reproduction issues](https://github.com/JoeyJia02/prismbench/issues).
